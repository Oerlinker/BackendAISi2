from rest_framework import serializers
from .models import Asistencia
from apps.usuarios.serializers import UserProfileSerializer
from apps.materias.serializers import MateriaSerializer

class AsistenciaSerializer(serializers.ModelSerializer):
    estudiante_detail = UserProfileSerializer(source='estudiante', read_only=True)
    materia_detail = MateriaSerializer(source='materia', read_only=True)

    class Meta:
        model = Asistencia
        fields = ['id', 'estudiante', 'materia', 'fecha', 'presente', 'justificacion',
                 'estudiante_detail', 'materia_detail']

class AsistenciaListSerializer(serializers.ModelSerializer):

    estudiante_nombre = serializers.CharField(source='estudiante.get_full_name', read_only=True)
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)

    class Meta:
        model = Asistencia
        fields = ['id', 'estudiante', 'materia', 'fecha', 'presente', 'justificacion',
                 'estudiante_nombre', 'materia_nombre']

