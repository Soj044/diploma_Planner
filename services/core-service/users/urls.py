"""API routes for user accounts."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .auth_views import IntrospectView, LoginView, LogoutView, MeView, RefreshView, SignupView
from .views import UserViewSet

router = DefaultRouter()
router.register("users", UserViewSet)

urlpatterns = [
    path("auth/signup", SignupView.as_view(), name="auth-signup"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/me", MeView.as_view(), name="auth-me"),
    path("auth/introspect", IntrospectView.as_view(), name="auth-introspect"),
    *router.urls,
]
