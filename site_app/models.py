from django.db import models
from django.contrib.auth.models import User


# -----------------------------
# User Profile — extends Django's built-in User
# adds role (field engineer or reviewer)
# -----------------------------
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("engineer", "Field Engineer"),
        ("reviewer", "Reviewer (Read Only)"),
    ]
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role        = models.CharField(max_length=20, choices=ROLE_CHOICES, default="engineer")

    def is_engineer(self):
        return self.role == "engineer"

    def is_reviewer(self):
        return self.role == "reviewer"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


# -----------------------------
# Alignment — represents a DXF file / site
# -----------------------------
class Alignment(models.Model):
    name        = models.CharField(max_length=100)
    dxf_file    = models.CharField(max_length=255)
    dxf_upload  = models.FileField(upload_to="dxf_files/", blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    active      = models.BooleanField(default=True)

    def delete(self, *args, **kwargs):
        # Delete the uploaded DXF file from disk when record is deleted
        if self.dxf_upload:
            import os
            if os.path.isfile(self.dxf_upload.path):
                os.remove(self.dxf_upload.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]


# -----------------------------
# Feature Capture — a point feature recorded on site
# -----------------------------
class FeatureCapture(models.Model):
    SIDE_CHOICES = [
        ("LHS",  "Left Hand Side"),
        ("RHS",  "Right Hand Side"),
        ("BOTH", "Both Sides"),
        ("NA",   "Not Applicable"),
    ]
    CONDITION_CHOICES = [
        ("GOOD",    "Good"),
        ("FAIR",    "Fair"),
        ("POOR",    "Poor"),
        ("DAMAGED", "Damaged"),
    ]
    FEATURE_TYPES = [
        ("Accesses / driveways",      "Accesses / driveways"),
        ("Bollards",                  "Bollards"),
        ("Bus stops / laybys",        "Bus stops / laybys"),
        ("Cabinets / comms boxes",    "Cabinets / comms boxes"),
        ("Culverts / headwalls",      "Culverts / headwalls"),
        ("Cuttings",                  "Cuttings"),
        ("Drainage ditches",          "Drainage ditches"),
        ("Edge break-up",             "Edge break-up"),
        ("Embankments",               "Embankments"),
        ("Existing walls",            "Existing walls"),
        ("Fencing",                   "Fencing"),
        ("Gates",                     "Gates"),
        ("Gullies",                   "Gullies"),
        ("Hedges",                    "Hedges"),
        ("Junctions",                 "Junctions"),
        ("Kerbs / edging",            "Kerbs / edging"),
        ("Lighting columns",          "Lighting columns"),
        ("Manholes / chambers",       "Manholes / chambers"),
        ("Overhead lines / poles",    "Overhead lines / poles"),
        ("Pavement defects",          "Pavement defects"),
        ("Ponding / drainage issues", "Ponding / drainage issues"),
        ("Retaining walls",           "Retaining walls"),
        ("Road markings",             "Road markings"),
        ("Sign faces",                "Sign faces"),
        ("Sign posts",                "Sign posts"),
        ("Traffic signals",           "Traffic signals"),
        ("Trees",                     "Trees"),
        ("Utility covers",            "Utility covers"),
        ("Utility marker posts",      "Utility marker posts"),
        ("Verge edges",               "Verge edges"),
        ("VRS",                       "VRS"),
        ("Watercourses",              "Watercourses"),
        ("Custom / Other",            "Custom / Other"),
    ]

    alignment             = models.ForeignKey(Alignment, on_delete=models.CASCADE, related_name="features")
    feature_id            = models.CharField(max_length=20, blank=True, default="")
    feature_type          = models.CharField(max_length=100, choices=FEATURE_TYPES)
    custom_feature_type   = models.CharField(max_length=100, blank=True)
    side                  = models.CharField(max_length=10, choices=SIDE_CHOICES)
    condition             = models.CharField(max_length=10, choices=CONDITION_CHOICES)
    offset_from_edge_m    = models.FloatField(default=0.0)
    distance_along_edge_m = models.FloatField(default=0.0)
    notes                 = models.TextField(blank=True)
    chainage_m            = models.FloatField()
    distance_from_alignment_m = models.FloatField()
    latitude              = models.FloatField()
    longitude             = models.FloatField()
    easting               = models.FloatField()
    northing              = models.FloatField()
    gps_accuracy_m        = models.FloatField(null=True, blank=True)
    entry_method          = models.CharField(max_length=10, default="GPS",
                               choices=[("GPS", "GPS Capture"), ("Manual", "Manual Entry")])
    captured_by           = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="features")
    captured_at           = models.DateTimeField(auto_now_add=True)

    def get_feature_label(self):
        if self.feature_type == "Custom / Other" and self.custom_feature_type:
            return self.custom_feature_type
        return self.feature_type

    def __str__(self):
        return f"{self.get_feature_label()} — Ch: {self.chainage_m}m"

    class Meta:
        ordering = ["chainage_m"]


# -----------------------------
# Passing Place
# -----------------------------
class PassingPlace(models.Model):
    SIDE_CHOICES = [
        ("LHS", "Left Hand Side"),
        ("RHS", "Right Hand Side"),
    ]
    STATUS_CHOICES = [
        ("Existing", "Existing"),
        ("New",      "New"),
    ]

    alignment     = models.ForeignKey(Alignment, on_delete=models.CASCADE, related_name="passing_places")
    pp_id         = models.CharField(max_length=10)
    side          = models.CharField(max_length=10, choices=SIDE_CHOICES)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES)
    mid_chainage_m= models.FloatField()
    mid_latitude  = models.FloatField()
    mid_longitude = models.FloatField()
    mid_easting   = models.FloatField()
    mid_northing  = models.FloatField()
    width_m       = models.FloatField(default=0.0)
    length_m      = models.FloatField(default=0.0)
    notes         = models.TextField(blank=True)
    gps_accuracy_m = models.FloatField(null=True, blank=True)
    entry_method   = models.CharField(max_length=10, default="GPS",
                        choices=[("GPS", "GPS Capture"), ("Manual", "Manual Entry")])
    captured_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="passing_places")
    captured_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.pp_id} — Ch: {self.mid_chainage_m}m ({self.side})"

    class Meta:
        ordering = ["mid_chainage_m"]


# -----------------------------
# Feature Photos
# -----------------------------
class FeaturePhoto(models.Model):
    feature     = models.ForeignKey(FeatureCapture, on_delete=models.CASCADE, related_name="photos")
    photo       = models.ImageField(upload_to="photos/features/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        import os
        if self.photo and os.path.isfile(self.photo.path):
            os.remove(self.photo.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Photo for {self.feature} — {self.uploaded_at}"


# -----------------------------
# Passing Place Photos
# -----------------------------
class PassingPlacePhoto(models.Model):
    passing_place = models.ForeignKey(PassingPlace, on_delete=models.CASCADE, related_name="photos")
    photo         = models.ImageField(upload_to="photos/passing_places/")
    uploaded_at   = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        import os
        if self.photo and os.path.isfile(self.photo.path):
            os.remove(self.photo.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Photo for {self.passing_place} — {self.uploaded_at}"


# -----------------------------
# Structure
# -----------------------------
class Structure(models.Model):

    FEATURE_TYPES = [
        ("Bridge",              "Bridge"),
        ("Arch Bridge",         "Arch Bridge"),
        ("Gabions",             "Gabions"),
        ("Multi-Cell Structure","Multi-Cell Structure"),
        ("Roadside Structure",  "Roadside Structure"),
        ("Arch",                "Arch"),
        ("Abutment",            "Abutment"),
        ("Approaches",          "Approaches"),
        ("Beam",                "Beam"),
        ("Cill-Unit",           "Cill-Unit"),
        ("Column / Pier",       "Column / Pier"),
        ("Culvert",             "Culvert"),
        ("Cutting",             "Cutting"),
        ("Embankment",          "Embankment"),
        ("Headwall",            "Headwall"),
        ("Retaining Wall",      "Retaining Wall"),
        ("Watercourse",         "Watercourse"),
        ("Wingwall",            "Wingwall"),
        ("Other",               "Other"),
    ]

    SIDE_CHOICES = [
        ("LHS", "Left Hand Side"),
        ("RHS", "Right Hand Side"),
        ("N/A", "Not Applicable"),
    ]

    CONDITION_CHOICES = [
        ("GOOD", "Good"),
        ("FAIR", "Fair"),
        ("POOR", "Poor"),
    ]

    ACTION_CHOICES = [
        ("No Action", "No Action"),
        ("Monitor",   "Monitor"),
        ("Protect",   "Protect"),
        ("Modify",    "Modify"),
        ("Replace",   "Replace"),
    ]

    BED_JOINT_CHOICES = [
        ("up_to_6mm",       "Widths up to 6mm"),
        ("6mm_to_12.5mm",   "Widths between 6mm and 12.5mm"),
        ("over_12.5mm",     "Widths over 12.5mm"),
    ]

    ARCH_JOINT_CHOICES = [
        ("pointed_good",       "Pointed joints in good condition"),
        ("unpointed_poor",     "Un-pointed joints, poor condition and insufficiently filled to 12.5mm from edge"),
        ("10pct_unfilled",     "With 10% of the thickness insufficiently filled"),
        ("10_30pct_unfilled",  "Insufficiently filled for more than 10% but less than 30% of the thickness of the barrel"),
    ]

    MORTAR_STRENGTH_CHOICES = [
        ("Crumbly", "Crumbly"),
        ("Solid",   "Solid"),
    ]

    MORTAR_BARREL_CHOICES = [
        ("Good",            "Good"),
        ("Loose_Friable",   "Loose or Friable"),
    ]

    # --- ID & Classification ---
    alignment           = models.ForeignKey(Alignment, on_delete=models.CASCADE, related_name="structures")
    structure_id        = models.CharField(max_length=20, blank=True, default="")
    structure_name      = models.CharField(max_length=200, blank=True)
    feature_type        = models.CharField(max_length=50, choices=FEATURE_TYPES)
    custom_feature_type = models.CharField(max_length=100, blank=True)

    # --- Detail Data & Dims (mm) ---
    bed_thickness_mm        = models.FloatField(null=True, blank=True)
    rise_mm                 = models.FloatField(null=True, blank=True)
    rise_quarter_points_mm  = models.FloatField(null=True, blank=True)
    abutment_length_mm      = models.FloatField(null=True, blank=True)
    approx_angle            = models.FloatField(null=True, blank=True)
    span_mm                 = models.FloatField(null=True, blank=True)
    parapet_height_mm       = models.FloatField(null=True, blank=True)
    parapet_thickness_mm    = models.FloatField(null=True, blank=True)
    vehicle_clearance_mm    = models.FloatField(null=True, blank=True)
    footpath_width_mm       = models.FloatField(null=True, blank=True)
    type_of_stone           = models.CharField(max_length=200, blank=True)

    # --- Arch Brick Dims (mm) ---
    arch_brick_d_mm     = models.FloatField(null=True, blank=True)
    arch_brick_b_mm     = models.FloatField(null=True, blank=True)

    # --- Abutment Brick Dims (mm) ---
    abutment_brick_d_mm = models.FloatField(null=True, blank=True)
    abutment_brick_b_mm = models.FloatField(null=True, blank=True)

    # --- Arch Barrel Joints ---
    bed_joint_thickness = models.CharField(max_length=20, choices=BED_JOINT_CHOICES, blank=True)
    arch_barrel_joints  = models.CharField(max_length=30, choices=ARCH_JOINT_CHOICES, blank=True)

    # --- Defects ---
    mortar_strength         = models.CharField(max_length=20, choices=MORTAR_STRENGTH_CHOICES, blank=True)
    mortar_barrel           = models.CharField(max_length=20, choices=MORTAR_BARREL_CHOICES, blank=True)
    arch_barrel_cracking    = models.CharField(max_length=5, choices=[("Yes","Yes"),("No","No")], blank=True)
    defect_location         = models.CharField(max_length=200, blank=True)
    defect_direction        = models.CharField(max_length=200, blank=True)
    defect_thickness        = models.CharField(max_length=200, blank=True)
    recommended_action      = models.CharField(max_length=20, choices=ACTION_CHOICES, blank=True)

    # --- General ---
    side                    = models.CharField(max_length=10, choices=SIDE_CHOICES, blank=True)
    condition               = models.CharField(max_length=10, choices=CONDITION_CHOICES, blank=True)
    offset_from_edge_mm     = models.FloatField(null=True, blank=True)
    distance_along_edge_mm  = models.FloatField(null=True, blank=True)
    notes                   = models.TextField(blank=True)

    # --- Location ---
    chainage_m                = models.FloatField()
    distance_from_alignment_m = models.FloatField()
    latitude                  = models.FloatField()
    longitude                 = models.FloatField()
    easting                   = models.FloatField()
    northing                  = models.FloatField()
    gps_accuracy_m            = models.FloatField(null=True, blank=True)
    entry_method              = models.CharField(max_length=10, default="GPS",
                                   choices=[("GPS","GPS Capture"),("Manual","Manual Entry")])
    captured_by               = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="structures")
    captured_at               = models.DateTimeField(auto_now_add=True)

    def get_feature_label(self):
        if self.feature_type == "Other" and self.custom_feature_type:
            return self.custom_feature_type
        return self.feature_type

    def __str__(self):
        return f"{self.structure_id} — {self.get_feature_label()} — Ch: {self.chainage_m}m"

    class Meta:
        ordering = ["chainage_m"]


# -----------------------------
# Structure Photos
# -----------------------------
class StructurePhoto(models.Model):
    structure   = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name="photos")
    photo       = models.ImageField(upload_to="photos/structures/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def delete(self, *args, **kwargs):
        import os
        if self.photo and os.path.isfile(self.photo.path):
            os.remove(self.photo.path)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"Photo for {self.structure} — {self.uploaded_at}"
