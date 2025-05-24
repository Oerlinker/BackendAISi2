from django.shortcuts import render
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notificacion
from .serializers import NotificacionSerializer, NotificacionListSerializer


class NotificacionViewSet(viewsets.ModelViewSet):
    """
    API para gestionar notificaciones de los usuarios.
    Permite listar, crear, actualizar y eliminar notificaciones,
    así como realizar acciones específicas como marcar como leída o archivar.
    """
    serializer_class = NotificacionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filtra las notificaciones para mostrar solo las del usuario autenticado"""
        usuario = self.request.user
        return Notificacion.objects.filter(usuario=usuario)

    def get_serializer_class(self):
        """Usa diferentes serializadores según la acción"""
        if self.action == 'list':
            return NotificacionListSerializer
        return NotificacionSerializer

    def list(self, request, *args, **kwargs):
        """Lista las notificaciones con filtros opcionales por estado"""
        queryset = self.get_queryset()

        # Filtrar por estado si se especifica en la URL
        estado = request.query_params.get('estado', None)
        if estado:
            queryset = queryset.filter(estado=estado)

        # Filtrar por tipo si se especifica
        tipo = request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo=tipo)

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def marcar_como_leida(self, request, pk=None):
        """Marca una notificación específica como leída"""
        notificacion = self.get_object()
        notificacion.estado = 'LEIDA'
        notificacion.fecha_lectura = timezone.now()
        notificacion.save()
        return Response({'status': 'notificación marcada como leída'})

    @action(detail=True, methods=['post'])
    def archivar(self, request, pk=None):
        """Archiva una notificación específica"""
        notificacion = self.get_object()
        notificacion.estado = 'ARCHIVADA'
        notificacion.save()
        return Response({'status': 'notificación archivada'})

    @action(detail=False, methods=['post'])
    def marcar_todas_como_leidas(self, request):
        """Marca todas las notificaciones no leídas del usuario como leídas"""
        self.get_queryset().filter(estado='NO_LEIDA').update(
            estado='LEIDA',
            fecha_lectura=timezone.now()
        )
        return Response({'status': 'todas las notificaciones marcadas como leídas'})

    @action(detail=False, methods=['get'])
    def no_leidas_count(self, request):
        """Devuelve el conteo de notificaciones no leídas"""
        count = self.get_queryset().filter(estado='NO_LEIDA').count()
        return Response({'count': count})
