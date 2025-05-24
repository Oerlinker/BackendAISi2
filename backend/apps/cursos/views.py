from rest_framework import viewsets, permissions
from .models import Curso
from .serializers import CursoSerializer


class IsAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):

        if request.method in permissions.SAFE_METHODS:
            return True


        return request.user and request.user.is_authenticated and request.user.role == 'ADMINISTRATIVO'


class CursoViewSet(viewsets.ModelViewSet):

    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    permission_classes = [IsAdminOrReadOnly]
