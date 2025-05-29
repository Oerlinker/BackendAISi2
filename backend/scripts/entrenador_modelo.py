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
import traceback


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aula_inteligente.settings')

import django
django.setup()

from django.db.models import Avg, Count
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


console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'models')
if not os.path.exists(MODELS_DIR):
    os.makedirs(MODELS_DIR)


def entrenar_modelo_general():
    """
    Entrena un modelo general basado en todas las notas disponibles.
    """
    model_path = os.path.join(MODELS_DIR, 'modelo_general.pkl')


    if os.path.exists(model_path):
        logger.info(f"El modelo general ya existe en {model_path}. Saltando entrenamiento.")
        print(f"El modelo general ya existe en {model_path}. Saltando entrenamiento.")
        try:
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            return model
        except Exception as e:
            logger.warning(f"Error al cargar el modelo existente: {str(e)}. Se volverá a entrenar.")
            print(f"Error al cargar el modelo existente: {str(e)}. Se volverá a entrenar.")

    logger.info("Iniciando entrenamiento del modelo general...")
    print("Iniciando entrenamiento del modelo general...")

    features = []
    labels = []


    notas = Nota.objects.all()
    total_notas = notas.count()
    logger.info(f"Total de notas encontradas: {total_notas}")
    print(f"Total de notas encontradas: {total_notas}")

    if total_notas < 30:
        logger.warning("No hay suficientes datos para entrenar el modelo general (mínimo 30 registros)")
        print("No hay suficientes datos para entrenar el modelo general (mínimo 30 registros)")
        return None


    notas_procesadas = 0
    for i, nota in enumerate(notas):
        try:

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

            notas_procesadas += 1


            if (i + 1) % 20 == 0 or i == total_notas - 1:
                porcentaje = (i + 1) / total_notas * 100
                mensaje = f"Progreso: {i + 1}/{total_notas} notas procesadas ({porcentaje:.1f}%)"
                logger.info(mensaje)
                print(mensaje)

        except Exception as e:
            logger.error(f"Error procesando nota ID {nota.id}: {str(e)}")
            print(f"Error procesando nota ID {nota.id}: {str(e)}")
            continue

    logger.info(f"Entrenando modelo RandomForest con {len(features)} características...")
    print(f"Entrenando modelo RandomForest con {len(features)} características...")

    X = np.array(features)
    y = np.array(labels)


    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=None,
        min_samples_split=2,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X, y)


    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    logger.info(f"Modelo general entrenado y guardado en {model_path}")
    print(f"Modelo general entrenado y guardado en {model_path}")
    return model


def entrenar_modelos_por_materia():
    """
    Entrena modelos específicos para cada materia que tenga suficientes datos.
    """
    logger.info("Iniciando entrenamiento de modelos por materia...")
    print("Iniciando entrenamiento de modelos por materia...")


    materias = Materia.objects.annotate(total_notas=Count('nota')).filter(total_notas__gte=20)
    total_materias = materias.count()

    logger.info(f"Se encontraron {total_materias} materias con suficientes datos para entrenar")
    print(f"Se encontraron {total_materias} materias con suficientes datos para entrenar")

    materias_procesadas = 0
    modelos_entrenados = 0

    for i, materia in enumerate(materias):
        try:
            logger.info(f"[{i+1}/{total_materias}] Procesando materia: {materia.nombre} (ID: {materia.id})")
            print(f"[{i+1}/{total_materias}] Procesando materia: {materia.nombre} (ID: {materia.id})")


            model_path = os.path.join(MODELS_DIR, f'modelo_materia_{materia.id}.pkl')
            if os.path.exists(model_path):
                logger.info(f"  El modelo para materia {materia.nombre} ya existe en {model_path}. Saltando entrenamiento.")
                print(f"  El modelo para materia {materia.nombre} ya existe en {model_path}. Saltando entrenamiento.")
                modelos_entrenados += 1
                materias_procesadas += 1
                porcentaje = materias_procesadas / total_materias * 100
                logger.info(f"Progreso general: {materias_procesadas}/{total_materias} materias ({porcentaje:.1f}%)")
                print(f"Progreso general: {materias_procesadas}/{total_materias} materias ({porcentaje:.1f}%)")
                continue


            notas = Nota.objects.filter(materia=materia)
            total_notas_materia = notas.count()

            logger.info(f"  - {total_notas_materia} notas encontradas para esta materia")
            print(f"  - {total_notas_materia} notas encontradas para esta materia")

            features = []
            labels = []


            for j, nota in enumerate(notas):
                try:

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


                    if total_notas_materia > 50 and (j + 1) % 20 == 0:
                        porcentaje = (j + 1) / total_notas_materia * 100
                        logger.info(f"    Progreso: {j + 1}/{total_notas_materia} notas procesadas ({porcentaje:.1f}%)")
                        print(f"    Progreso: {j + 1}/{total_notas_materia} notas procesadas ({porcentaje:.1f}%)")

                except Exception as e:
                    logger.warning(f"Error procesando nota ID {nota.id} para materia {materia.nombre}: {str(e)}")
                    continue

            logger.info(f"  Entrenando modelo para materia {materia.nombre} con {len(features)} registros...")
            print(f"  Entrenando modelo para materia {materia.nombre} con {len(features)} registros...")

            X = np.array(features)
            y = np.array(labels)


            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=None,
                min_samples_split=2,
                random_state=42,
                n_jobs=-1
            )
            model.fit(X, y)


            model_path = os.path.join(MODELS_DIR, f'modelo_materia_{materia.id}.pkl')
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            logger.info(f"  Modelo para materia {materia.nombre} entrenado y guardado en {model_path}")
            print(f"  Modelo para materia {materia.nombre} entrenado y guardado en {model_path}")
            modelos_entrenados += 1

        except Exception as e:
            logger.error(f"Error procesando materia {materia.nombre}: {str(e)}")
            logger.error(traceback.format_exc())
            print(f"Error procesando materia {materia.nombre}: {str(e)}")

        materias_procesadas += 1
        porcentaje = materias_procesadas / total_materias * 100
        logger.info(f"Progreso general: {materias_procesadas}/{total_materias} materias ({porcentaje:.1f}%)")
        print(f"Progreso general: {materias_procesadas}/{total_materias} materias ({porcentaje:.1f}%)")

    logger.info(f"Procesamiento completado: {materias_procesadas} materias procesadas, {modelos_entrenados} modelos entrenados")
    return modelos_entrenados


def generar_metadatos_entrenamiento():
    """
    Genera un archivo de metadatos con información sobre el entrenamiento.
    """
    logger.info("Generando metadatos del entrenamiento...")
    print("Generando metadatos del entrenamiento...")

    metadata = {
        'fecha_entrenamiento': datetime.now().isoformat(),
        'total_notas': Nota.objects.count(),
        'total_asistencias': Asistencia.objects.count(),
        'total_participaciones': Participacion.objects.count(),
        'total_materias': Materia.objects.count(),
        'modelos_disponibles': [
            f for f in os.listdir(MODELS_DIR)
            if f.endswith('.pkl') and f != 'metadata.pkl'
        ]
    }

    metadata_path = os.path.join(MODELS_DIR, 'metadata.pkl')
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)

    logger.info(f"Metadatos de entrenamiento guardados en {metadata_path}")
    print(f"Metadatos de entrenamiento guardados en {metadata_path}")
    return metadata


if __name__ == "__main__":
    logger.info("=== INICIO DEL PROCESO DE ENTRENAMIENTO ===")
    print("\n=== INICIO DEL PROCESO DE ENTRENAMIENTO ===")
    print(f"Los logs se guardarán en: {os.path.abspath('entrenamiento_modelo.log')}")
    print(f"Los modelos se guardarán en: {os.path.abspath(MODELS_DIR)}")
    print("\nEste proceso puede tardar varios minutos dependiendo de la cantidad de datos.\n")

    try:
        print("\n--- Fase 1: Entrenamiento del modelo general ---")
        modelo_general = entrenar_modelo_general()

        print("\n--- Fase 2: Entrenamiento de modelos por materia ---")
        total_modelos = entrenar_modelos_por_materia()

        print("\n--- Fase 3: Generación de metadatos ---")
        metadata = generar_metadatos_entrenamiento()

        logger.info("=== PROCESO DE ENTRENAMIENTO COMPLETADO CON ÉXITO ===")
        print("\n=== PROCESO DE ENTRENAMIENTO COMPLETADO CON ÉXITO ===")
        print(f"Entrenamiento completado: modelo general + {total_modelos} modelos por materia")

        print("\nResumen del entrenamiento:")
        print(f"- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"- Total de notas procesadas: {metadata['total_notas']}")
        print(f"- Total de materias con modelo específico: {total_modelos}")
        print(f"- Modelos guardados en: {os.path.abspath(MODELS_DIR)}")

    except Exception as e:
        logger.exception(f"Error durante el proceso de entrenamiento: {str(e)}")
        print(f"\nError durante el entrenamiento: {str(e)}")
        logger.error(traceback.format_exc())
        print(traceback.format_exc())
        sys.exit(1)
