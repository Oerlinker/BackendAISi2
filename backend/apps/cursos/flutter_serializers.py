from rest_framework import serializers
from .models import Curso
from apps.usuarios.models import User
from apps.notas.models import Nota, Periodo
from django.db.models import Sum

class EstudianteConNotasSerializer(serializers.ModelSerializer):
    """
    Serializer para mostrar información de un estudiante con sus notas en una materia específica.
    """
    nota_id = serializers.IntegerField(source='nota.id', read_only=True, default=None)
    ser_puntaje = serializers.DecimalField(source='nota.ser_puntaje', max_digits=4, decimal_places=2, read_only=True, default=0)
    saber_puntaje = serializers.DecimalField(source='nota.saber_puntaje', max_digits=4, decimal_places=2, read_only=True, default=0)
    hacer_puntaje = serializers.DecimalField(source='nota.hacer_puntaje', max_digits=4, decimal_places=2, read_only=True, default=0)
    decidir_puntaje = serializers.DecimalField(source='nota.decidir_puntaje', max_digits=4, decimal_places=2, read_only=True, default=0)
    nota_total = serializers.DecimalField(source='nota.nota_total', max_digits=5, decimal_places=2, read_only=True, default=0)
    aprobado = serializers.BooleanField(source='nota.aprobado', read_only=True, default=False)
    tiene_nota = serializers.BooleanField(read_only=True, default=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email',
                  'nota_id', 'ser_puntaje', 'saber_puntaje', 'hacer_puntaje',
                  'decidir_puntaje', 'nota_total', 'aprobado', 'tiene_nota']

class CursoConEstudiantesYNotasSerializer(serializers.ModelSerializer):
    """
    Serializer para mostrar un curso con sus estudiantes y las notas de estos en una materia específica.
    """
    estudiantes = serializers.SerializerMethodField()

    class Meta:
        model = Curso
        fields = ['id', 'nombre', 'nivel', 'estudiantes']

    def get_estudiantes(self, curso):
        # Obtener los parámetros de la solicitud a través del contexto
        materia_id = self.context.get('materia_id')
        periodo_id = self.context.get('periodo_id')

        # Obtener todos los estudiantes del curso
        estudiantes = User.objects.filter(curso=curso, role='ESTUDIANTE')

        resultado = []
        for estudiante in estudiantes:
            # Buscar la nota del estudiante para esta materia y periodo específicos
            try:
                nota = Nota.objects.get(
                    estudiante=estudiante,
                    materia_id=materia_id,
                    periodo_id=periodo_id
                )
                estudiante_data = EstudianteConNotasSerializer(estudiante).data
                # Agregar los datos de la nota al estudiante
                estudiante_data['nota_id'] = nota.id
                estudiante_data['ser_puntaje'] = nota.ser_puntaje
                estudiante_data['saber_puntaje'] = nota.saber_puntaje
                estudiante_data['hacer_puntaje'] = nota.hacer_puntaje
                estudiante_data['decidir_puntaje'] = nota.decidir_puntaje
                estudiante_data['nota_total'] = nota.nota_total
                estudiante_data['aprobado'] = nota.aprobado
                estudiante_data['tiene_nota'] = True
            except Nota.DoesNotExist:
                # Si el estudiante no tiene nota para esta materia y periodo
                estudiante_data = EstudianteConNotasSerializer(estudiante).data
                estudiante_data['tiene_nota'] = False

            resultado.append(estudiante_data)

        return resultado
