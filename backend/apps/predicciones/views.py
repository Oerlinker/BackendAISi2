from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Prediccion
from .serializers import PrediccionSerializer
from apps.notas.models import Nota, Periodo
from apps.asistencias.models import Asistencia
from apps.participaciones.models import Participacion
from apps.usuarios.models import User
from apps.materias.models import Materia
from apps.cursos.models import Curso
from django.db.models import Avg
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from datetime import datetime, timedelta
from decimal import Decimal
from .recomendaciones import GeneradorRecomendaciones


class PrediccionViewSet(viewsets.ModelViewSet):
    queryset = Prediccion.objects.all().order_by('-fecha_prediccion')
    serializer_class = PrediccionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        user = self.request.user
        queryset = self.queryset

        if user.role == 'ESTUDIANTE':
            queryset = queryset.filter(estudiante=user)
        elif user.role == 'PROFESOR':

            queryset = queryset.filter(materia__profesor=user)

        estudiante_id = self.request.query_params.get('estudiante')
        materia_id = self.request.query_params.get('materia')
        curso_id = self.request.query_params.get('curso')

        if estudiante_id:
            queryset = queryset.filter(estudiante__id=estudiante_id)
        if materia_id:
            queryset = queryset.filter(materia__id=materia_id)
        if curso_id:
            queryset = queryset.filter(estudiante__curso__id=curso_id)

        return queryset

    @action(detail=False, methods=['post'])
    def generar_prediccion(self, request):

        estudiante_id = request.data.get('estudiante')
        materia_id = request.data.get('materia')

        if not estudiante_id or not materia_id:
            return Response(
                {"error": "Se requiere especificar estudiante_id y materia_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            estudiante = User.objects.get(id=estudiante_id, role='ESTUDIANTE')
            materia = Materia.objects.get(id=materia_id)
        except User.DoesNotExist:
            return Response(
                {"error": "Estudiante no encontrado o no es un estudiante válido"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Materia.DoesNotExist:
            return Response(
                {"error": "Materia no encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )

        prediccion_reciente = Prediccion.objects.filter(
            estudiante=estudiante,
            materia=materia,
            fecha_prediccion__gte=datetime.now() - timedelta(days=7)
        ).first()

        if prediccion_reciente:
            serializer = self.get_serializer(prediccion_reciente)
            return Response(
                {
                    "message": "Ya existe una predicción reciente",
                    "prediccion": serializer.data
                },
                status=status.HTTP_200_OK
            )

        try:
            prediccion = self._calcular_prediccion(estudiante, materia)
            serializer = self.get_serializer(prediccion)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": f"Error al generar predicción: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def estudiantes_en_riesgo(self, request):

        curso_id = request.query_params.get('curso')
        materia_id = request.query_params.get('materia')

        estudiantes = User.objects.filter(role='ESTUDIANTE')
        if curso_id:
            estudiantes = estudiantes.filter(curso__id=curso_id)

        materias = Materia.objects.all()
        if materia_id:
            materias = materias.filter(id=materia_id)

        estudiantes_riesgo = []
        umbral_riesgo = 60.0

        for estudiante in estudiantes:
            materias_riesgo = []

            for materia in materias:

                prediccion = Prediccion.objects.filter(
                    estudiante=estudiante,
                    materia=materia
                ).order_by('-fecha_prediccion').first()

                if not prediccion:
                    try:
                        prediccion = self._calcular_prediccion(estudiante, materia)
                    except:
                        continue

                if prediccion and prediccion.valor_numerico < umbral_riesgo:
                    materias_riesgo.append({
                        'materia_id': materia.id,
                        'materia_nombre': materia.nombre,
                        'valor_predicho': float(prediccion.valor_numerico),
                        'nivel_rendimiento': prediccion.nivel_rendimiento,
                        'fecha_prediccion': prediccion.fecha_prediccion
                    })

            if materias_riesgo:
                estudiantes_riesgo.append({
                    'estudiante_id': estudiante.id,
                    'nombre': f"{estudiante.first_name} {estudiante.last_name}",
                    'username': estudiante.username,
                    'curso': estudiante.curso.nombre if estudiante.curso else None,
                    'materias_riesgo': materias_riesgo,
                    'total_materias_riesgo': len(materias_riesgo)
                })

        estudiantes_riesgo.sort(key=lambda x: x['total_materias_riesgo'], reverse=True)

        return Response({
            'total_estudiantes_riesgo': len(estudiantes_riesgo),
            'umbral_riesgo': umbral_riesgo,
            'estudiantes': estudiantes_riesgo
        }, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def recomendaciones(self, request, pk=None):

        prediccion = self.get_object()

        if request.user.role == 'ESTUDIANTE' and request.user.id != prediccion.estudiante.id:
            return Response(
                {"error": "No tienes permiso para ver recomendaciones de otro estudiante"},
                status=status.HTTP_403_FORBIDDEN
            )

        notas = Nota.objects.filter(
            estudiante=prediccion.estudiante,
            materia=prediccion.materia
        ).order_by('-periodo__fecha_inicio')

        asistencias = Asistencia.objects.filter(
            estudiante=prediccion.estudiante,
            materia=prediccion.materia,
            fecha__gte=datetime.now() - timedelta(days=90)
        )

        participaciones = Participacion.objects.filter(
            estudiante=prediccion.estudiante,
            materia=prediccion.materia,
            fecha__gte=datetime.now() - timedelta(days=90)
        )

        recomendaciones = GeneradorRecomendaciones.generar_recomendaciones(
            prediccion, asistencias, participaciones, notas
        )

        return Response({
            'prediccion_id': prediccion.id,
            'estudiante': prediccion.estudiante.username,
            'materia': prediccion.materia.nombre,
            'nivel_rendimiento': prediccion.nivel_rendimiento,
            'valor_numerico': float(prediccion.valor_numerico),
            'recomendaciones': recomendaciones,
            'total_recomendaciones': len(recomendaciones)
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def notificaciones(self, request):

        user = request.user
        notificaciones = []

        if user.role == 'ESTUDIANTE':

            predicciones_preocupantes = Prediccion.objects.filter(
                estudiante=user,
                nivel_rendimiento__in=['BAJO', 'MEDIO'],
                fecha_prediccion__gte=datetime.now() - timedelta(days=14)
            ).select_related('materia')

            for pred in predicciones_preocupantes:
                if pred.nivel_rendimiento == 'BAJO':
                    mensaje = f"Alerta: Tu rendimiento en {pred.materia.nombre} está por debajo del nivel esperado."
                    tipo = "urgente"
                else:
                    mensaje = f"Importante: Hay espacio para mejorar en {pred.materia.nombre}."
                    tipo = "advertencia"

                notificaciones.append({
                    'id': f"pred_{pred.id}",
                    'tipo': tipo,
                    'mensaje': mensaje,
                    'fecha': pred.fecha_prediccion,
                    'detalle': {
                        'prediccion_id': pred.id,
                        'materia': pred.materia.nombre,
                        'valor': float(pred.valor_numerico)
                    },
                    'accion': {
                        'texto': "Ver recomendaciones",
                        'url': f"/predicciones/{pred.id}/recomendaciones/"
                    }
                })

            faltas_recientes = Asistencia.objects.filter(
                estudiante=user,
                presente=False,
                fecha__gte=datetime.now() - timedelta(days=14)
            ).select_related('materia')

            if faltas_recientes.exists():
                materias_faltadas = {}
                for falta in faltas_recientes:
                    if falta.materia.id in materias_faltadas:
                        materias_faltadas[falta.materia.id]['count'] += 1
                    else:
                        materias_faltadas[falta.materia.id] = {
                            'nombre': falta.materia.nombre,
                            'count': 1
                        }

                for materia_id, datos in materias_faltadas.items():
                    if datos['count'] >= 2:
                        notificaciones.append({
                            'id': f"falta_{materia_id}",
                            'tipo': "alerta",
                            'mensaje': f"Tienes {datos['count']} faltas recientes en {datos['nombre']}",
                            'fecha': datetime.now(),
                            'accion': {
                                'texto': "Ver asistencia",
                                'url': f"/asistencias?materia={materia_id}&estudiante={user.id}"
                            }
                        })


        elif user.role == 'PROFESOR':

            materias_impartidas = Materia.objects.filter(profesor=user)

            if materias_impartidas.exists():
                for materia in materias_impartidas:

                    estudiantes_bajo_rendimiento = Prediccion.objects.filter(
                        materia=materia,
                        nivel_rendimiento='BAJO',
                        fecha_prediccion__gte=datetime.now() - timedelta(days=14)
                    ).select_related('estudiante').count()

                    if estudiantes_bajo_rendimiento > 0:
                        notificaciones.append({
                            'id': f"riesgo_{materia.id}",
                            'tipo': "informacion",
                            'mensaje': f"Hay {estudiantes_bajo_rendimiento} estudiantes en riesgo de reprobar {materia.nombre}",
                            'fecha': datetime.now(),
                            'accion': {
                                'texto': "Ver detalles",
                                'url': f"/predicciones/estudiantes_en_riesgo?materia={materia.id}"
                            }
                        })

                    ultima_semana = datetime.now() - timedelta(days=7)
                    asistencias = Asistencia.objects.filter(
                        materia=materia,
                        fecha__gte=ultima_semana
                    )

                    if asistencias.exists():
                        total = asistencias.count()
                        presentes = asistencias.filter(presente=True).count()
                        porcentaje = (presentes / total) * 100 if total > 0 else 0

                        if porcentaje < 70:
                            notificaciones.append({
                                'id': f"asistencia_{materia.id}",
                                'tipo': "advertencia",
                                'mensaje': f"La asistencia a {materia.nombre} es baja ({porcentaje:.1f}%)",
                                'fecha': datetime.now(),
                                'accion': {
                                    'texto': "Ver asistencias",
                                    'url': f"/asistencias?materia={materia.id}"
                                }
                            })


        elif user.role == 'ADMINISTRATIVO':

            cursos = Curso.objects.all()

            for curso in cursos:
                estudiantes_curso = User.objects.filter(curso=curso, role='ESTUDIANTE')

                if not estudiantes_curso.exists():
                    continue

                estudiantes_riesgo = 0
                for estudiante in estudiantes_curso:
                    tiene_riesgo = Prediccion.objects.filter(
                        estudiante=estudiante,
                        nivel_rendimiento='BAJO',
                        fecha_prediccion__gte=datetime.now() - timedelta(days=14)
                    ).exists()

                    if tiene_riesgo:
                        estudiantes_riesgo += 1

                if estudiantes_riesgo > 0:
                    porcentaje = (estudiantes_riesgo / estudiantes_curso.count()) * 100

                    if porcentaje > 30:
                        notificaciones.append({
                            'id': f"curso_{curso.id}",
                            'tipo': "urgente",
                            'mensaje': f"Atención: {estudiantes_riesgo} estudiantes ({porcentaje:.1f}%) en {curso.nombre} están en riesgo académico",
                            'fecha': datetime.now(),
                            'accion': {
                                'texto': "Ver reporte",
                                'url': f"/predicciones/estudiantes_en_riesgo?curso={curso.id}"
                            }
                        })

        prioridad = {"urgente": 1, "advertencia": 2, "alerta": 3, "informacion": 4}
        notificaciones.sort(key=lambda x: (prioridad.get(x['tipo'], 99), -int(x['id'].split('_')[1])))

        return Response({
            'total_notificaciones': len(notificaciones),
            'notificaciones': notificaciones
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def generar_prediccion_ml(self, request):

        estudiante_id = request.data.get('estudiante')
        materia_id = request.data.get('materia')

        if not estudiante_id or not materia_id:
            return Response(
                {"error": "Se requiere especificar estudiante_id y materia_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            estudiante = User.objects.get(id=estudiante_id, role='ESTUDIANTE')
            materia = Materia.objects.get(id=materia_id)
        except (User.DoesNotExist, Materia.DoesNotExist):
            return Response(
                {"error": "Estudiante o materia no encontrados"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:

            prediccion = self._generar_prediccion_ml(estudiante, materia)
            serializer = self.get_serializer(prediccion)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response(
                {"error": f"Error al generar predicción ML: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _generar_prediccion_ml(self, estudiante, materia):

        features = []
        labels = []

        notas = Nota.objects.filter(materia=materia)

        if notas.count() < 10:
            raise ValueError("No hay suficientes datos históricos para entrenar el modelo ML")

        for nota in notas:
            asistencias = Asistencia.objects.filter(
                estudiante=nota.estudiante,
                materia=nota.materia,
                fecha__range=(nota.periodo.fecha_inicio, nota.periodo.fecha_fin)
            )

            asistencias_total = asistencias.count()
            asistencias_presente = asistencias.filter(presente=True).count()
            porcentaje_asistencia = (asistencias_presente / asistencias_total) * 100 if asistencias_total > 0 else 0

            participaciones = Participacion.objects.filter(
                estudiante=nota.estudiante,
                materia=nota.materia,
                fecha__range=(nota.periodo.fecha_inicio, nota.periodo.fecha_fin)
            )

            promedio_participaciones = participaciones.aggregate(Avg('valor'))['valor__avg'] or 0

            features.append([
                float(nota.ser_puntaje),
                float(nota.saber_puntaje),
                float(nota.hacer_puntaje),
                float(nota.decidir_puntaje),
                porcentaje_asistencia,
                promedio_participaciones
            ])

            labels.append(float(nota.nota_total))

        X = np.array(features)
        y = np.array(labels)

        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)

        ultimo_periodo = Periodo.objects.all().order_by('-fecha_inicio').first()

        asistencias_recientes = Asistencia.objects.filter(
            estudiante=estudiante,
            materia=materia,
            fecha__gte=datetime.now() - timedelta(days=90)
        )

        total_asistencias = asistencias_recientes.count()
        asistencias_presentes = asistencias_recientes.filter(presente=True).count()
        porcentaje_asistencia = (asistencias_presentes / total_asistencias) * 100 if total_asistencias > 0 else 0

        participaciones_recientes = Participacion.objects.filter(
            estudiante=estudiante,
            materia=materia,
            fecha__gte=datetime.now() - timedelta(days=90)
        )

        promedio_participaciones = participaciones_recientes.aggregate(Avg('valor'))['valor__avg'] or 0

        ultima_nota = Nota.objects.filter(
            estudiante=estudiante,
            materia=materia
        ).order_by('-periodo__fecha_inicio').first()

        if not ultima_nota:
            raise ValueError("No hay notas previas para este estudiante en esta materia")

        features_estudiante = [
            float(ultima_nota.ser_puntaje),
            float(ultima_nota.saber_puntaje),
            float(ultima_nota.hacer_puntaje),
            float(ultima_nota.decidir_puntaje),
            porcentaje_asistencia,
            promedio_participaciones
        ]

        valor_predicho = model.predict([features_estudiante])[0]

        valor_predicho = max(0, min(100, valor_predicho))

        nivel_rendimiento = 'BAJO'
        if valor_predicho >= 80:
            nivel_rendimiento = 'ALTO'
        elif valor_predicho >= 60:
            nivel_rendimiento = 'MEDIO'

        valor_predicho_decimal = Decimal(str(round(valor_predicho, 2)))
        porcentaje_asistencia_decimal = Decimal(str(round(porcentaje_asistencia, 2)))
        promedio_participaciones_decimal = Decimal(str(round(promedio_participaciones, 2)))
        promedio_total_decimal = Decimal(str(round(float(ultima_nota.nota_total), 2)))

        prediccion = Prediccion.objects.create(
            estudiante=estudiante,
            materia=materia,
            valor_numerico=valor_predicho_decimal,
            nivel_rendimiento=nivel_rendimiento,
            promedio_notas=promedio_total_decimal,
            porcentaje_asistencia=porcentaje_asistencia_decimal,
            promedio_participaciones=promedio_participaciones_decimal
        )

        return prediccion

    def _calcular_prediccion(self, estudiante, materia):

        notas = Nota.objects.filter(
            estudiante=estudiante,
            materia=materia
        ).order_by('periodo__fecha_inicio')

        if not notas.exists():
            raise ValueError("No hay suficientes datos históricos de notas")

        ultimo_periodo = Periodo.objects.all().order_by('-fecha_inicio').first()

        asistencias = Asistencia.objects.filter(
            estudiante=estudiante,
            materia=materia,
            fecha__gte=ultimo_periodo.fecha_inicio if ultimo_periodo else datetime.now() - timedelta(days=120)
        )

        total_asistencias = asistencias.count()
        asistencias_presentes = asistencias.filter(presente=True).count()

        porcentaje_asistencia = 100.0
        if total_asistencias > 0:
            porcentaje_asistencia = (asistencias_presentes / total_asistencias) * 100

        participaciones = Participacion.objects.filter(
            estudiante=estudiante,
            materia=materia,
            fecha__gte=ultimo_periodo.fecha_inicio if ultimo_periodo else datetime.now() - timedelta(days=120)
        )

        promedio_participaciones = 0.0
        if participaciones.exists():
            promedio_participaciones_decimal = participaciones.aggregate(Avg('valor'))['valor__avg']

            promedio_participaciones = float(
                promedio_participaciones_decimal) if promedio_participaciones_decimal is not None else 0.0

        promedio_notas = notas.aggregate(
            ser=Avg('ser_puntaje'),
            saber=Avg('saber_puntaje'),
            hacer=Avg('hacer_puntaje'),
            decidir=Avg('decidir_puntaje'),
            auto_ser=Avg('autoevaluacion_ser'),
            auto_decidir=Avg('autoevaluacion_decidir')
        )

        promedio_total = sum([
            float(promedio_notas['ser'] or 0),
            float(promedio_notas['saber'] or 0),
            float(promedio_notas['hacer'] or 0),
            float(promedio_notas['decidir'] or 0),
            float(promedio_notas['auto_ser'] or 0),
            float(promedio_notas['auto_decidir'] or 0)
        ])

        factor_asistencia = porcentaje_asistencia * 0.25

        factor_participacion = min(10, promedio_participaciones) / 10 * 15

        factor_notas = promedio_total * 0.6

        valor_predicho = factor_asistencia + factor_participacion + factor_notas

        if notas.count() >= 2:
            notas_ordenadas = list(notas.order_by('periodo__fecha_inicio'))
            ultima_nota = float(notas_ordenadas[-1].nota_total)
            penultima_nota = float(notas_ordenadas[-2].nota_total if len(notas_ordenadas) > 1 else ultima_nota)

            tendencia = ultima_nota - penultima_nota

            valor_predicho += min(5, max(-5, tendencia))

        valor_predicho = max(0, min(100, valor_predicho))

        nivel_rendimiento = 'BAJO'
        if valor_predicho >= 80:
            nivel_rendimiento = 'ALTO'
        elif valor_predicho >= 60:
            nivel_rendimiento = 'MEDIO'

        valor_predicho_decimal = Decimal(str(round(valor_predicho, 2)))
        porcentaje_asistencia_decimal = Decimal(str(round(porcentaje_asistencia, 2)))
        promedio_participaciones_decimal = Decimal(str(round(promedio_participaciones, 2)))
        promedio_total_decimal = Decimal(str(round(promedio_total, 2)))

        prediccion = Prediccion.objects.create(
            estudiante=estudiante,
            materia=materia,
            valor_numerico=valor_predicho_decimal,
            nivel_rendimiento=nivel_rendimiento,
            promedio_notas=promedio_total_decimal,
            porcentaje_asistencia=porcentaje_asistencia_decimal,
            promedio_participaciones=promedio_participaciones_decimal
        )

        return prediccion
