from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Curso
from .serializers import CursoSerializer
from .flutter_serializers import CursoConEstudiantesYNotasSerializer
from apps.materias.models import Materia
from apps.notas.models import Nota, Periodo
from apps.usuarios.models import User
from apps.notas.serializers import NotaSerializer


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

    @action(detail=True, methods=['post'], url_path='crear-nota')
    def crear_nota(self, request, pk=None):
        """
        Endpoint para crear una nueva nota para un estudiante en una materia y periodo específicos.
        """
        curso = self.get_object()
        data = request.data

        # Validar datos requeridos
        if not all(key in data for key in ['estudiante_id', 'materia_id', 'periodo_id']):
            return Response(
                {"error": "Los campos estudiante_id, materia_id y periodo_id son requeridos."},
                status=status.HTTP_400_BAD_REQUEST
            )

        estudiante_id = data['estudiante_id']
        materia_id = data['materia_id']
        periodo_id = data['periodo_id']

        # Verificar que el estudiante pertenezca al curso
        try:
            estudiante = User.objects.get(id=estudiante_id, curso=curso, role='ESTUDIANTE')
        except User.DoesNotExist:
            return Response(
                {"error": "El estudiante no existe o no pertenece a este curso."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar que la materia pertenezca al curso
        try:
            materia = Materia.objects.get(id=materia_id)
            if materia not in curso.materias.all():
                return Response(
                    {"error": "La materia no pertenece a este curso."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Materia.DoesNotExist:
            return Response(
                {"error": "La materia especificada no existe."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar que el periodo exista
        try:
            periodo = Periodo.objects.get(id=periodo_id)
        except Periodo.DoesNotExist:
            return Response(
                {"error": "El periodo especificado no existe."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Si el usuario es profesor, verificar que sea profesor de la materia
        if request.user.role == 'PROFESOR':
            if not Materia.objects.filter(id=materia_id, profesor=request.user).exists():
                return Response(
                    {"error": "No tienes permisos para añadir notas en esta materia."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Verificar si ya existe una nota para este estudiante, materia y periodo
        if Nota.objects.filter(estudiante=estudiante, materia=materia, periodo=periodo).exists():
            return Response(
                {"error": "Ya existe una nota para este estudiante en esta materia y periodo."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Crear una instancia de serializer con los datos de la nueva nota
        nota_data = {
            'estudiante': estudiante.id,
            'materia': materia.id,
            'periodo': periodo.id,
            'ser_puntaje': data.get('ser_puntaje', 0),
            'saber_puntaje': data.get('saber_puntaje', 0),
            'hacer_puntaje': data.get('hacer_puntaje', 0),
            'decidir_puntaje': data.get('decidir_puntaje', 0),
            'autoevaluacion_ser': data.get('autoevaluacion_ser', 0),
            'autoevaluacion_decidir': data.get('autoevaluacion_decidir', 0),
            'comentario': data.get('comentario', '')
        }

        serializer = NotaSerializer(data=nota_data)
        if serializer.is_valid():
            nota = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['put'], url_path='actualizar-nota/(?P<nota_id>[^/.]+)')
    def actualizar_nota(self, request, pk=None, nota_id=None):
        """
        Endpoint para actualizar una nota existente.
        """
        curso = self.get_object()

        # Obtener la nota que se desea actualizar
        try:
            nota = Nota.objects.get(id=nota_id)
        except Nota.DoesNotExist:
            return Response(
                {"error": "La nota especificada no existe."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar que el estudiante pertenezca al curso
        if nota.estudiante.curso != curso:
            return Response(
                {"error": "Esta nota no pertenece a un estudiante de este curso."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Si el usuario es profesor, verificar que sea profesor de la materia
        if request.user.role == 'PROFESOR':
            if not Materia.objects.filter(id=nota.materia.id, profesor=request.user).exists():
                return Response(
                    {"error": "No tienes permisos para modificar notas en esta materia."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Actualizar los campos de la nota
        data = request.data
        if 'ser_puntaje' in data:
            nota.ser_puntaje = data['ser_puntaje']
        if 'saber_puntaje' in data:
            nota.saber_puntaje = data['saber_puntaje']
        if 'hacer_puntaje' in data:
            nota.hacer_puntaje = data['hacer_puntaje']
        if 'decidir_puntaje' in data:
            nota.decidir_puntaje = data['decidir_puntaje']
        if 'autoevaluacion_ser' in data:
            nota.autoevaluacion_ser = data['autoevaluacion_ser']
        if 'autoevaluacion_decidir' in data:
            nota.autoevaluacion_decidir = data['autoevaluacion_decidir']
        if 'comentario' in data:
            nota.comentario = data['comentario']

        try:
            nota.save()
            serializer = NotaSerializer(nota)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['delete'], url_path='eliminar-nota/(?P<nota_id>[^/.]+)')
    def eliminar_nota(self, request, pk=None, nota_id=None):
        """
        Endpoint para eliminar una nota existente.
        """
        curso = self.get_object()

        # Obtener la nota que se desea eliminar
        try:
            nota = Nota.objects.get(id=nota_id)
        except Nota.DoesNotExist:
            return Response(
                {"error": "La nota especificada no existe."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Verificar que el estudiante pertenezca al curso
        if nota.estudiante.curso != curso:
            return Response(
                {"error": "Esta nota no pertenece a un estudiante de este curso."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Si el usuario es profesor, verificar que sea profesor de la materia
        if request.user.role == 'PROFESOR':
            if not Materia.objects.filter(id=nota.materia.id, profesor=request.user).exists():
                return Response(
                    {"error": "No tienes permisos para eliminar notas en esta materia."},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Eliminar la nota
        nota_id = nota.id  # Guardamos el ID para devolverlo en la respuesta
        nota.delete()

        return Response(
            {"mensaje": "Nota eliminada correctamente", "nota_id": nota_id},
            status=status.HTTP_200_OK
        )

