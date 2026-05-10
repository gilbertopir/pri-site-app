from django.urls import path
from . import views

urlpatterns = [

    # -----------------------------
    # Auth
    # -----------------------------
    path("login/",              views.login_view,           name="login"),
    path("logout/",             views.logout_view,          name="logout"),

    # -----------------------------
    # Dashboard — site selector
    # -----------------------------
    path("",                    views.dashboard,            name="dashboard"),
    path("dashboard/",          views.dashboard,            name="dashboard"),

    # -----------------------------
    # Phone GPS
    # -----------------------------
    path("gps/<int:alignment_id>/",         views.phone_gps,        name="phone_gps"),

    # -----------------------------
    # Capture feature
    # -----------------------------
    path("capture/<int:alignment_id>/",     views.capture,          name="capture"),

    # -----------------------------
    # Passing places
    # -----------------------------
    path("passing-places/<int:alignment_id>/", views.passing_places, name="passing_places"),

    # -----------------------------
    # View captured points
    # -----------------------------
    path("view/<int:alignment_id>/",        views.view_points,      name="view_points"),

    # -----------------------------
    # Tools — Chainage ↔ GPS
    # -----------------------------
    path("tools/<int:alignment_id>/", views.tools, name="tools"),

    # -----------------------------
    # AJAX endpoints — called from JavaScript
    # -----------------------------
    path("api/gps-to-chainage/<int:alignment_id>/",  views.api_gps_to_chainage,  name="api_gps_to_chainage"),
    path("api/chainage-to-gps/<int:alignment_id>/",  views.api_chainage_to_gps,  name="api_chainage_to_gps"),
    path("api/capture/<int:alignment_id>/",          views.api_capture,          name="api_capture"),
    path("api/passing-place/<int:alignment_id>/",    views.api_passing_place,    name="api_passing_place"),

    # -----------------------------
    # Exports
    # -----------------------------
    path("export/features/<int:alignment_id>/",       views.export_features_csv,      name="export_features_csv"),
    path("export/passing-places/<int:alignment_id>/", views.export_passing_places_csv, name="export_passing_places_csv"),
    # -----------------------------
    # Delete records
    # -----------------------------
    path("delete/feature/<int:feature_id>/",       views.delete_feature,       name="delete_feature"),
    path("delete/passing-place/<int:pp_id>/",      views.delete_passing_place, name="delete_passing_place"),

    # -----------------------------
    # Admin export page
    # -----------------------------
    path("admin-export/",                          views.admin_export, name="admin_export"),
    path("admin-export/zip/<int:alignment_id>/",   views.export_zip,   name="export_zip"),
]
