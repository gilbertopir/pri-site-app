import json
import csv
from datetime import datetime

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib import messages

from .models import Alignment, FeatureCapture, PassingPlace
from .utils import (
    load_alignment_from_dxf,
    get_available_dxf_files,
    gps_to_projected,
    chainage_to_gps,
    get_alignment_gps_line,
    get_next_pp_id,
)


# -----------------------------
# Helper — load alignment or 404
# -----------------------------
def get_alignment_data(alignment):
    """Load DXF data for an alignment. Returns None if file missing."""
    return load_alignment_from_dxf(alignment.dxf_file)


# -----------------------------
# Auth views
# -----------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    error = None
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            error = "Invalid username or password."

    return render(request, "login.html", {"error": error})


def logout_view(request):
    logout(request)
    return redirect("login")


# -----------------------------
# Dashboard — site selector
# -----------------------------
@login_required
def dashboard(request):
    alignments = Alignment.objects.filter(active=True)
    return render(request, "dashboard.html", {"alignments": alignments})


# -----------------------------
# Phone GPS
# -----------------------------
@login_required
def phone_gps(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        messages.error(request, f"Could not load DXF file: {alignment.dxf_file}")
        return redirect("dashboard")

    gps_line = get_alignment_gps_line(data["points"])

    return render(request, "phone_gps.html", {
        "alignment":  alignment,
        "gps_line":   json.dumps(gps_line),
        "total":      round(data["total_length"], 3),
    })


# -----------------------------
# Capture feature
# -----------------------------
@login_required
def capture(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        messages.error(request, f"Could not load DXF file: {alignment.dxf_file}")
        return redirect("dashboard")

    gps_line      = get_alignment_gps_line(data["points"])
    feature_types = FeatureCapture.FEATURE_TYPES

    if request.method == "POST":
        try:
            lat = float(request.POST.get("latitude"))
            lon = float(request.POST.get("longitude"))
        except (TypeError, ValueError):
            messages.error(request, "No GPS location captured — please get your location first.")
            return render(request, "capture.html", {
                "alignment":         alignment,
                "gps_line":          json.dumps(gps_line),
                "feature_types":     feature_types,
                "total":             round(data["total_length"], 3),
            })

        projected    = gps_to_projected(data["points"], data["cum_dist"], lat, lon)
        feature_type = request.POST.get("feature_type", "")
        custom_type  = request.POST.get("custom_feature_type", "")
        photo        = request.FILES.get("photo")

        FeatureCapture.objects.create(
            alignment             = alignment,
            feature_type          = feature_type,
            custom_feature_type   = custom_type,
            side                  = request.POST.get("side", "NA"),
            condition             = request.POST.get("condition", "GOOD"),
            offset_from_edge_m    = float(request.POST.get("offset_from_edge_m", 0) or 0),
            distance_along_edge_m = float(request.POST.get("distance_along_edge_m", 0) or 0),
            notes                 = request.POST.get("notes", ""),
            chainage_m            = projected["chainage"],
            distance_from_alignment_m = projected["distance_from_alignment"],
            latitude              = projected["latitude"],
            longitude             = projected["longitude"],
            easting               = projected["easting"],
            northing              = projected["northing"],
            photo                 = photo,
            gps_accuracy_m        = float(request.POST.get("gps_accuracy", 0) or 0),
            captured_by           = request.user,
        )

        messages.success(
            request,
            f"✅ Captured: {custom_type or feature_type} at chainage {projected['chainage']}m"
        )
        return redirect("capture", alignment_id=alignment_id)

    return render(request, "capture.html", {
        "alignment":         alignment,
        "gps_line":          json.dumps(gps_line),
        "feature_types":     feature_types,
        "total":             round(data["total_length"], 3),
    })


# -----------------------------
# Passing places
# -----------------------------
@login_required
def passing_places(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        messages.error(request, f"Could not load DXF file: {alignment.dxf_file}")
        return redirect("dashboard")

    gps_line  = get_alignment_gps_line(data["points"])
    next_id   = get_next_pp_id(alignment)
    pp_list   = PassingPlace.objects.filter(alignment=alignment)

    return render(request, "passing_places.html", {
        "alignment": alignment,
        "gps_line":  json.dumps(gps_line),
        "next_id":   next_id,
        "pp_list":   pp_list,
        "total":     round(data["total_length"], 3),
    })


# -----------------------------
# View captured points
# -----------------------------
@login_required
def view_points(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        messages.error(request, f"Could not load DXF file: {alignment.dxf_file}")
        return redirect("dashboard")

    gps_line = get_alignment_gps_line(data["points"])
    features = FeatureCapture.objects.filter(alignment=alignment)
    pp_list  = PassingPlace.objects.filter(alignment=alignment)

    return render(request, "view_points.html", {
        "alignment": alignment,
        "gps_line":  json.dumps(gps_line),
        "features":  features,
        "pp_list":   pp_list,
    })


# -----------------------------
# Tools — Chainage ↔ GPS
# -----------------------------
@login_required
def tools(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        messages.error(request, f"Could not load DXF file: {alignment.dxf_file}")
        return redirect("dashboard")

    gps_line        = get_alignment_gps_line(data["points"])
    ch_result       = None
    gps_result      = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "chainage_to_gps":
            try:
                chainage  = float(request.POST.get("chainage", 0))
                ch_result = chainage_to_gps(data["points"], data["cum_dist"], chainage)
            except (ValueError, TypeError):
                messages.error(request, "Invalid chainage value.")

        elif action == "gps_to_chainage":
            try:
                lat        = float(request.POST.get("latitude", 0))
                lon        = float(request.POST.get("longitude", 0))
                gps_result = gps_to_projected(data["points"], data["cum_dist"], lat, lon)
            except (ValueError, TypeError):
                messages.error(request, "Invalid coordinates.")

    return render(request, "tools.html", {
        "alignment":  alignment,
        "gps_line":   json.dumps(gps_line),
        "total":      round(data["total_length"], 3),
        "ch_result":  ch_result,
        "gps_result": gps_result,
    })


# -----------------------------
# AJAX — GPS to chainage
# -----------------------------
@login_required
def api_gps_to_chainage(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        return JsonResponse({"error": "DXF file not found"}, status=404)

    try:
        body   = json.loads(request.body)
        lat    = float(body["latitude"])
        lon    = float(body["longitude"])
        result = gps_to_projected(data["points"], data["cum_dist"], lat, lon)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# -----------------------------
# AJAX — chainage to GPS
# -----------------------------
@login_required
def api_chainage_to_gps(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        return JsonResponse({"error": "DXF file not found"}, status=404)

    try:
        body     = json.loads(request.body)
        chainage = float(body["chainage"])
        result   = chainage_to_gps(data["points"], data["cum_dist"], chainage)
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# -----------------------------
# AJAX — save feature capture
# -----------------------------
@login_required
def api_capture(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        return JsonResponse({"error": "DXF file not found"}, status=404)

    try:
        body        = json.loads(request.body)
        lat         = float(body["latitude"])
        lon         = float(body["longitude"])
        projected   = gps_to_projected(data["points"], data["cum_dist"], lat, lon)

        feature_type = body.get("feature_type", "")
        custom       = body.get("custom_feature_type", "")

        FeatureCapture.objects.create(
            alignment             = alignment,
            feature_type          = feature_type,
            custom_feature_type   = custom,
            side                  = body.get("side", "NA"),
            condition             = body.get("condition", "GOOD"),
            offset_from_edge_m    = float(body.get("offset_from_edge_m", 0)),
            distance_along_edge_m = float(body.get("distance_along_edge_m", 0)),
            notes                 = body.get("notes", ""),
            chainage_m            = projected["chainage"],
            distance_from_alignment_m = projected["distance_from_alignment"],
            latitude              = projected["latitude"],
            longitude             = projected["longitude"],
            easting               = projected["easting"],
            northing              = projected["northing"],
            captured_by           = request.user,
        )
        return JsonResponse({"success": True, "chainage": projected["chainage"]})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# -----------------------------
# AJAX — save passing place
# -----------------------------
@login_required
def api_passing_place(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    data      = get_alignment_data(alignment)
    if data is None:
        return JsonResponse({"error": "DXF file not found"}, status=404)

    try:
        body      = json.loads(request.body)
        lat       = float(body["latitude"])
        lon       = float(body["longitude"])
        projected = gps_to_projected(data["points"], data["cum_dist"], lat, lon)
        next_id   = get_next_pp_id(alignment)

        PassingPlace.objects.create(
            alignment      = alignment,
            pp_id          = next_id,
            side           = body.get("side", "LHS"),
            status         = body.get("status", "Existing"),
            mid_chainage_m = projected["chainage"],
            mid_latitude   = projected["latitude"],
            mid_longitude  = projected["longitude"],
            mid_easting    = projected["easting"],
            mid_northing   = projected["northing"],
            width_m        = float(body.get("width_m", 0)),
            length_m       = float(body.get("length_m", 0)),
            notes          = body.get("notes", ""),
            gps_accuracy_m = float(body.get("gps_accuracy_m", 0) or 0),
            captured_by    = request.user,
        )
        return JsonResponse({"success": True, "pp_id": next_id, "chainage": projected["chainage"]})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


# -----------------------------
# Delete passing place
# -----------------------------
@login_required
def delete_passing_place(request, pp_id):
    pp = get_object_or_404(PassingPlace, id=pp_id)
    alignment_id = pp.alignment.id
    pp.delete()
    messages.success(request, "Passing place deleted.")
    return redirect("view_points", alignment_id=alignment_id)


# -----------------------------
# Delete feature
# -----------------------------
@login_required
def delete_feature(request, feature_id):
    feature = get_object_or_404(FeatureCapture, id=feature_id)
    alignment_id = feature.alignment.id
    feature.delete()
    messages.success(request, "Feature deleted.")
    return redirect("view_points", alignment_id=alignment_id)
@login_required
def export_features_csv(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    features  = FeatureCapture.objects.filter(alignment=alignment)
    stem      = alignment.dxf_file.replace(".dxf", "")
    filename  = f"{stem}_points_{datetime.now().strftime('%Y%m%d')}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "Feature Type", "Side", "Condition",
        "Offset from Edge (m)", "Distance Along Edge (m)",
        "Chainage (m)", "Distance from Alignment (m)",
        "Latitude", "Longitude", "Easting", "Northing",
        "GPS Accuracy (m)", "Notes", "Captured By", "Captured At"
    ])
    for f in features:
        writer.writerow([
            f.id, f.get_feature_label(), f.side, f.condition,
            f.offset_from_edge_m, f.distance_along_edge_m,
            f.chainage_m, f.distance_from_alignment_m,
            f.latitude, f.longitude, f.easting, f.northing,
            f.gps_accuracy_m,
            f.notes, f.captured_by.username if f.captured_by else "",
            f.captured_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    return response


# -----------------------------
# Export passing places CSV
# -----------------------------
@login_required
def export_passing_places_csv(request, alignment_id):
    alignment = get_object_or_404(Alignment, id=alignment_id, active=True)
    pp_list   = PassingPlace.objects.filter(alignment=alignment)
    stem      = alignment.dxf_file.replace(".dxf", "")
    filename  = f"{stem}_passing_places_{datetime.now().strftime('%Y%m%d')}.csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "ID", "PP ID", "Side", "Status",
        "Mid Chainage (m)", "Mid Latitude", "Mid Longitude",
        "Mid Easting", "Mid Northing",
        "Width (m)", "Length (m)",
        "GPS Accuracy (m)", "Notes", "Captured By", "Captured At"
    ])
    for pp in pp_list:
        writer.writerow([
            pp.id, pp.pp_id, pp.side, pp.status,
            pp.mid_chainage_m, pp.mid_latitude, pp.mid_longitude,
            pp.mid_easting, pp.mid_northing,
            pp.width_m, pp.length_m,
            pp.gps_accuracy_m,
            pp.notes, pp.captured_by.username if pp.captured_by else "",
            pp.captured_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    return response
