from rest_framework import serializers
from .models import Participacion
from apps.usuarios.serializers import UserProfileSerializer
from apps.materias.serializers import MateriaSerializer

class ParticipacionSerializer(serializers.ModelSerializer):
    estudiante_detail = UserProfileSerializer(source='estudiante', read_only=True)
    materia_detail = MateriaSerializer(source='materia', read_only=True)

    class Meta:
        model = Participacion
        fields = ['id', 'estudiante', 'materia', 'fecha', 'tipo', 'descripcion', 'valor',
                 'estudiante_detail', 'materia_detail']
