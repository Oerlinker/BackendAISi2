from rest_framework import serializers
from .models import Materia
from apps.usuarios.serializers import UserRegisterSerializer

class MateriaSerializer(serializers.ModelSerializer):
    # Para mostrar los detalles del profesor cuando se obtiene una materia
    profesor_detail = UserRegisterSerializer(source='profesor', read_only=True)

    class Meta:
        model = Materia
        fields = ['id', 'nombre', 'codigo', 'descripcion', 'creditos', 'profesor', 'profesor_detail']
        # El campo 'profesor' se usará para escritura (solo ID)
        # El campo 'profesor_detail' se usará para lectura (datos completos)
