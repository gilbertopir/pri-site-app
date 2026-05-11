from django.contrib import admin
from .models import UserProfile, Alignment, FeatureCapture, PassingPlace, FeaturePhoto, PassingPlacePhoto


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ["user", "role"]
    list_filter   = ["role"]


@admin.register(Alignment)
class AlignmentAdmin(admin.ModelAdmin):
    list_display    = ["name", "dxf_file", "active", "uploaded_at"]
    list_filter     = ["active"]
    readonly_fields = ["dxf_file"]

    def save_model(self, request, obj, form, change):
        if obj.dxf_upload:
            from pathlib import Path
            obj.dxf_file = Path(obj.dxf_upload.name).name
        super().save_model(request, obj, form, change)


class FeaturePhotoInline(admin.TabularInline):
    model = FeaturePhoto
    extra = 0


@admin.register(FeatureCapture)
class FeatureCaptureAdmin(admin.ModelAdmin):
    list_display    = ["get_feature_label", "alignment", "chainage_m", "side", "condition", "captured_by", "captured_at"]
    list_filter     = ["alignment", "feature_type", "side", "condition"]
    search_fields   = ["notes", "custom_feature_type"]
    readonly_fields = ["captured_at"]
    inlines         = [FeaturePhotoInline]


class PassingPlacePhotoInline(admin.TabularInline):
    model = PassingPlacePhoto
    extra = 0


@admin.register(PassingPlace)
class PassingPlaceAdmin(admin.ModelAdmin):
    list_display    = ["pp_id", "alignment", "mid_chainage_m", "side", "status", "width_m", "length_m", "captured_by", "captured_at"]
    list_filter     = ["alignment", "side", "status"]
    readonly_fields = ["captured_at"]
    inlines         = [PassingPlacePhotoInline]


@admin.register(FeaturePhoto)
class FeaturePhotoAdmin(admin.ModelAdmin):
    list_display = ["feature", "uploaded_at"]


@admin.register(PassingPlacePhoto)
class PassingPlacePhotoAdmin(admin.ModelAdmin):
    list_display = ["passing_place", "uploaded_at"]
