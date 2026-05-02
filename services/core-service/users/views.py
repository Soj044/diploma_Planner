"""DRF viewsets for user accounts."""

from rest_framework import viewsets

from .models import User
from .permissions import IsAdminRole
from .serializers import UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = UserSerializer
    permission_classes = [IsAdminRole]
