from rest_framework import serializers
from .models import Notificacion


class UserBasicInfoSerializer(serializers.Serializer):
    """Serializador simple para información básica del usuario"""
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)


class NotificacionSerializer(serializers.ModelSerializer):
    """Serializador completo para el modelo de Notificación"""
    usuario_info = UserBasicInfoSerializer(source='usuario', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Notificacion
        fields = [
            'id', 'usuario', 'usuario_info', 'titulo', 'mensaje',
            'tipo', 'tipo_display', 'estado', 'estado_display',
            'fecha_creacion', 'fecha_lectura', 'url_accion'
        ]
        read_only_fields = ['fecha_creacion', 'fecha_lectura']


class NotificacionListSerializer(serializers.ModelSerializer):
    """Serializador simplificado para listar notificaciones"""
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Notificacion
        fields = ['id', 'titulo', 'tipo', 'tipo_display', 'estado', 'fecha_creacion', 'url_accion']
