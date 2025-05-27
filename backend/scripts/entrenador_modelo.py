"""
Script para entrenar el modelo de predicción de rendimiento académico
y guardarlo para su uso posterior sin necesidad de re-entrenarlo cada vez.

Este script está diseñado para ejecutarse periódicamente (por ejemplo, diariamente)
a través de un programador de tareas o cron job.
"""

import os
import sys
import logging
import pickle
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aula_inteligente.settings')

import django
django.setup()

from django.db.models import Avg
from apps.notas.models import Nota
from apps.asistencias.models import Asistencia
from apps.participaciones.models import Participacion
from apps.materias.models import Materia


logging.basicConfig(
    filename='entrenamiento_modelo.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)


def entrenar_modelo_general():

    logger.info("Iniciando entrenamiento del modelo general...")

    features = []
    labels = []


    notas = Nota.objects.all()

    if notas.count() < 30:
        logger.warning("No hay suficientes datos para entrenar el modelo general (mínimo 30 registros)")
        return None


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
            float(nota.autoevaluacion_ser),
            float(nota.autoevaluacion_decidir),
            porcentaje_asistencia,
            promedio_participaciones
        ])

        # Etiqueta a predecir (nota total)
        labels.append(float(nota.nota_total))

    X = np.array(features)
    y = np.array(labels)


    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=None,
        min_samples_split=2,
        random_state=42
    )
    model.fit(X, y)


    model_path = os.path.join(MODELS_DIR, 'modelo_general.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    logger.info(f"Modelo general entrenado y guardado en {model_path}")
    return model


def entrenar_modelos_por_materia():

    logger.info("Iniciando entrenamiento de modelos por materia...")

    materias = Materia.objects.all()
    materias_procesadas = 0
    modelos_entrenados = 0

    for materia in materias:
        logger.info(f"Procesando materia: {materia.nombre}")


        notas = Nota.objects.filter(materia=materia)

        if notas.count() < 20:
            logger.info(f"Materia {materia.nombre}: insuficientes datos para entrenar modelo específico (mínimo 20 registros)")
            continue

        features = []
        labels = []


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
                float(nota.autoevaluacion_ser),
                float(nota.autoevaluacion_decidir),
                porcentaje_asistencia,
                promedio_participaciones
            ])

            labels.append(float(nota.nota_total))

        X = np.array(features)
        y = np.array(labels)

        # Entrenar modelo específico para esta materia
        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=None,
            min_samples_split=2,
            random_state=42
        )
        model.fit(X, y)


        model_path = os.path.join(MODELS_DIR, f'modelo_materia_{materia.id}.pkl')
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)

        logger.info(f"Modelo para materia {materia.nombre} entrenado y guardado en {model_path}")
        modelos_entrenados += 1
        materias_procesadas += 1

    logger.info(f"Procesamiento completado: {materias_procesadas} materias procesadas, {modelos_entrenados} modelos entrenados")
    return modelos_entrenados


def generar_metadatos_entrenamiento():
    """
    Genera un archivo de metadatos con información sobre el entrenamiento.
    """
    metadata = {
        'fecha_entrenamiento': datetime.now().isoformat(),
        'total_notas': Nota.objects.count(),
        'total_asistencias': Asistencia.objects.count(),
        'total_participaciones': Participacion.objects.count(),
        'total_materias': Materia.objects.count()
    }

    metadata_path = os.path.join(MODELS_DIR, 'metadata.pkl')
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)

    logger.info(f"Metadatos de entrenamiento guardados en {metadata_path}")


if __name__ == "__main__":
    logger.info("=== INICIO DEL PROCESO DE ENTRENAMIENTO ===")

    try:

        modelo_general = entrenar_modelo_general()


        total_modelos = entrenar_modelos_por_materia()


        generar_metadatos_entrenamiento()

        logger.info("=== PROCESO DE ENTRENAMIENTO COMPLETADO CON ÉXITO ===")
        print(f"Entrenamiento completado: modelo general + {total_modelos} modelos por materia")

    except Exception as e:
        logger.exception(f"Error durante el proceso de entrenamiento: {str(e)}")
        print(f"Error durante el entrenamiento: {str(e)}")
        sys.exit(1)
