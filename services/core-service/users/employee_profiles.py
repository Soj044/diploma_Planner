"""Helpers to keep user role and employee profile presence in sync."""

from django.apps import apps

from .models import User


def _default_employee_full_name(user: User) -> str:
    full_name = f"{user.first_name} {user.last_name}".strip()
    return full_name or user.email


def ensure_employee_profile_for_user(user: User):
    """Create an employee profile for manager/employee roles when missing."""

    if user.role not in {User.Role.MANAGER, User.Role.EMPLOYEE}:
        return None

    employee_model = apps.get_model("operations", "Employee")
    existing_profile = employee_model.objects.filter(user_id=user.id).first()
    if existing_profile is not None:
        return existing_profile

    return employee_model.objects.create(
        user=user,
        full_name=_default_employee_full_name(user),
        position_name="Pending assignment",
        employment_type=employee_model.EmploymentType.FULL_TIME,
        weekly_capacity_hours=40,
        timezone="UTC",
        hire_date=None,
        is_active=True,
    )
