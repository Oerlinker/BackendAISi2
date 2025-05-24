from rest_framework import serializers
from .models import Periodo, Nota
from apps.usuarios.serializers import UserProfileSerializer
from apps.materias.serializers import MateriaSerializer


class PeriodoSerializer(serializers.ModelSerializer):
    trimestre_display = serializers.CharField(source='get_trimestre_display', read_only=True)

    class Meta:
        model = Periodo
        fields = ['id', 'nombre', 'trimestre', 'trimestre_display', 'año_academico', 'fecha_inicio', 'fecha_fin']


class NotaSerializer(serializers.ModelSerializer):
    estudiante_detail = UserProfileSerializer(source='estudiante', read_only=True)
    materia_detail = MateriaSerializer(source='materia', read_only=True)
    periodo_detail = PeriodoSerializer(source='periodo', read_only=True)

    ser_total = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    decidir_total = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    nota_total = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    aprobado = serializers.BooleanField(read_only=True)

    class Meta:
        model = Nota
        fields = [
            'id', 'estudiante', 'materia', 'periodo',
            'estudiante_detail', 'materia_detail', 'periodo_detail',
            'ser_puntaje', 'saber_puntaje', 'hacer_puntaje', 'decidir_puntaje',
            'autoevaluacion_ser', 'autoevaluacion_decidir',
            'ser_total', 'decidir_total', 'nota_total', 'aprobado',
            'fecha_registro', 'ultima_modificacion', 'comentario'
        ]
        read_only_fields = ['fecha_registro', 'ultima_modificacion']

    def validate(self, data):

        if 'decidir_puntaje' in data and data['decidir_puntaje'] > 10:
            raise serializers.ValidationError({"decidir_puntaje": "El puntaje de decidir no puede ser mayor a 10."})

        if 'autoevaluacion_ser' in data and data['autoevaluacion_ser'] > 5:
            raise serializers.ValidationError(
                {"autoevaluacion_ser": "La autoevaluación del ser no puede ser mayor a 5."})

        if 'autoevaluacion_decidir' in data and data['autoevaluacion_decidir'] > 5:
            raise serializers.ValidationError(
                {"autoevaluacion_decidir": "La autoevaluación del decidir no puede ser mayor a 5."})

        return data


class NotaEstudianteSerializer(NotaSerializer):
    class Meta(NotaSerializer.Meta):
        read_only_fields = NotaSerializer.Meta.read_only_fields + [
            'ser_puntaje', 'saber_puntaje', 'hacer_puntaje', 'decidir_puntaje', 'comentario'
        ]
