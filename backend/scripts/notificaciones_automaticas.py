import sys

from datetime import datetime, timedelta
import logging
from django.db.models import Count

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("notificaciones_automaticas.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("Iniciando proceso automático de notificaciones y predicciones")

from apps.predicciones.models import Prediccion
from notificaciones.models import Notificacion
from apps.usuarios.models import User
from apps.materias.models import Materia
from apps.asistencias.models import Asistencia


def generar_predicciones_automaticas():
    """Genera predicciones para estudiantes que no tienen predicciones recientes."""
    logger.info("Generando predicciones automáticas...")

    # Obtener todos los estudiantes
    estudiantes = User.objects.filter(role='ESTUDIANTE')
    materias = Materia.objects.all()

    predicciones_generadas = 0
    predicciones_fallidas = 0

    # Iteramos por cada estudiante y materia
    for estudiante in estudiantes:
        for materia in materias:
            # Verificamos si el estudiante tiene una predicción reciente (menos de 7 días)
            prediccion_reciente = Prediccion.objects.filter(
                estudiante=estudiante,
                materia=materia,
                fecha_prediccion__gte=datetime.now() - timedelta(days=7)
            ).exists()

            # Si no tiene predicción reciente, generamos una nueva
            if not prediccion_reciente:
                try:
                    from apps.predicciones.views import PrediccionViewSet
                    viewset = PrediccionViewSet()

                    # Intentamos generar una nueva predicción
                    prediccion = viewset._calcular_prediccion(estudiante, materia)
                    predicciones_generadas += 1

                    # Si la predicción muestra riesgo (BAJO), generar una notificación
                    if prediccion.nivel_rendimiento == 'BAJO':
                        # Crear notificación para el estudiante
                        Notificacion.objects.create(
                            usuario=estudiante,
                            tipo='ALERTA',
                            titulo=f"Riesgo académico en {materia.nombre}",
                            mensaje=f"Tu rendimiento en {materia.nombre} está por debajo del nivel esperado. " 
                                    f"Revisa las recomendaciones para mejorar.",
                            url_accion=f"/predicciones/{prediccion.id}/recomendaciones/"
                        )

                        # Si la materia tiene profesor asignado, notificar también al profesor
                        if materia.profesor:
                            Notificacion.objects.create(
                                usuario=materia.profesor,
                                tipo='ALERTA',
                                titulo=f"Estudiante en riesgo: {estudiante.first_name} {estudiante.last_name}",
                                mensaje=f"El estudiante {estudiante.first_name} {estudiante.last_name} "
                                        f"está en riesgo académico en tu materia {materia.nombre}.",
                                url_accion=f"/estudiantes/{estudiante.id}/detalle"
                            )

                    # Si la predicción muestra nivel medio, enviar notificación informativa
                    elif prediccion.nivel_rendimiento == 'MEDIO':
                        Notificacion.objects.create(
                            usuario=estudiante,
                            tipo='INFO',
                            titulo=f"Rendimiento medio en {materia.nombre}",
                            mensaje=f"Tu rendimiento en {materia.nombre} es aceptable, "
                                    f"pero hay espacio para mejorar.",
                            url_accion=f"/predicciones/{prediccion.id}/recomendaciones/"
                        )

                    logger.info(f"Predicción generada para estudiante {estudiante.username} en materia {materia.nombre}: {prediccion.nivel_rendimiento}")

                except Exception as e:
                    predicciones_fallidas += 1
                    logger.error(f"Error al generar predicción para {estudiante.username} en {materia.nombre}: {str(e)}")

    logger.info(f"Proceso completado: {predicciones_generadas} predicciones generadas, {predicciones_fallidas} fallidas")
    return predicciones_generadas, predicciones_fallidas

def notificar_asistencia():
    """Genera notificaciones sobre problemas de asistencia recientes."""
    logger.info("Generando notificaciones de asistencia...")

    # Obtener estudiantes
    estudiantes = User.objects.filter(role='ESTUDIANTE')

    notificaciones_creadas = 0

    for estudiante in estudiantes:
        # Buscar faltas recientes (últimos 14 días)
        faltas_recientes = Asistencia.objects.filter(
            estudiante=estudiante,
            presente=False,
            fecha__gte=datetime.now() - timedelta(days=14)
        ).values('materia').annotate(total_faltas=Count('id')).filter(total_faltas__gte=2)

        for falta in faltas_recientes:
            try:
                materia = Materia.objects.get(id=falta['materia'])

                # Notificar al estudiante sobre sus faltas
                Notificacion.objects.create(
                    usuario=estudiante,
                    tipo='RECORDATORIO',
                    titulo=f"Faltas de asistencia en {materia.nombre}",
                    mensaje=f"Tienes {falta['total_faltas']} faltas recientes en {materia.nombre}. "
                            f"Esto puede afectar tu rendimiento académico.",
                    url_accion=f"/asistencias?materia={materia.id}&estudiante={estudiante.id}"
                )

                notificaciones_creadas += 1
                logger.info(f"Notificación de asistencia creada para {estudiante.username} en {materia.nombre}")

                # Si la materia tiene profesor, notificar también
                if materia.profesor:
                    Notificacion.objects.create(
                        usuario=materia.profesor,
                        tipo='INFO',
                        titulo=f"Estudiante con inasistencias: {estudiante.first_name}",
                        mensaje=f"El estudiante {estudiante.first_name} {estudiante.last_name} "
                                f"tiene {falta['total_faltas']} faltas recientes en tu materia.",
                        url_accion=f"/asistencias?materia={materia.id}&estudiante={estudiante.id}"
                    )
                    notificaciones_creadas += 1

            except Exception as e:
                logger.error(f"Error al crear notificación de asistencia: {str(e)}")

    logger.info(f"Proceso completado: {notificaciones_creadas} notificaciones de asistencia creadas")
    return notificaciones_creadas

def notificar_administradores():
    """Genera resúmenes de notificaciones para administradores."""
    logger.info("Generando resumen para administradores...")

    # Obtener estadísticas generales
    total_predicciones_bajo = Prediccion.objects.filter(
        nivel_rendimiento='BAJO',
        fecha_prediccion__gte=datetime.now() - timedelta(days=14)
    ).count()

    total_estudiantes = User.objects.filter(role='ESTUDIANTE').count()

    # Contar estudiantes con al menos una predicción de nivel BAJO
    estudiantes_en_riesgo = Prediccion.objects.filter(
        nivel_rendimiento='BAJO',
        fecha_prediccion__gte=datetime.now() - timedelta(days=14)
    ).values('estudiante').distinct().count()

    porcentaje_riesgo = (estudiantes_en_riesgo / total_estudiantes) * 100 if total_estudiantes > 0 else 0

    # Buscar administradores
    administradores = User.objects.filter(role='ADMINISTRATIVO')

    notificaciones_creadas = 0

    # Si el porcentaje de riesgo es preocupante (más del 20%), notificar a admins
    if porcentaje_riesgo > 20:
        for admin in administradores:
            Notificacion.objects.create(
                usuario=admin,
                tipo='ALERTA',  # Ajustado a los TIPO_CHOICES definidos en el modelo
                titulo="Alerta: Estudiantes en riesgo académico",
                mensaje=f"El {porcentaje_riesgo:.1f}% de los estudiantes están en riesgo académico. "
                        f"Se recomienda revisar los informes detallados.",
                url_accion="/predicciones/estudiantes_en_riesgo"
            )
            notificaciones_creadas += 1
            logger.info(f"Resumen enviado a administrador {admin.username}")

    logger.info(f"Proceso de resúmenes completado: {notificaciones_creadas} notificaciones creadas")
    return notificaciones_creadas

# Ejecutar las funciones cuando se ejecuta directamente el script
if __name__ == "__main__":
    try:
        # Ejecutar las funciones
        predicciones_generadas, predicciones_fallidas = generar_predicciones_automaticas()
        notificaciones_asistencia = notificar_asistencia()
        notificaciones_admin = notificar_administradores()

        total_notificaciones = notificaciones_asistencia + notificaciones_admin

        logger.info("Proceso automático de notificaciones y predicciones completado exitosamente")
        logger.info(f"Resumen: {predicciones_generadas} predicciones generadas, {total_notificaciones} notificaciones creadas")

        print(f"Proceso completado: {predicciones_generadas} predicciones generadas, {total_notificaciones} notificaciones creadas")
    except Exception as e:
        logger.critical(f"Error crítico en el proceso: {str(e)}")
        print(f"Error en el proceso: {str(e)}")

# Cuando estás en el shell interactivo de Django, este bloque ejecutará todas las funciones
# Este bloque se ejecutará cuando se use: exec(open('scripts/notificaciones_automaticas.py').read())
try:
    print("Ejecutando script de notificaciones desde el shell interactivo...")
    predicciones_generadas, predicciones_fallidas = generar_predicciones_automaticas()
    notificaciones_asistencia = notificar_asistencia()
    notificaciones_admin = notificar_administradores()

    total_notificaciones = notificaciones_asistencia + notificaciones_admin

    print(f"Proceso completado exitosamente!")
    print(f"Resumen: {predicciones_generadas} predicciones generadas")
    print(f"{total_notificaciones} notificaciones creadas")
except Exception as e:
    print(f"Error al ejecutar el script: {str(e)}")

