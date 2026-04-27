"""DRF serializers for user accounts."""

from rest_framework import serializers

from .employee_profiles import ensure_employee_profile_for_user
from .models import User


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "password",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "last_login",
            "date_joined",
            "updated_at",
        )
        read_only_fields = ("id", "last_login", "date_joined", "updated_at")

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password", None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        ensure_employee_profile_for_user(user)
        return user

    def update(self, instance: User, validated_data: dict) -> User:
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        ensure_employee_profile_for_user(instance)
        return instance
