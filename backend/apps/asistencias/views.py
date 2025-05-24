from rest_framework import viewsets, permissions
from .models import Asistencia
from .serializers import AsistenciaSerializer
from rest_framework.decorators import action
from rest_framework.response import Response


class AsistenciaViewSet(viewsets.ModelViewSet):
    serializer_class = AsistenciaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = Asistencia.objects.all()
        estudiante_id = self.request.query_params.get('estudiante')
        materia_id = self.request.query_params.get('materia')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')

        if estudiante_id:
            queryset = queryset.filter(estudiante__id=estudiante_id)
        if materia_id:
            queryset = queryset.filter(materia__id=materia_id)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)

        return queryset

    @action(detail=False, methods=['get'])
    def porcentaje_asistencia(self, request):
        """Calcular el porcentaje de asistencia para un estudiante en una materia"""
        estudiante_id = request.query_params.get('estudiante')
        materia_id = request.query_params.get('materia')

        if not estudiante_id or not materia_id:
            return Response({"error": "Se requieren los IDs de estudiante y materia"}, status=400)


        total_registros = Asistencia.objects.filter(
            estudiante__id=estudiante_id,
            materia__id=materia_id
        ).count()

        if total_registros == 0:
            return Response({"porcentaje": 0, "total_clases": 0, "asistencias": 0, "ausencias": 0})


        total_asistencias = Asistencia.objects.filter(
            estudiante__id=estudiante_id,
            materia__id=materia_id,
            presente=True
        ).count()


        porcentaje = (total_asistencias / total_registros) * 100

        return Response({
            "porcentaje": round(porcentaje, 2),
            "total_clases": total_registros,
            "asistencias": total_asistencias,
            "ausencias": total_registros - total_asistencias
        })
