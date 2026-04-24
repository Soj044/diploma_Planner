"""URL config for core-service MVP."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("users.urls")),
    path("api/v1/", include("operations.urls")),
]
