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
