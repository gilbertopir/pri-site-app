from django.contrib import admin
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import connection
from .models import UserProfile, Alignment, FeatureCapture, PassingPlace, FeaturePhoto, PassingPlacePhoto


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display  = ["user", "role"]
    list_filter   = ["role"]


@admin.register(Alignment)
class AlignmentAdmin(admin.ModelAdmin):
    list_display      = ["name", "dxf_file", "active", "uploaded_at"]
    list_filter       = ["active"]
    readonly_fields   = ["dxf_file"]
    change_form_template = "admin/alignment_reset_confirm_form.html"

    def save_model(self, request, obj, form, change):
        if obj.dxf_upload:
            from pathlib import Path
            obj.dxf_file = Path(obj.dxf_upload.name).name
        super().save_model(request, obj, form, change)

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('<int:alignment_id>/reset/', self.admin_site.admin_view(self.reset_view), name='alignment_reset'),
        ]
        return custom + urls

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['reset_url'] = f'/admin/site_app/alignment/{object_id}/reset/'
        return super().change_view(request, object_id, form_url, extra_context)

    def reset_view(self, request, alignment_id):
        alignment = get_object_or_404(Alignment, id=alignment_id)

        if request.method == 'POST':
            confirmed_name = request.POST.get('alignment_name', '').strip()

            if confirmed_name != alignment.name:
                messages.error(request, f'Name did not match. Type exactly: {alignment.name}')
                return redirect(f'/admin/site_app/alignment/{alignment_id}/reset/')

            # Delete all photos from disk
            for f in FeatureCapture.objects.filter(alignment=alignment):
                for fp in f.photos.all():
                    fp.delete()

            for pp in PassingPlace.objects.filter(alignment=alignment):
                for pp_photo in pp.photos.all():
                    pp_photo.delete()

            # Delete all records
            FeatureCapture.objects.filter(alignment=alignment).delete()
            PassingPlace.objects.filter(alignment=alignment).delete()

            # Reset auto-increment counters
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='site_app_featurecapture'")
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='site_app_passingplace'")

            messages.success(request, f'✅ All data for {alignment.name} has been reset. IDs will restart from F001 / PP001.')
            return redirect('/admin/site_app/alignment/')

        return render(request, 'admin/alignment_reset_confirm.html', {
            'alignment': alignment,
            'title':     f'Reset {alignment.name}',
            'opts':      Alignment._meta,
        })


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
