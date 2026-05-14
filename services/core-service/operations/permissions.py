"""Role-aware permissions for core-service CRUD and planner boundaries."""

import secrets

from django.conf import settings
from rest_framework.permissions import BasePermission


class RoleActionPermission(BasePermission):
    """Map DRF viewset actions to roles with deny-by-default behavior."""

    admin_actions = {"*"}
    manager_actions: set[str] = set()
    employee_actions: set[str] = set()

    def _allowed_actions_for_role(self, role: str) -> set[str] | None:
        if role == "admin":
            return self.admin_actions
        if role == "manager":
            return self.manager_actions
        if role == "employee":
            return self.employee_actions
        return None

    def _is_action_allowed(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False

        action = getattr(view, "action", None)
        if action is None:
            return False
        allowed_actions = self._allowed_actions_for_role(getattr(user, "role", ""))
        if not allowed_actions:
            return False
        return "*" in allowed_actions or action in allowed_actions

    def has_permission(self, request, view) -> bool:
        return self._is_action_allowed(request, view)

    def has_object_permission(self, request, view, obj) -> bool:
        return self._is_action_allowed(request, view)


class EmployeeOwnedObjectPermission(RoleActionPermission):
    """Permission with object ownership checks for employee self-scope CRUD."""

    owner_attr_path = ""

    def _owner_employee_id(self, obj) -> int | None:
        current = obj
        for attr in self.owner_attr_path.split("."):
            current = getattr(current, attr, None)
            if current is None:
                return None
        return current

    def has_object_permission(self, request, view, obj) -> bool:
        if not super().has_object_permission(request, view, obj):
            return False

        if getattr(request.user, "role", "") != "employee":
            return True

        employee_profile = getattr(request.user, "employee_profile", None)
        if employee_profile is None:
            return False
        return self._owner_employee_id(obj) == employee_profile.id


class DepartmentPermission(RoleActionPermission):
    manager_actions = {"list", "retrieve"}
    employee_actions = {"list", "retrieve"}


class SkillPermission(RoleActionPermission):
    manager_actions = {"list", "retrieve", "create", "update", "partial_update"}
    employee_actions = {"list", "retrieve"}


class EmployeePermission(RoleActionPermission):
    manager_actions = {"list", "retrieve"}


class EmployeeSkillPermission(RoleActionPermission):
    manager_actions = {"list", "retrieve"}


class WorkSchedulePermission(EmployeeOwnedObjectPermission):
    manager_actions = {"list", "retrieve", "create", "update", "partial_update", "destroy"}
    employee_actions = {"list", "retrieve"}
    owner_attr_path = "employee_id"


class WorkScheduleDayPermission(EmployeeOwnedObjectPermission):
    manager_actions = {"list", "retrieve", "create", "update", "partial_update", "destroy"}
    employee_actions = {"list", "retrieve"}
    owner_attr_path = "schedule.employee_id"


class EmployeeLeavePermission(EmployeeOwnedObjectPermission):
    admin_actions = {"list", "retrieve", "set_status"}
    manager_actions = {"list", "retrieve", "set_status"}
    employee_actions = {"list", "retrieve", "create", "update", "partial_update", "destroy"}
    owner_attr_path = "employee_id"

    def has_object_permission(self, request, view, obj) -> bool:
        if not super().has_object_permission(request, view, obj):
            return False

        if getattr(request.user, "role", "") != "employee":
            return True

        action = getattr(view, "action", None)
        if action in {"update", "partial_update", "destroy"} and obj.status != "requested":
            return False
        return True


class AvailabilityOverridePermission(RoleActionPermission):
    manager_actions = {"list", "retrieve", "create", "update", "partial_update", "destroy"}


class TaskPermission(RoleActionPermission):
    manager_actions = {"list", "retrieve", "create", "update", "partial_update"}
    employee_actions = {"list", "retrieve"}


class TaskRequirementPermission(RoleActionPermission):
    manager_actions = {"list", "retrieve", "create", "update", "partial_update", "destroy"}
    employee_actions = {"list", "retrieve"}


class AssignmentPermission(EmployeeOwnedObjectPermission):
    admin_actions = {"list", "retrieve", "approve_proposal", "manual", "reject"}
    manager_actions = {"list", "retrieve", "approve_proposal", "manual", "reject"}
    employee_actions = {"list", "retrieve"}
    owner_attr_path = "employee_id"


class AssignmentChangeLogPermission(RoleActionPermission):
    manager_actions = {"list", "retrieve"}


class SchedulePreviewPermission(BasePermission):
    """Allow authenticated schedule preview reads for operational roles."""

    message = "Authentication credentials were not provided."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated or not user.is_active:
            return False
        return getattr(user, "role", "") in {"admin", "manager", "employee"}


class PlannerApprovalPermission(RoleActionPermission):
    """Explicit allow-list for assignment approval handoff endpoint."""

    admin_actions = {"approve_proposal"}
    manager_actions = {"approve_proposal"}


class InternalPlannerServiceTokenPermission(BasePermission):
    """Allow planner integration only with a shared internal service token."""

    message = "Authentication credentials were not provided."

    def has_permission(self, request, view) -> bool:
        internal_token = getattr(settings, "INTERNAL_SERVICE_TOKEN", "")
        request_token = request.headers.get("X-Internal-Service-Token", "")
        if not internal_token or not request_token:
            return False

        return secrets.compare_digest(request_token, internal_token)
