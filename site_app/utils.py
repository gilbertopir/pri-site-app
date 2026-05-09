import math
import ezdxf
import pyproj
import numpy as np
from pathlib import Path
from django.conf import settings


# -----------------------------
# Coordinate transformers
# -----------------------------
osgb_to_gps = pyproj.Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True)
gps_to_osgb = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)


# -----------------------------
# DXF helpers
# -----------------------------
def extract_xy_from_entity(e):
    points = []
    if e.dxftype() == "LWPOLYLINE":
        for p in e.get_points():
            points.append((float(p[0]), float(p[1])))
    elif e.dxftype() == "POLYLINE":
        for v in e.vertices:
            loc = v.dxf.location
            points.append((float(loc.x), float(loc.y)))
    elif e.dxftype() == "LINE":
        points.append((float(e.dxf.start.x), float(e.dxf.start.y)))
        points.append((float(e.dxf.end.x), float(e.dxf.end.y)))
    clean = []
    for p in points:
        if not clean or math.dist(clean[-1], p) > 0.001:
            clean.append(p)
    return clean


def line_length(points):
    return sum(math.dist(points[i - 1], points[i]) for i in range(1, len(points)))


def cumulative_distances(points):
    d = [0.0]
    for i in range(1, len(points)):
        d.append(d[-1] + math.dist(points[i - 1], points[i]))
    return np.array(d)


def load_alignment_from_dxf(dxf_filename):
    """
    Load the longest polyline from a DXF file.
    Returns a dict with points, cum_dist, total_length, layer, entity.
    Returns None if file not found or no valid entities.
    """
    dxf_path = Path(settings.DXF_DIR) / dxf_filename

    if not dxf_path.exists():
        return None

    try:
        doc = ezdxf.readfile(str(dxf_path))
    except Exception:
        return None

    msp = doc.modelspace()
    candidates = []

    for e in msp:
        if e.dxftype() in ["LWPOLYLINE", "POLYLINE", "LINE"]:
            pts = extract_xy_from_entity(e)
            if len(pts) >= 2:
                candidates.append({
                    "entity": e.dxftype(),
                    "layer":  e.dxf.layer,
                    "points": pts,
                    "length": line_length(pts)
                })

    if not candidates:
        return None

    longest = max(candidates, key=lambda x: x["length"])

    return {
        "points":       longest["points"],
        "cum_dist":     cumulative_distances(longest["points"]),
        "total_length": longest["length"],
        "layer":        longest["layer"],
        "entity":       longest["entity"],
    }


def get_available_dxf_files():
    """Return a sorted list of .dxf filenames in the DXF_DIR."""
    dxf_dir = Path(settings.DXF_DIR)
    if not dxf_dir.exists():
        return []
    return sorted([f.name for f in dxf_dir.glob("*.dxf")])


# -----------------------------
# Geometry helpers
# -----------------------------
def point_at_chainage(points, cum_dist, chainage):
    """Return the (easting, northing) point at a given chainage along the alignment."""
    total  = cum_dist[-1]
    target = max(0.0, min(float(chainage), float(total)))

    if target >= total:
        return points[-1]

    idx = int(np.searchsorted(cum_dist, target)) - 1
    idx = max(0, min(idx, len(points) - 2))

    seg_len = cum_dist[idx + 1] - cum_dist[idx]
    if seg_len == 0:
        return points[idx]

    frac = (target - cum_dist[idx]) / seg_len
    x1, y1 = points[idx]
    x2, y2 = points[idx + 1]

    return (x1 + (x2 - x1) * frac, y1 + (y2 - y1) * frac)


def chainage_from_xy(points, cum_dist, x, y):
    """
    Find the nearest point on the alignment to (x, y).
    Returns dict with chainage, easting, northing, distance.
    """
    best = None

    for i in range(len(points) - 1):
        x1, y1 = points[i]
        x2, y2 = points[i + 1]
        dx, dy  = x2 - x1, y2 - y1
        seg_len_sq = dx * dx + dy * dy

        if seg_len_sq == 0:
            continue

        t = max(0.0, min(1.0, ((x - x1) * dx + (y - y1) * dy) / seg_len_sq))
        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        distance = math.dist((x, y), (proj_x, proj_y))
        chainage = float(cum_dist[i]) + t * math.sqrt(seg_len_sq)

        if best is None or distance < best["distance"]:
            best = {
                "chainage": chainage,
                "easting":  proj_x,
                "northing": proj_y,
                "distance": distance,
            }

    return best


# -----------------------------
# Coordinate conversion helpers
# -----------------------------
def osgb_to_wgs84(easting, northing):
    """Convert OSGB36 easting/northing to WGS84 lat/lon."""
    lon, lat = osgb_to_gps.transform(easting, northing)
    return round(lat, 8), round(lon, 8)


def wgs84_to_osgb(lat, lon):
    """Convert WGS84 lat/lon to OSGB36 easting/northing."""
    easting, northing = gps_to_osgb.transform(lon, lat)
    return round(easting, 3), round(northing, 3)


def gps_to_projected(points, cum_dist, lat, lon):
    """
    Full pipeline: GPS coords → projected point on alignment.
    Returns dict with chainage, projected lat/lon, easting, northing,
    distance_from_alignment. Returns None if no alignment loaded.
    """
    easting, northing = wgs84_to_osgb(lat, lon)
    result = chainage_from_xy(points, cum_dist, easting, northing)

    if result is None:
        return None

    proj_lat, proj_lon = osgb_to_wgs84(result["easting"], result["northing"])

    return {
        "chainage":                round(result["chainage"], 3),
        "easting":                 round(result["easting"], 3),
        "northing":                round(result["northing"], 3),
        "latitude":                proj_lat,
        "longitude":               proj_lon,
        "distance_from_alignment": round(result["distance"], 3),
    }


def chainage_to_gps(points, cum_dist, chainage):
    """
    Full pipeline: chainage → GPS coords + OSGB coords.
    Returns dict with easting, northing, lat, lon.
    """
    east, north = point_at_chainage(points, cum_dist, chainage)
    lat, lon    = osgb_to_wgs84(east, north)

    return {
        "chainage":  round(chainage, 3),
        "easting":   round(east, 3),
        "northing":  round(north, 3),
        "latitude":  lat,
        "longitude": lon,
    }


# -----------------------------
# Alignment GPS line for maps
# -----------------------------
def get_alignment_gps_line(points):
    """
    Convert all alignment points to WGS84 for Leaflet polyline.
    Returns list of [lat, lon] pairs.
    """
    return [list(osgb_to_wgs84(x, y)) for x, y in points]


# -----------------------------
# Next passing place ID
# -----------------------------
def get_next_pp_id(alignment):
    """Generate the next PP ID for a given alignment e.g. PP004."""
    from .models import PassingPlace
    existing = PassingPlace.objects.filter(alignment=alignment).values_list("pp_id", flat=True)
    nums = []
    for pp_id in existing:
        try:
            nums.append(int(pp_id.replace("PP", "")))
        except ValueError:
            pass
    next_num = max(nums) + 1 if nums else 1
    return f"PP{next_num:03d}"