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
        try:
            total_estudiantes = User.objects.filter(role='ESTUDIANTE').count()
            total_materias = Materia.objects.count()

            # Calcular promedio general sumando los componentes individuales
            notas = Nota.objects.all()
            if notas.exists():
                suma_total = 0
                cantidad_notas = 0
                for nota in notas:
                    suma_total += (nota.ser_puntaje + nota.saber_puntaje +
                                  nota.hacer_puntaje + nota.decidir_puntaje +
                                  nota.autoevaluacion_ser + nota.autoevaluacion_decidir)
                    cantidad_notas += 1
                promedio_general = suma_total / cantidad_notas if cantidad_notas > 0 else 0
            else:
                promedio_general = 0

            # Calcular promedio de asistencia con manejo seguro de caso cero
            total_asistencias = Asistencia.objects.count()
            if total_asistencias > 0:
                presentes = Asistencia.objects.filter(presente=True).count()
                asistencia_promedio = (presentes / total_asistencias) * 100
            else:
                asistencia_promedio = 0

            predicciones_distribucion = Prediccion.objects.values('nivel_rendimiento').annotate(
                cantidad=Count('id')
            ).order_by('nivel_rendimiento')

            # Añadimos funcionalidad para calcular estadísticas por materia sin usar nota_total
            materias_stats = []
            for materia in Materia.objects.all():
                notas_materia = Nota.objects.filter(materia=materia)
                # Usamos el total de estudiantes general en lugar de contar por materia
                if notas_materia.exists():
                    suma_notas = 0
                    for nota in notas_materia:
                        suma_notas += (nota.ser_puntaje + nota.saber_puntaje +
                                      nota.hacer_puntaje + nota.decidir_puntaje +
                                      nota.autoevaluacion_ser + nota.autoevaluacion_decidir)
                    promedio_notas = suma_notas / notas_materia.count()
                else:
                    promedio_notas = 0

                materias_stats.append({
                    'id': materia.id,
                    'nombre': materia.nombre,
                    'total_estudiantes': total_estudiantes,  # Usamos el total general de estudiantes
                    'promedio_notas': round(promedio_notas, 2)
                })

            # Añadimos funcionalidad para calcular estadísticas por trimestre sin usar nota_total
            trimestres_stats = []
            for periodo in Periodo.objects.all():
                notas_periodo = Nota.objects.filter(periodo=periodo)
                # Usamos el total de estudiantes general en lugar de contar por periodo
                if notas_periodo.exists():
                    suma_notas = 0
                    for nota in notas_periodo:
                        suma_notas += (nota.ser_puntaje + nota.saber_puntaje +
                                      nota.hacer_puntaje + nota.decidir_puntaje +
                                      nota.autoevaluacion_ser + nota.autoevaluacion_decidir)
                    promedio = suma_notas / notas_periodo.count()
                else:
                    promedio = 0

                trimestres_stats.append({
                    'trimestre': periodo.trimestre,
                    'promedio': round(promedio, 2),
                    'estudiantes': total_estudiantes  # Usamos el total general de estudiantes
                })

            trimestres_stats.sort(key=lambda x: x['trimestre'])

            return Response({
                'total_estudiantes': total_estudiantes,
                'total_materias': total_materias,
                'promedio_general': round(promedio_general, 2),
                'asistencia_promedio': round(asistencia_promedio, 2),
                'predicciones_distribucion': predicciones_distribucion,
                'materias_stats': materias_stats,
                'trimestres_stats': trimestres_stats
            })
        except Exception as e:
            print(f"Error en DashboardGeneralView: {str(e)}")
            return Response(
                {"error": "Ha ocurrido un error al obtener las estadísticas"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
                    'autoevaluacion': nota.autoevaluacion_ser + nota.autoevaluacion_decidir
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

            if pred.valor_numerico >= 51:

                probabilidad_aprobar = min(100, 70 + (pred.valor_numerico - 51) * 1.5)
            else:

                probabilidad_aprobar = max(0, (pred.valor_numerico / 51) * 70)

            predicciones_list.append({
                'id': pred.id,
                'materia_id': pred.materia.id,
                'materia_nombre': pred.materia.nombre,
                'fecha_prediccion': pred.fecha_prediccion,
                'valor_numerico': pred.valor_numerico,
                'nivel_rendimiento': pred.nivel_rendimiento,
                'probabilidad_aprobar': round(probabilidad_aprobar, 1),
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


        estudiante_id = request.query_params.get('estudiante')
        materia_id = request.query_params.get('materia')


        predicciones_query = Prediccion.objects.all().select_related('estudiante', 'materia')


        if estudiante_id:
            predicciones_query = predicciones_query.filter(estudiante_id=estudiante_id)
        if materia_id:
            predicciones_query = predicciones_query.filter(materia_id=materia_id)

        comparaciones = []

        for pred in predicciones_query:

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
