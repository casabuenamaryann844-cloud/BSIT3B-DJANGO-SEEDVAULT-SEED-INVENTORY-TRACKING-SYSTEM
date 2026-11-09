
from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view),
    path("login/", views.login_view, name="login"),
    path("home/", views.home, name="dashboard"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),

    path("inventory/", views.inventory_list, name="inventory_list"),
    path("inventory/export/", views.inventory_export, name="inventory_export"),
    path("inventory/add/", views.inventory_create, name="inventory_create"),
    path(
        "inventory/<int:pk>/edit/",
        views.inventory_edit,
        name="inventory_edit",
    ),
    path(
        "inventory/<int:pk>/delete/",
        views.inventory_delete,
        name="inventory_delete",
    ),

    path(
        "categories/",
        views.seed_categories,
        name="seed_categories",
    ),
    path(
        "locations/",
        views.storage_locations,
        name="storage_locations",
    ),
    path(
        "seed-status/",
        views.seed_status,
        name="seed_status",
    ),
    path(
        "reports/",
        views.inventory_reports,
        name="inventory_reports",
    ),

    path(
        "expiry/",
        views.seed_expiry,
        name="seed_expiry",
    ),
]
