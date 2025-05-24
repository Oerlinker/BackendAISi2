"""
Script para probar el sistema de predicciones desde la shell de Django.
Este script prueba:
1. La generación de predicciones
2. Las recomendaciones personalizadas
3. Las notificaciones para diferentes tipos de usuarios

Ejecución: python manage.py shell < scripts/prueba_predicciones.py
"""

from apps.predicciones.views import PrediccionViewSet
from apps.usuarios.models import User
from apps.materias.models import Materia
from apps.predicciones.models import Prediccion
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request
from django.contrib.auth.models import AnonymousUser
from rest_framework.response import Response
import traceback
import sys

print("Iniciando pruebas del sistema de predicciones...")

# Verificar que existen datos para realizar las pruebas
try:
    estudiante_count = User.objects.filter(role='ESTUDIANTE').count()
    materia_count = Materia.objects.all().count()
    prediccion_count = Prediccion.objects.all().count()

    print(f"Estadísticas iniciales:")
    print(f"- {estudiante_count} estudiantes en la base de datos")
    print(f"- {materia_count} materias en la base de datos")
    print(f"- {prediccion_count} predicciones existentes")

    if estudiante_count == 0 or materia_count == 0:
        print("ERROR: No hay suficientes datos en la base de datos para realizar pruebas.")
        sys.exit(1)

except Exception as e:
    print(f"Error al verificar datos: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

# Crear instancias de las vistas para cada acción específica
factory = APIRequestFactory()
viewset = PrediccionViewSet()

# Función para convertir un WSGIRequest a DRF Request
def get_drf_request(request):
    # Convertir WSGIRequest a DRF Request
    drf_request = Request(request)
    drf_request.user = request.user
    drf_request.data = getattr(request, 'data', {})
    drf_request.query_params = getattr(request, 'GET', {})
    return drf_request

# 1. Probar generación de predicciones
def probar_generar_prediccion():
    print("\n*** PROBANDO GENERACIÓN DE PREDICCIONES ***\n")

    try:
        # Obtener un estudiante y una materia para la prueba
        estudiante = User.objects.filter(role='ESTUDIANTE').first()
        materia = Materia.objects.first()

        if not estudiante or not materia:
            print("ERROR: No hay estudiantes o materias en la base de datos")
            return

        print(f"Generando predicción para estudiante: {estudiante.username} (ID: {estudiante.id})")
        print(f"Materia seleccionada: {materia.nombre} (ID: {materia.id})")

        data = {
            'estudiante': estudiante.id,
            'materia': materia.id
        }

        # Crear el request para la acción generar_prediccion
        request = factory.post('/predicciones/generar_prediccion/', data=data)
        request.user = User.objects.filter(role='PROFESOR').first() or estudiante

        # Convertir a DRF Request
        drf_request = get_drf_request(request)

        # Llamar directamente a la acción en el viewset
        viewset.request = drf_request
        viewset.format_kwarg = None
        response = viewset.generar_prediccion(drf_request)

        print(f"Resultado de la generación de predicción:")
        print(f"- Estatus: {response.status_code}")

        if hasattr(response, 'data'):
            if 'prediccion' in response.data:
                pred_data = response.data['prediccion']
                print(f"- Valor predicho: {pred_data.get('valor_numerico', 'N/A')}")
                print(f"- Nivel: {pred_data.get('nivel_rendimiento', 'N/A')}")
            elif 'valor_numerico' in response.data:
                print(f"- Valor predicho: {response.data['valor_numerico']}")
                print(f"- Nivel: {response.data['nivel_rendimiento']}")
        else:
            print("- No hay datos en la respuesta")

        # Devolver el ID de la última predicción para usarlo en otras pruebas
        return Prediccion.objects.filter(
            estudiante=estudiante,
            materia=materia
        ).order_by('-fecha_prediccion').first()

    except Exception as e:
        print(f"ERROR en generación de predicción: {str(e)}")
        traceback.print_exc()
        return None

# 2. Probar recomendaciones personalizadas
def probar_recomendaciones(prediccion=None):
    print("\n*** PROBANDO RECOMENDACIONES PERSONALIZADAS ***\n")

    try:
        if not prediccion:
            prediccion = Prediccion.objects.order_by('-fecha_prediccion').first()

        if not prediccion:
            print("ERROR: No hay predicciones disponibles para probar recomendaciones")
            return

        print(f"Obteniendo recomendaciones para:")
        print(f"- Estudiante: {prediccion.estudiante.username}")
        print(f"- Materia: {prediccion.materia.nombre}")
        print(f"- Predicción ID: {prediccion.id}")

        # Crear el request para la acción recomendaciones
        request = factory.get(f'/predicciones/{prediccion.id}/recomendaciones/')
        request.user = prediccion.estudiante

        # Convertir a DRF Request
        drf_request = get_drf_request(request)

        # Llamar directamente a la acción en el viewset
        viewset.request = drf_request
        viewset.format_kwarg = None
        viewset.kwargs = {'pk': prediccion.id}
        viewset.action = 'recomendaciones'

        # Establecer el objeto actual
        viewset.get_object = lambda: prediccion

        response = viewset.recomendaciones(drf_request, pk=prediccion.id)

        print(f"Resultado de las recomendaciones:")
        print(f"- Estatus: {response.status_code}")

        if hasattr(response, 'data'):
            total_recs = response.data.get('total_recomendaciones', 0)
            print(f"- Total recomendaciones: {total_recs}")

            # Mostrar las 3 primeras recomendaciones
            recomendaciones = response.data.get('recomendaciones', [])
            for i, rec in enumerate(recomendaciones[:3]):
                print(f"  {i+1}. [{rec.get('categoria', 'N/A')}] {rec.get('mensaje', 'N/A')}")

            if len(recomendaciones) > 3:
                print(f"  ... y {len(recomendaciones) - 3} recomendaciones más")
        else:
            print("- No hay datos en la respuesta")

    except Exception as e:
        print(f"ERROR en recomendaciones: {str(e)}")
        traceback.print_exc()

# 3. Probar notificaciones para diferentes roles
def probar_notificaciones():
    print("\n*** PROBANDO NOTIFICACIONES ***\n")

    try:
        for role in ['ESTUDIANTE', 'PROFESOR', 'ADMINISTRATIVO']:
            usuario = User.objects.filter(role=role).first()
            if not usuario:
                print(f"No hay usuarios con rol {role}")
                continue

            print(f"Obteniendo notificaciones para {usuario.username} (rol: {role})")

            # Crear el request para la acción notificaciones
            request = factory.get('/predicciones/notificaciones/')
            request.user = usuario

            # Convertir a DRF Request
            drf_request = get_drf_request(request)

            # Llamar directamente a la acción en el viewset
            viewset.request = drf_request
            viewset.format_kwarg = None
            response = viewset.notificaciones(drf_request)

            print(f"Resultado de notificaciones para {role}:")
            print(f"- Estatus: {response.status_code}")

            if hasattr(response, 'data'):
                total_notif = response.data.get('total_notificaciones', 0)
                print(f"- Total notificaciones: {total_notif}")

                # Mostrar las 2 primeras notificaciones
                notificaciones = response.data.get('notificaciones', [])
                for i, notif in enumerate(notificaciones[:2]):
                    print(f"  {i+1}. [{notif.get('tipo', 'N/A')}] {notif.get('mensaje', 'N/A')}")

                if len(notificaciones) > 2:
                    print(f"  ... y {len(notificaciones) - 2} notificaciones más")
            else:
                print("- No hay datos en la respuesta")
            print("")

    except Exception as e:
        print(f"ERROR en notificaciones: {str(e)}")
        traceback.print_exc()

# 4. Probar estudiantes en riesgo
def probar_estudiantes_en_riesgo():
    print("\n*** PROBANDO ESTUDIANTES EN RIESGO ***\n")

    try:
        # Como admin
        admin = User.objects.filter(role='ADMINISTRATIVO').first() or User.objects.filter(is_superuser=True).first()
        if not admin:
            print("ERROR: No hay administradores para ejecutar esta prueba")
            return

        print(f"Consultando estudiantes en riesgo como: {admin.username}")

        # Crear el request para la acción estudiantes_en_riesgo
        request = factory.get('/predicciones/estudiantes_en_riesgo/')
        request.user = admin

        # Convertir a DRF Request
        drf_request = get_drf_request(request)

        # Llamar directamente a la acción en el viewset
        viewset.request = drf_request
        viewset.format_kwarg = None
        response = viewset.estudiantes_en_riesgo(drf_request)

        print(f"Resultado de estudiantes en riesgo:")
        print(f"- Estatus: {response.status_code}")

        if hasattr(response, 'data'):
            total_estudiantes = response.data.get('total_estudiantes_riesgo', 0)
            print(f"- Total estudiantes en riesgo: {total_estudiantes}")

            # Mostrar los 3 primeros estudiantes en riesgo
            estudiantes = response.data.get('estudiantes', [])
            for i, est in enumerate(estudiantes[:3]):
                print(f"  {i+1}. {est.get('nombre', 'N/A')} - Materias en riesgo: {est.get('total_materias_riesgo', 0)}")

                # Mostrar 1 materia en riesgo para este estudiante
                materias_riesgo = est.get('materias_riesgo', [])
                if materias_riesgo:
                    materia = materias_riesgo[0]
                    print(f"     - {materia.get('materia_nombre', 'N/A')}: {materia.get('valor_predicho', 'N/A')}")

            if len(estudiantes) > 3:
                print(f"  ... y {len(estudiantes) - 3} estudiantes más en riesgo")
        else:
            print("- No hay datos en la respuesta")

    except Exception as e:
        print(f"ERROR en estudiantes en riesgo: {str(e)}")
        traceback.print_exc()

# 5. Probar RandomForest ML (si hay suficientes datos)
def probar_prediccion_ml():
    print("\n*** PROBANDO PREDICCIÓN CON MACHINE LEARNING ***\n")

    try:
        # Obtener un estudiante y una materia
        estudiante = User.objects.filter(role='ESTUDIANTE').first()
        materia = Materia.objects.first()

        if not estudiante or not materia:
            print("ERROR: No hay estudiantes o materias en la base de datos")
            return

        print(f"Generando predicción ML para estudiante: {estudiante.username}")
        print(f"Materia seleccionada: {materia.nombre}")

        data = {
            'estudiante': estudiante.id,
            'materia': materia.id
        }

        # Crear el request para la acción generar_prediccion_ml
        request = factory.post('/predicciones/generar_prediccion_ml/', data=data)
        request.user = User.objects.filter(role='PROFESOR').first() or estudiante

        # Convertir a DRF Request
        drf_request = get_drf_request(request)

        # Asegurar que los datos estén accesibles
        drf_request.data = data

        # Llamar directamente a la acción en el viewset
        viewset.request = drf_request
        viewset.format_kwarg = None

        try:
            response = viewset.generar_prediccion_ml(drf_request)

            print(f"Resultado de predicción ML:")
            print(f"- Estatus: {response.status_code}")

            if hasattr(response, 'data'):
                if response.status_code < 400:  # Si no es error
                    print(f"- Valor predicho: {response.data.get('valor_numerico', 'N/A')}")
                    print(f"- Nivel: {response.data.get('nivel_rendimiento', 'N/A')}")
                else:
                    print(f"- Error: {response.data}")
            else:
                print("- No hay datos en la respuesta")

        except Exception as e:
            print(f"Error ejecutando predicción ML: {str(e)}")
            print("Es posible que no haya suficientes datos históricos para entrenar el modelo ML")
            traceback.print_exc()

    except Exception as e:
        print(f"ERROR en predicción ML: {str(e)}")
        traceback.print_exc()

# Ejecutar todas las pruebas
print("\n=== PROBANDO SISTEMA DE PREDICCIONES Y RECOMENDACIONES ===\n")

pred = probar_generar_prediccion()
if pred:
    probar_recomendaciones(pred)
probar_notificaciones()
probar_estudiantes_en_riesgo()
probar_prediccion_ml()

print("\n=== PRUEBAS COMPLETADAS ===\n")
