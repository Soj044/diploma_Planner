"""Admin configuration for core-service users."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CoreUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Workestrator", {"fields": ("role",)}),)
    list_display = ("email", "username", "role", "is_active", "is_staff")
    search_fields = ("email", "username", "first_name", "last_name")
