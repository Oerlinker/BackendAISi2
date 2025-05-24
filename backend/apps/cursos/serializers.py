from rest_framework import serializers
from .models import Curso
from apps.materias.models import Materia

class CursoSerializer(serializers.ModelSerializer):

    materias = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Materia.objects.all()
    )

    class Meta:
        model = Curso
        fields = ['id', 'nombre', 'nivel', 'materias']
