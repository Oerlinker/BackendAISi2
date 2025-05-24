from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Avg, Count, F, Sum
from apps.usuarios.models import User
from apps.notas.models import Nota, Periodo
from apps.materias.models import Materia
from apps.asistencias.models import Asistencia
from apps.participaciones.models import Participacion
from apps.predicciones.models import Prediccion


class DashboardGeneralView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total_estudiantes = User.objects.filter(role='ESTUDIANTE').count()
        total_materias = Materia.objects.count()

        promedio_general = Nota.objects.aggregate(promedio=Avg('nota_total'))['promedio'] or 0

        # Calcular promedio de asistencia
        total_asistencias = Asistencia.objects.count()
        presentes = Asistencia.objects.filter(estado='PRESENTE').count()
        asistencia_promedio = (presentes / total_asistencias * 100) if total_asistencias > 0 else 0

        predicciones_distribucion = Prediccion.objects.values('nivel_rendimiento').annotate(
            cantidad=Count('id')
        ).order_by('nivel_rendimiento')

        materias_stats = Materia.objects.annotate(
            total_estudiantes=Count('nota__estudiante', distinct=True),
            promedio_notas=Avg('nota__nota_total')
        ).values('id', 'nombre', 'total_estudiantes', 'promedio_notas')

        trimestres_stats = Periodo.objects.values('trimestre').annotate(
            promedio=Avg('nota__nota_total'),
            estudiantes=Count('nota__estudiante', distinct=True)
        ).order_by('trimestre')

        return Response({
            'total_estudiantes': total_estudiantes,
            'total_materias': total_materias,
            'promedio_general': round(promedio_general, 2),
            'asistencia_promedio': round(asistencia_promedio, 2),
            'predicciones_distribucion': predicciones_distribucion,
            'materias_stats': materias_stats,
            'trimestres_stats': trimestres_stats
        })


class DashboardEstudianteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, estudiante_id=None):

        if not estudiante_id:
            if request.user.role == 'ESTUDIANTE':
                estudiante_id = request.user.id
            else:
                return Response(
                    {"error": "Debe especificar el ID del estudiante"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            estudiante = User.objects.get(id=estudiante_id, role='ESTUDIANTE')
        except User.DoesNotExist:
            return Response(
                {"error": "Estudiante no encontrado"},
                status=status.HTTP_404_NOT_FOUND
            )

        info_estudiante = {
            'id': estudiante.id,
            'username': estudiante.username,
            'email': estudiante.email,
            'nombre_completo': f"{estudiante.first_name} {estudiante.last_name}",
        }

        notas = Nota.objects.filter(estudiante=estudiante).select_related('materia', 'periodo')

        notas_por_materia = {}
        for nota in notas:
            materia_id = nota.materia.id
            materia_nombre = nota.materia.nombre
            trimestre = nota.periodo.trimestre
            año = nota.periodo.año_academico

            if materia_id not in notas_por_materia:
                notas_por_materia[materia_id] = {
                    'id': materia_id,
                    'nombre': materia_nombre,
                    'trimestres': {}
                }

            trimestre_key = f"{trimestre}_{año}"
            notas_por_materia[materia_id]['trimestres'][trimestre_key] = {
                'trimestre': trimestre,
                'año': año,
                'nota_total': nota.nota_total,
                'componentes': {
                    'ser': nota.ser_puntaje,
                    'saber': nota.saber_puntaje,
                    'hacer': nota.hacer_puntaje,
                    'decidir': nota.decidir_puntaje,
                    'autoevaluacion': nota.autoevaluacion_puntaje
                }
            }

        notas_materias_list = list(notas_por_materia.values())

        asistencias = {}
        for materia in Materia.objects.all():
            total_asistencias = Asistencia.objects.filter(
                estudiante=estudiante,
                materia=materia
            ).count()

            if total_asistencias > 0:
                asistencias_presentes = Asistencia.objects.filter(
                    estudiante=estudiante,
                    materia=materia,
                    presente=True
                ).count()

                porcentaje = (asistencias_presentes / total_asistencias) * 100
                asistencias[materia.id] = {
                    'materia_id': materia.id,
                    'materia_nombre': materia.nombre,
                    'porcentaje': round(porcentaje, 2),
                    'presentes': asistencias_presentes,
                    'total': total_asistencias
                }

        participaciones = {}
        for materia in Materia.objects.all():
            participaciones_count = Participacion.objects.filter(
                estudiante=estudiante,
                materia=materia
            ).count()

            if participaciones_count > 0:
                promedio_valor = Participacion.objects.filter(
                    estudiante=estudiante,
                    materia=materia
                ).aggregate(promedio=Avg('valor'))['promedio'] or 0

                participaciones[materia.id] = {
                    'materia_id': materia.id,
                    'materia_nombre': materia.nombre,
                    'total': participaciones_count,
                    'promedio_valor': round(promedio_valor, 2)
                }

        predicciones = Prediccion.objects.filter(estudiante=estudiante).select_related('materia')
        predicciones_list = []
        for pred in predicciones:
            predicciones_list.append({
                'id': pred.id,
                'materia_id': pred.materia.id,
                'materia_nombre': pred.materia.nombre,
                'fecha_prediccion': pred.fecha_prediccion,
                'valor_numerico': pred.valor_numerico,
                'nivel_rendimiento': pred.nivel_rendimiento,
                'variables': {
                    'promedio_notas': pred.promedio_notas,
                    'porcentaje_asistencia': pred.porcentaje_asistencia,
                    'promedio_participaciones': pred.promedio_participaciones
                }
            })

        return Response({
            'estudiante': info_estudiante,
            'notas': notas_materias_list,
            'asistencias': list(asistencias.values()),
            'participaciones': list(participaciones.values()),
            'predicciones': predicciones_list
        })


class ComparativoRendimientoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):

        if request.user.role not in ['PROFESOR', 'ADMINISTRATIVO']:
            return Response(
                {"error": "No tiene permisos para ver esta información"},
                status=status.HTTP_403_FORBIDDEN
            )

        predicciones = Prediccion.objects.all().select_related('estudiante', 'materia')

        comparaciones = []

        for pred in predicciones:

            nota_real = Nota.objects.filter(
                estudiante=pred.estudiante,
                materia=pred.materia
            ).order_by('-fecha_registro').first()

            if nota_real:
                comparaciones.append({
                    'estudiante_id': pred.estudiante.id,
                    'estudiante_nombre': f"{pred.estudiante.first_name} {pred.estudiante.last_name}",
                    'materia_id': pred.materia.id,
                    'materia_nombre': pred.materia.nombre,
                    'nota_predicha': pred.valor_numerico,
                    'nota_real': nota_real.nota_total,
                    'diferencia': nota_real.nota_total - pred.valor_numerico,
                    'nivel_predicho': pred.nivel_rendimiento
                })

        if comparaciones:

            error_absoluto = sum(abs(comp['diferencia']) for comp in comparaciones) / len(comparaciones)

            precision = 100 - (error_absoluto / 100) * 100
        else:
            precision = 0

        return Response({
            'comparaciones': comparaciones,
            'precision_modelo': round(precision, 2),
            'total_predicciones': len(comparaciones)
        })
