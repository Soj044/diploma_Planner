"""Token-based auth endpoints for signup/login/refresh/logout/me/introspect."""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings as jwt_api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .auth_serializers import AuthMeSerializer, IntrospectSerializer, LoginSerializer, SignupSerializer, build_auth_user_payload
from .permissions import HasInternalServiceToken


def _get_refresh_cookie_name() -> str:
    return settings.JWT_REFRESH_COOKIE_NAME


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Attach a refresh token cookie for browser-based silent refresh."""

    max_age = int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds())
    response.set_cookie(
        key=_get_refresh_cookie_name(),
        value=refresh_token,
        max_age=max_age,
        httponly=True,
        secure=settings.JWT_REFRESH_COOKIE_SECURE,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
        path=settings.JWT_REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Remove the refresh cookie during logout or invalid refresh handling."""

    response.delete_cookie(
        key=_get_refresh_cookie_name(),
        path=settings.JWT_REFRESH_COOKIE_PATH,
        samesite=settings.JWT_REFRESH_COOKIE_SAMESITE,
    )


def _get_user_from_token(token: AccessToken | RefreshToken):
    """Resolve a user instance from a validated access/refresh token."""

    user_model = get_user_model()
    user_id = token.get(jwt_api_settings.USER_ID_CLAIM)
    if user_id is None:
        return None
    return user_model.objects.filter(id=user_id).first()


def _build_auth_response(user, *, status_code: int = status.HTTP_200_OK) -> Response:
    """Issue access+refresh tokens and shape the standard auth payload."""

    refresh = RefreshToken.for_user(user)
    payload = {
        "access": str(refresh.access_token),
        "user": AuthMeSerializer(build_auth_user_payload(user)).data,
    }
    response = Response(payload, status=status_code)
    _set_refresh_cookie(response, str(refresh))
    return response


class SignupView(APIView):
    """Public signup endpoint that creates an employee role account."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        update_last_login(None, user)
        return _build_auth_response(user, status_code=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Credential login endpoint that issues JWT tokens."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        if not user.is_active:
            return Response({"detail": "User account is inactive."}, status=status.HTTP_401_UNAUTHORIZED)
        update_last_login(None, user)
        return _build_auth_response(user)


class RefreshView(APIView):
    """Silent refresh endpoint that reads refresh token from HttpOnly cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(_get_refresh_cookie_name(), "")
        if not refresh_token:
            return Response({"detail": "Refresh token cookie is missing."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            raw_refresh = RefreshToken(refresh_token)
        except TokenError:
            response = Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        user = _get_user_from_token(raw_refresh)
        if user is None or not user.is_active:
            response = Response({"detail": "User account is inactive."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        serializer = TokenRefreshSerializer(data={"refresh": refresh_token})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError:
            response = Response({"detail": "Invalid refresh token."}, status=status.HTTP_401_UNAUTHORIZED)
            _clear_refresh_cookie(response)
            return response

        payload = {
            "access": serializer.validated_data["access"],
            "user": AuthMeSerializer(build_auth_user_payload(user)).data,
        }
        response = Response(payload, status=status.HTTP_200_OK)
        rotated_refresh = serializer.validated_data.get("refresh")
        if rotated_refresh:
            _set_refresh_cookie(response, str(rotated_refresh))
        else:
            _set_refresh_cookie(response, refresh_token)
        return response


class LogoutView(APIView):
    """Logout endpoint that blacklists refresh token and clears cookie."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.COOKIES.get(_get_refresh_cookie_name(), "")
        if refresh_token:
            try:
                RefreshToken(refresh_token).blacklist()
            except TokenError:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class MeView(APIView):
    """Return current authenticated user context for frontend guards."""

    def get(self, request):
        user_payload = AuthMeSerializer(build_auth_user_payload(request.user)).data
        return Response(user_payload, status=status.HTTP_200_OK)


class IntrospectView(APIView):
    """Validate access token for internal service-to-service role checks."""

    authentication_classes = []
    permission_classes = [HasInternalServiceToken]

    def post(self, request):
        serializer = IntrospectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token_value = serializer.validated_data["token"]
        try:
            access_token = AccessToken(token_value)
        except TokenError:
            return Response({"detail": "Invalid access token."}, status=status.HTTP_401_UNAUTHORIZED)

        user = _get_user_from_token(access_token)
        if user is None:
            return Response({"detail": "Invalid access token."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            return Response({"detail": "User account is inactive."}, status=status.HTTP_403_FORBIDDEN)

        payload = {
            "user_id": user.id,
            "role": user.role,
            "is_active": user.is_active,
            "employee_id": getattr(getattr(user, "employee_profile", None), "id", None),
        }
        return Response(payload, status=status.HTTP_200_OK)
