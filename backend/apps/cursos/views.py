from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Curso
from .serializers import CursoSerializer
from .flutter_serializers import CursoConEstudiantesYNotasSerializer
from apps.materias.models import Materia


class IsAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):

        if request.method in permissions.SAFE_METHODS:
            return True


        return request.user and request.user.is_authenticated and request.user.role == 'ADMINISTRATIVO'


class CursoViewSet(viewsets.ModelViewSet):

    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=True, methods=['get'], url_path='estudiantes-con-notas')
    def estudiantes_con_notas(self, request, pk=None):
        """
        Endpoint específico para Flutter que devuelve los estudiantes de un curso con sus notas
        en una materia específica y periodo seleccionado.

        Parámetros de consulta requeridos:
        - materia_id: ID de la materia
        - periodo_id: ID del periodo
        """
        curso = self.get_object()
        materia_id = request.query_params.get('materia_id')
        periodo_id = request.query_params.get('periodo_id')

        # Validar parámetros requeridos
        if not materia_id or not periodo_id:
            return Response(
                {"error": "Los parámetros 'materia_id' y 'periodo_id' son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar que la materia exista
        try:
            materia = Materia.objects.get(id=materia_id)
        except Materia.DoesNotExist:
            return Response(
                {"error": "La materia especificada no existe."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar que la materia pertenezca al curso
        if materia not in curso.materias.all():
            return Response(
                {"error": "La materia especificada no pertenece a este curso."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Si el usuario es un profesor, verificar que sea profesor de la materia
        if request.user.role == 'PROFESOR':
            materias_profesor = Materia.objects.filter(profesor=request.user)
            if materia not in materias_profesor:
                return Response(
                    {"error": "No tienes permisos para ver las notas de esta materia."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Serializar el curso con los estudiantes y sus notas
        serializer = CursoConEstudiantesYNotasSerializer(
            curso,
            context={'materia_id': materia_id, 'periodo_id': periodo_id}
        )

        return Response(serializer.data)
