"""Serializers for token-based authentication endpoints in core-service."""

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .employee_profiles import ensure_employee_profile_for_user


class InvalidCredentialsError(APIException):
    """Credential error with explicit 401 status for auth endpoints."""

    status_code = 401
    default_detail = "Invalid email or password."
    default_code = "invalid_credentials"


class AuthEmployeeProfileSerializer(serializers.Serializer):
    """Compact employee profile embedded into auth payloads."""

    id = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    department_id = serializers.IntegerField(allow_null=True, read_only=True)
    position_name = serializers.CharField(read_only=True)
    hire_date = serializers.DateField(allow_null=True, read_only=True)
    is_active = serializers.BooleanField(read_only=True)


class AuthMeSerializer(serializers.Serializer):
    """Compact user profile returned by auth/me and login/signup endpoints."""

    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)
    is_active = serializers.BooleanField(read_only=True)
    employee_id = serializers.IntegerField(allow_null=True, read_only=True)
    employee_profile = AuthEmployeeProfileSerializer(allow_null=True, read_only=True)


def build_auth_user_payload(user) -> dict:
    """Build an auth-focused payload with role and employee context."""

    employee = getattr(user, "employee_profile", None)
    employee_id = None
    employee_profile = None
    if employee:
        employee_id = employee.id
        employee_profile = {
            "id": employee.id,
            "full_name": employee.full_name,
            "department_id": employee.department_id,
            "position_name": employee.position_name,
            "hire_date": employee.hire_date,
            "is_active": employee.is_active,
        }
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "employee_id": employee_id,
        "employee_profile": employee_profile,
    }


class SignupSerializer(serializers.Serializer):
    """Public signup serializer that always creates an employee-role account."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8, trim_whitespace=False)
    username = serializers.CharField(required=False, allow_blank=True, max_length=150)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_email(self, value: str) -> str:
        user_model = get_user_model()
        if user_model.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value.lower()

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            return value
        user_model = get_user_model()
        if user_model.objects.filter(username=value).exists():
            raise serializers.ValidationError("User with this username already exists.")
        return value

    def _generate_username(self, email: str) -> str:
        user_model = get_user_model()
        base = email.split("@", 1)[0].strip() or "user"
        base = base[:150]
        candidate = base
        suffix = 1
        while user_model.objects.filter(username=candidate).exists():
            suffix_text = f"-{suffix}"
            candidate = f"{base[: 150 - len(suffix_text)]}{suffix_text}"
            suffix += 1
        return candidate

    def create(self, validated_data: dict):
        user_model = get_user_model()
        password = validated_data.pop("password")
        email = validated_data.pop("email")
        username = validated_data.pop("username", "").strip()
        user = user_model(
            email=email,
            username=username or self._generate_username(email=email),
            role=user_model.Role.EMPLOYEE,
            **validated_data,
        )
        user.set_password(password)
        user.save()
        ensure_employee_profile_for_user(user)
        return user


class LoginSerializer(serializers.Serializer):
    """Validate credentials and expose the authenticated user."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email", "").lower()
        password = attrs.get("password", "")
        user = authenticate(request=self.context.get("request"), username=email, password=password)
        if user is None:
            raise InvalidCredentialsError()
        attrs["user"] = user
        return attrs


class IntrospectSerializer(serializers.Serializer):
    """Payload serializer for access token introspection."""

    token = serializers.CharField(trim_whitespace=True)
