from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserRegisterSerializer, UserProfileSerializer, AdminUserUpdateSerializer
from .models import User
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        serializer = UserProfileSerializer(user)
        data['user'] = serializer.data
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegisterSerializer


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = UserProfileSerializer(user)
        return Response(serializer.data)

    def put(self, request):
        user = request.user
        serializer = UserProfileSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id):
        """
        Permite a los administradores obtener información detallada de un usuario específico
        """
        if request.user.role != 'ADMINISTRATIVO':
            return Response(
                {"detail": "No tienes permiso para ver detalles de usuarios."},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = User.objects.get(id=user_id)
            serializer = UserProfileSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, user_id):
        """
        Permite a los administradores actualizar la información de cualquier usuario
        """
        if request.user.role != 'ADMINISTRATIVO':
            return Response(
                {"detail": "No tienes permiso para actualizar usuarios."},
                status=status.HTTP_403_FORBIDDEN
            )

        # Obtener el usuario a actualizar
        try:
            user_to_update = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {"detail": "Usuario no encontrado."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Actualizar el usuario usando el serializador con permisos de administrador
        serializer = AdminUserUpdateSerializer(user_to_update, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "detail": f"Usuario {user_to_update.username} actualizado correctamente.",
                "user": UserProfileSerializer(user_to_update).data
            })

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminUserDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, user_id):
        if request.user.role != 'ADMINISTRATIVO':
            return Response(
                {"detail": "No tienes permiso para eliminar usuarios."},
                status=status.HTTP_403_FORBIDDEN
            )

        user_to_delete = get_object_or_404(User, id=user_id)
        username = user_to_delete.username
        user_to_delete.delete()

        return Response(
            {"detail": f"Usuario {username} eliminado correctamente."},
            status=status.HTTP_204_NO_CONTENT
        )


class UserListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['ADMINISTRATIVO', 'PROFESOR']:
            return Response(
                {"detail": "No tienes permiso para listar usuarios."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = User.objects.all()

        rol = request.query_params.get('rol')
        if rol:
            queryset = queryset.filter(role=rol)

        materia_id = request.query_params.get('materia')
        curso_id = request.query_params.get('curso')

        if materia_id and curso_id and rol == 'ESTUDIANTE':
            queryset = queryset.filter(curso__id=curso_id)
        elif curso_id and rol == 'ESTUDIANTE':
            queryset = queryset.filter(curso__id=curso_id)

        serializer = UserProfileSerializer(queryset, many=True)
        return Response(serializer.data)


class EstudiantesListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role not in ['ADMINISTRATIVO', 'PROFESOR']:
            return Response(
                {"detail": "No tienes permiso para listar estudiantes."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = User.objects.filter(role='ESTUDIANTE')

        curso_id = request.query_params.get('curso')
        if curso_id:
            queryset = queryset.filter(curso__id=curso_id)

        serializer = UserProfileSerializer(queryset, many=True)
        return Response(serializer.data)
