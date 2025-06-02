from rest_framework import viewsets, permissions, status
from .models import Asistencia
from .serializers import AsistenciaSerializer, AsistenciaListSerializer
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import IntegrityError, transaction
from rest_framework.pagination import PageNumberPagination


class AsistenciaPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 500


class AsistenciaViewSet(viewsets.ModelViewSet):
    serializer_class = AsistenciaSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = AsistenciaPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return AsistenciaListSerializer
        return AsistenciaSerializer

    def get_queryset(self):
        queryset = Asistencia.objects.all()
        estudiante_id = self.request.query_params.get('estudiante')
        materia_id = self.request.query_params.get('materia')
        fecha = self.request.query_params.get('fecha')
        fecha_inicio = self.request.query_params.get('fecha_inicio')
        fecha_fin = self.request.query_params.get('fecha_fin')
        curso_id = self.request.query_params.get('curso')

        if estudiante_id:
            queryset = queryset.filter(estudiante__id=estudiante_id)
        if materia_id:
            queryset = queryset.filter(materia__id=materia_id)
        if fecha:

            from datetime import datetime
            try:

                if '-' in fecha:
                    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
                    fecha_formateada = fecha_obj.strftime('%Y-%m-%d')
                    queryset = queryset.filter(fecha=fecha_formateada)
                else:

                    try:
                        fecha_obj = datetime.strptime(fecha, '%d/%m/%Y')
                        fecha_formateada = fecha_obj.strftime('%Y-%m-%d')
                        queryset = queryset.filter(fecha=fecha_formateada)
                    except ValueError:

                        queryset = queryset.filter(fecha=fecha)
            except ValueError:

                queryset = queryset.filter(fecha=fecha)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        if curso_id:
            queryset = queryset.filter(estudiante__curso__id=curso_id)

        if self.action in ['list', 'retrieve']:
            queryset = queryset.select_related('estudiante', 'materia')

        return queryset.order_by('-fecha', 'estudiante__last_name')

    def create(self, request, *args, **kwargs):
        try:

            estudiante_id = request.data.get('estudiante')
            materia_id = request.data.get('materia')
            fecha = request.data.get('fecha')

            if not all([estudiante_id, materia_id, fecha]):
                return Response(
                    {"error": "Se requieren estudiante_id, materia_id y fecha"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            try:
                asistencia_existente = Asistencia.objects.get(
                    estudiante_id=estudiante_id,
                    materia_id=materia_id,
                    fecha=fecha
                )

                serializer = self.get_serializer(asistencia_existente, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
                return Response(serializer.data)

            except Asistencia.DoesNotExist:

                return super().create(request, *args, **kwargs)

        except IntegrityError as e:
            return Response(
                {"error": f"Error de integridad: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"error": f"Error al registrar asistencia: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def bulk_create(self, request):

        try:
            asistencias_data = request.data.get('asistencias', [])
            if not asistencias_data:
                return Response(
                    {"error": "No se proporcionaron datos de asistencia"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            resultados = {
                "creados": 0,
                "actualizados": 0,
                "errores": []
            }

            with transaction.atomic():
                for item in asistencias_data:
                    try:
                        estudiante_id = item.get('estudiante')
                        materia_id = item.get('materia')
                        fecha = item.get('fecha')
                        presente = item.get('presente', True)
                        justificacion = item.get('justificacion', '')

                        try:
                            asistencia = Asistencia.objects.get(
                                estudiante_id=estudiante_id,
                                materia_id=materia_id,
                                fecha=fecha
                            )
                            asistencia.presente = presente
                            asistencia.justificacion = justificacion
                            asistencia.save()
                            resultados["actualizados"] += 1
                        except Asistencia.DoesNotExist:

                            Asistencia.objects.create(
                                estudiante_id=estudiante_id,
                                materia_id=materia_id,
                                fecha=fecha,
                                presente=presente,
                                justificacion=justificacion
                            )
                            resultados["creados"] += 1
                    except Exception as e:
                        resultados["errores"].append(f"Error con estudiante {estudiante_id}: {str(e)}")

                        continue

            if resultados["errores"] and resultados["creados"] == 0 and resultados["actualizados"] == 0:
                return Response(
                    {"error": "No se pudo crear/actualizar ningún registro de asistencia",
                     "detalles": resultados["errores"]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(resultados, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": f"Error en la operación masiva de asistencias: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def porcentaje_asistencia(self, request):

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
