from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Avg
from django.shortcuts import get_object_or_404

from .models import Periodo, Nota
from .serializers import PeriodoSerializer, NotaSerializer, NotaEstudianteSerializer
from apps.materias.models import Materia
from apps.usuarios.models import User


class PeriodoViewSet(viewsets.ModelViewSet):
    queryset = Periodo.objects.all().order_by('-año_academico', 'trimestre')
    serializer_class = PeriodoSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotaViewSet(viewsets.ModelViewSet):
    serializer_class = NotaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):

        user = self.request.user
        queryset = Nota.objects.all()

        if user.role == 'ESTUDIANTE':

            queryset = queryset.filter(estudiante=user)
        elif user.role == 'PROFESOR':

            queryset = queryset.filter(materia__profesor=user)


        estudiante_id = self.request.query_params.get('estudiante')
        materia_id = self.request.query_params.get('materia')
        periodo_id = self.request.query_params.get('periodo')
        curso_id = self.request.query_params.get('curso')

        if estudiante_id:
            queryset = queryset.filter(estudiante__id=estudiante_id)
        if materia_id:
            queryset = queryset.filter(materia__id=materia_id)
        if periodo_id:
            queryset = queryset.filter(periodo__id=periodo_id)
        if curso_id:
            queryset = queryset.filter(estudiante__curso__id=curso_id)

        return queryset

    def get_serializer_class(self):

        user = self.request.user

        if user.role == 'ESTUDIANTE' and self.action in ['update', 'partial_update']:
            return NotaEstudianteSerializer

        return NotaSerializer

    @action(detail=True, methods=['post'])
    def autoevaluacion(self, request, pk=None):

        nota = self.get_object()
        user = request.user

        if user.role != 'ESTUDIANTE' or nota.estudiante.id != user.id:
            return Response(
                {"error": "Solo puedes realizar tu propia autoevaluación"},
                status=status.HTTP_403_FORBIDDEN
            )

        ser_valor = request.data.get('autoevaluacion_ser')
        decidir_valor = request.data.get('autoevaluacion_decidir')

        if ser_valor is None or decidir_valor is None:
            return Response(
                {"error": "Debes proporcionar valores para 'autoevaluacion_ser' y 'autoevaluacion_decidir'"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            ser_valor = float(ser_valor)
            decidir_valor = float(decidir_valor)

            if not (0 <= ser_valor <= 5):
                return Response(
                    {"error": "La autoevaluación del ser debe estar entre 0 y 5"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not (0 <= decidir_valor <= 5):
                return Response(
                    {"error": "La autoevaluación del decidir debe estar entre 0 y 5"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            nota.autoevaluacion_ser = ser_valor
            nota.autoevaluacion_decidir = decidir_valor
            nota.save()

            return Response(
                {
                    "message": "Autoevaluación registrada correctamente",
                    "autoevaluacion_ser": ser_valor,
                    "autoevaluacion_decidir": decidir_valor,
                    "nota_total": nota.nota_total
                },
                status=status.HTTP_200_OK
            )

        except ValueError:
            return Response(
                {"error": "Los valores de autoevaluación deben ser números"},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def estadisticas_estudiante(self, request):

        estudiante_id = request.query_params.get('estudiante')
        if not estudiante_id:
            return Response({"error": "Se requiere el ID del estudiante"}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.role == 'ESTUDIANTE' and str(request.user.id) != estudiante_id:
            return Response(
                {"error": "No tienes permiso para ver las estadísticas de otro estudiante"},
                status=status.HTTP_403_FORBIDDEN
            )

        notas = Nota.objects.filter(estudiante__id=estudiante_id)

        if not notas.exists():
            return Response(
                {"message": "No hay notas registradas para este estudiante"},
                status=status.HTTP_200_OK
            )

        promedios = {
            'ser': notas.aggregate(Avg('ser_puntaje'))['ser_puntaje__avg'],
            'saber': notas.aggregate(Avg('saber_puntaje'))['saber_puntaje__avg'],
            'hacer': notas.aggregate(Avg('hacer_puntaje'))['hacer_puntaje__avg'],
            'decidir': notas.aggregate(Avg('decidir_puntaje'))['decidir_puntaje__avg'],
            'autoevaluacion_ser': notas.aggregate(Avg('autoevaluacion_ser'))['autoevaluacion_ser__avg'],
            'autoevaluacion_decidir': notas.aggregate(Avg('autoevaluacion_decidir'))['autoevaluacion_decidir__avg'],
        }

        nota_promedio = sum([
            promedios['ser'],
            promedios['saber'],
            promedios['hacer'],
            promedios['decidir'],
            promedios['autoevaluacion_ser'],
            promedios['autoevaluacion_decidir']
        ])

        materias = []
        for nota in notas:
            materias.append({
                'materia': nota.materia.nombre,
                'nota_total': nota.nota_total,
                'aprobado': nota.aprobado
            })

        materias_aprobadas = sum(1 for nota in notas if nota.aprobado)
        materias_reprobadas = notas.count() - materias_aprobadas

        return Response({
            'estudiante_id': estudiante_id,
            'promedios': promedios,
            'nota_promedio': nota_promedio,
            'materias': materias,
            'materias_aprobadas': materias_aprobadas,
            'materias_reprobadas': materias_reprobadas,
            'total_materias': notas.count()
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def estadisticas_materia(self, request):
        materia_id = request.query_params.get('materia')
        periodo_id = request.query_params.get('periodo')

        if not materia_id:
            return Response({"error": "Se requiere el ID de la materia"}, status=status.HTTP_400_BAD_REQUEST)

        # Verificamos permisos solo para profesores, no para administrativos
        if request.user.role == 'PROFESOR':
            materia = get_object_or_404(Materia, id=materia_id)
            if materia.profesor and materia.profesor.id != request.user.id:
                return Response(
                    {"error": "No tienes permiso para ver las estadísticas de esta materia"},
                    status=status.HTTP_403_FORBIDDEN
                )
        # Los administrativos pueden acceder a todas las materias sin restricción

        notas = Nota.objects.filter(materia__id=materia_id)

        if periodo_id:
            notas = notas.filter(periodo__id=periodo_id)
            periodo_info = get_object_or_404(Periodo, id=periodo_id)
            periodo_display = f"{periodo_info.get_trimestre_display()} - {periodo_info.año_academico}"
        else:
            periodo_display = "Todos los periodos"

        if not notas.exists():
            return Response(
                {"message": "No hay notas registradas para esta materia en el periodo seleccionado"},
                status=status.HTTP_200_OK
            )

        promedios = {
            'ser': notas.aggregate(Avg('ser_puntaje'))['ser_puntaje__avg'],
            'saber': notas.aggregate(Avg('saber_puntaje'))['saber_puntaje__avg'],
            'hacer': notas.aggregate(Avg('hacer_puntaje'))['hacer_puntaje__avg'],
            'decidir': notas.aggregate(Avg('decidir_puntaje'))['decidir_puntaje__avg'],
            'autoevaluacion_ser': notas.aggregate(Avg('autoevaluacion_ser'))['autoevaluacion_ser__avg'],
            'autoevaluacion_decidir': notas.aggregate(Avg('autoevaluacion_decidir'))['autoevaluacion_decidir__avg'],
        }

        promedio_total = sum([
            promedios['ser'],
            promedios['saber'],
            promedios['hacer'],
            promedios['decidir'],
            promedios['autoevaluacion_ser'],
            promedios['autoevaluacion_decidir']
        ])

        aprobados = 0
        reprobados = 0
        mejor_nota = 0
        peor_nota = 100

        estudiantes = []
        for nota in notas:
            nota_total = nota.nota_total

            if nota.aprobado:
                aprobados += 1
            else:
                reprobados += 1

            if nota_total > mejor_nota:
                mejor_nota = nota_total
            if nota_total < peor_nota:
                peor_nota = nota_total

            estudiantes.append({
                'estudiante_id': nota.estudiante.id,
                'nombre': f"{nota.estudiante.first_name} {nota.estudiante.last_name}",
                'ser': float(nota.ser_puntaje + nota.autoevaluacion_ser),
                'saber': float(nota.saber_puntaje),
                'hacer': float(nota.hacer_puntaje),
                'decidir': float(nota.decidir_puntaje + nota.autoevaluacion_decidir),
                'nota_total': float(nota_total),
                'aprobado': nota.aprobado
            })

        if not estudiantes:
            peor_nota = 0

        return Response({
            'materia_id': materia_id,
            'materia_nombre': Materia.objects.get(id=materia_id).nombre,
            'periodo': periodo_display,
            'promedios': promedios,
            'promedio_total': promedio_total,
            'total_estudiantes': len(estudiantes),
            'aprobados': aprobados,
            'reprobados': reprobados,
            'porcentaje_aprobacion': (aprobados / len(estudiantes)) * 100 if len(estudiantes) > 0 else 0,
            'mejor_nota': mejor_nota,
            'peor_nota': peor_nota,
            'estudiantes': estudiantes
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def reporte_trimestral(self, request):
        curso_id = request.query_params.get('curso')
        periodo_id = request.query_params.get('periodo')

        if not curso_id or not periodo_id:
            return Response(
                {"error": "Se requiere el ID del curso y el periodo"},
                status=status.HTTP_400_BAD_REQUEST
            )

        estudiantes = User.objects.filter(curso__id=curso_id, role='ESTUDIANTE')

        if not estudiantes.exists():
            return Response(
                {"message": "No hay estudiantes asignados a este curso"},
                status=status.HTTP_200_OK
            )

        periodo = get_object_or_404(Periodo, id=periodo_id)

        reporte = []
        for estudiante in estudiantes:
            notas_estudiante = Nota.objects.filter(
                estudiante=estudiante,
                periodo=periodo
            )

            estudiante_data = {
                'estudiante_id': estudiante.id,
                'nombre': f"{estudiante.first_name} {estudiante.last_name}",
                'username': estudiante.username,
                'materias': [],
                'promedio_general': 0,
                'aprobadas': 0,
                'reprobadas': 0,
                'total_materias': 0
            }

            if not notas_estudiante.exists():
                reporte.append(estudiante_data)
                continue

            suma_notas = 0
            for nota in notas_estudiante:
                nota_total = nota.nota_total
                suma_notas += nota_total

                if nota.aprobado:
                    estudiante_data['aprobadas'] += 1
                else:
                    estudiante_data['reprobadas'] += 1

                estudiante_data['materias'].append({
                    'materia_id': nota.materia.id,
                    'nombre': nota.materia.nombre,
                    'ser': float(nota.ser_puntaje + nota.autoevaluacion_ser),
                    'saber': float(nota.saber_puntaje),
                    'hacer': float(nota.hacer_puntaje),
                    'decidir': float(nota.decidir_puntaje + nota.autoevaluacion_decidir),
                    'nota_total': float(nota_total),
                    'aprobado': nota.aprobado
                })

            estudiante_data['total_materias'] = len(estudiante_data['materias'])
            if estudiante_data['total_materias'] > 0:
                estudiante_data['promedio_general'] = suma_notas / estudiante_data['total_materias']

            reporte.append(estudiante_data)

        total_materias_curso = sum(e['total_materias'] for e in reporte)
        total_aprobadas = sum(e['aprobadas'] for e in reporte)
        total_reprobadas = sum(e['reprobadas'] for e in reporte)

        if total_materias_curso > 0:
            promedio_general_curso = sum(
                e['promedio_general'] * e['total_materias'] for e in reporte) / total_materias_curso
        else:
            promedio_general_curso = 0

        return Response({
            'curso_id': curso_id,
            'periodo': {
                'id': periodo.id,
                'nombre': periodo.nombre,
                'trimestre': periodo.get_trimestre_display(),
                'año_academico': periodo.año_academico
            },
            'estadisticas_curso': {
                'promedio_general': promedio_general_curso,
                'total_materias': total_materias_curso,
                'materias_aprobadas': total_aprobadas,
                'materias_reprobadas': total_reprobadas,
                'porcentaje_aprobacion': (
                                                     total_aprobadas / total_materias_curso) * 100 if total_materias_curso > 0 else 0
            },
            'estudiantes': reporte,
            'total_estudiantes': len(reporte)
        }, status=status.HTTP_200_OK)
