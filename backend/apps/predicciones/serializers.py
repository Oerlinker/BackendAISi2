from rest_framework import serializers
from .models import Prediccion
from apps.usuarios.serializers import UserProfileSerializer
from apps.materias.serializers import MateriaSerializer

class PrediccionSerializer(serializers.ModelSerializer):
    estudiante_detail = UserProfileSerializer(source='estudiante', read_only=True)
    materia_detail = MateriaSerializer(source='materia', read_only=True)

    class Meta:
        model = Prediccion
        fields = ['id', 'estudiante', 'materia', 'fecha_prediccion', 'valor_numerico',
                 'nivel_rendimiento', 'promedio_notas', 'porcentaje_asistencia',
                 'promedio_participaciones', 'confianza', 'estudiante_detail', 'materia_detail']
        read_only_fields = ['fecha_prediccion']
