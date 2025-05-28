from rest_framework import viewsets, permissions, pagination
from .models import Participacion
from .serializers import ParticipacionSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg, Count


class ParticipacionPagination(pagination.PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 100


class ParticipacionViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = ParticipacionPagination

    def get_queryset(self):
        queryset = Participacion.objects.select_related('estudiante', 'materia')
        estudiante_id = self.request.query_params.get('estudiante')
        materia_id = self.request.query_params.get('materia')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        tipo = self.request.query_params.get('tipo')
        curso_id = self.request.query_params.get('curso')
        fecha = self.request.query_params.get('fecha')

        if estudiante_id:
            queryset = queryset.filter(estudiante__id=estudiante_id)
        if materia_id:
            queryset = queryset.filter(materia__id=materia_id)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        if fecha:
            queryset = queryset.filter(fecha=fecha)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        if curso_id:
            queryset = queryset.filter(estudiante__curso__id=curso_id)

        return queryset.order_by('-fecha', '-id')

    @action(detail=False, methods=['get'])
    def estadisticas_participacion(self, request):
        estudiante_id = request.query_params.get('estudiante')
        materia_id = request.query_params.get('materia')

        if not estudiante_id or not materia_id:
            return Response({"error": "Se requieren los IDs de estudiante y materia"}, status=400)

        participaciones = Participacion.objects.select_related('estudiante', 'materia').filter(
            estudiante__id=estudiante_id,
            materia__id=materia_id
        )

        total_participaciones = participaciones.count()
        if total_participaciones == 0:
            return Response({
                "promedio_valor": 0,
                "total_participaciones": 0,
                "por_tipo": []
            })

        promedio_valor = participaciones.aggregate(promedio=Avg('valor'))['promedio'] or 0

        distribucion_tipo = participaciones.values('tipo').annotate(
            cantidad=Count('id'),
            promedio_valor=Avg('valor')
        ).order_by('-cantidad')

        return Response({
            "promedio_valor": round(promedio_valor, 2),
            "total_participaciones": total_participaciones,
            "por_tipo": distribucion_tipo
        })
