"""
Script para poblar la base de datos con datos de prueba realistas.
"""

import random
from datetime import datetime, timedelta
from decimal import Decimal

from apps.usuarios.models import User
from apps.cursos.models import Curso
from apps.materias.models import Materia
from apps.notas.models import Periodo, Nota
from apps.asistencias.models import Asistencia
from apps.participaciones.models import Participacion
from django.db import transaction

print("Iniciando poblamiento de datos...")


def crear_periodos():
    print("Creando periodos academicos...")
    periodos = []

    periodo1, _ = Periodo.objects.get_or_create(
        nombre="Primer Trimestre",
        trimestre="PRIMERO",
        año_academico="2024-2025",
        fecha_inicio=datetime(2024, 8, 1),
        fecha_fin=datetime(2024, 11, 15)
    )
    periodos.append(periodo1)

    periodo2, _ = Periodo.objects.get_or_create(
        nombre="Segundo Trimestre",
        trimestre="SEGUNDO",
        año_academico="2024-2025",
        fecha_inicio=datetime(2024, 11, 16),
        fecha_fin=datetime(2025, 2, 28)
    )
    periodos.append(periodo2)

    periodo3, _ = Periodo.objects.get_or_create(
        nombre="Tercer Trimestre",
        trimestre="TERCERO",
        año_academico="2024-2025",
        fecha_inicio=datetime(2025, 3, 1),
        fecha_fin=datetime(2025, 6, 15)
    )
    periodos.append(periodo3)

    print(f"Periodos creados: {len(periodos)}")
    return periodos


def generar_fechas_clase():
    fecha_inicio = datetime(2024, 8, 1)
    fecha_fin = datetime(2025, 6, 15)

    fechas = []
    fecha_actual = fecha_inicio

    while fecha_actual <= fecha_fin:

        if fecha_actual.weekday() < 5:
            fechas.append(fecha_actual.date())
        fecha_actual += timedelta(days=1)

    print(f"Fechas de clase generadas: {len(fechas)}")
    return fechas


def crear_asistencias(cursos, fechas):
    print("Creando asistencias...")
    contador = 0

    for curso in cursos:
        estudiantes = User.objects.filter(curso=curso, role='ESTUDIANTE')
        materias = curso.materias.all()

        fechas_muestra = random.sample(fechas, min(len(fechas), 30))

        for fecha in fechas_muestra:
            for estudiante in estudiantes:
                for materia in materias:

                    presente = random.random() <= 0.9
                    justificacion = None if presente else random.choice(["Enfermedad", "Cita medica", None])

                    try:
                        Asistencia.objects.get_or_create(
                            estudiante=estudiante,
                            materia=materia,
                            fecha=fecha,
                            defaults={
                                'presente': presente,
                                'justificacion': justificacion
                            }
                        )
                        contador += 1
                        if contador % 500 == 0:
                            print(f"  {contador} asistencias creadas...")
                    except Exception as e:
                        print(f"Error al crear asistencia: {e}")

    print(f"Total asistencias: {contador}")


def crear_participaciones(cursos, fechas):
    print("Creando participaciones...")
    contador = 0
    tipos = ['VOLUNTARIA', 'SOLICITADA', 'EJERCICIO', 'PRESENTACION', 'DEBATE']

    for curso in cursos:
        estudiantes = User.objects.filter(curso=curso, role='ESTUDIANTE')
        materias = curso.materias.all()

        fechas_muestra = random.sample(fechas, min(len(fechas), 20))

        for fecha in fechas_muestra:
            for materia in materias:

                participantes = random.sample(list(estudiantes), min(7, len(estudiantes)))

                for estudiante in participantes:

                    for _ in range(random.randint(1, 2)):
                        tipo = random.choice(tipos)
                        valor = random.randint(6, 10)  # Valores entre 6-10
                        descripcion = f"Participacion {tipo.lower()}"

                        try:
                            Participacion.objects.create(
                                estudiante=estudiante,
                                materia=materia,
                                fecha=fecha,
                                tipo=tipo,
                                valor=valor,
                                descripcion=descripcion
                            )
                            contador += 1
                        except Exception as e:
                            print(f"Error al crear participacion: {e}")

    print(f"Total participaciones: {contador}")


def crear_notas(periodos, cursos):
    print("Creando notas...")
    contador = 0

    for periodo in periodos:
        for curso in cursos:
            estudiantes = User.objects.filter(curso=curso, role='ESTUDIANTE')
            materias = curso.materias.all()

            for estudiante in estudiantes:
                for materia in materias:
                    # Componentes de evaluacion
                    ser = Decimal(str(round(random.uniform(6, 10), 2)))
                    saber = Decimal(str(round(random.uniform(20, 35), 2)))
                    hacer = Decimal(str(round(random.uniform(20, 35), 2)))
                    decidir = Decimal(str(round(random.uniform(6, 10), 2)))

                    auto_ser = Decimal(str(round(random.uniform(3, 5), 2)))
                    auto_decidir = Decimal(str(round(random.uniform(3, 5), 2)))

                    try:
                        Nota.objects.get_or_create(
                            estudiante=estudiante,
                            materia=materia,
                            periodo=periodo,
                            defaults={
                                'ser_puntaje': ser,
                                'saber_puntaje': saber,
                                'hacer_puntaje': hacer,
                                'decidir_puntaje': decidir,
                                'autoevaluacion_ser': auto_ser,
                                'autoevaluacion_decidir': auto_decidir,
                                'comentario': "Buen desempeno"
                            }
                        )
                        contador += 1
                    except Exception as e:
                        print(f"Error al crear nota: {e}")

    print(f"Total notas: {contador}")


def poblar():

    if not Curso.objects.exists() or not User.objects.filter(role='ESTUDIANTE').exists():
        print("Error: No hay cursos o estudiantes en la base de datos")
        return

    with transaction.atomic():
        periodos = crear_periodos()
        fechas = generar_fechas_clase()
        cursos = Curso.objects.all()

        crear_asistencias(cursos, fechas)
        crear_participaciones(cursos, fechas)
        crear_notas(periodos, cursos)

    print("Poblamiento completado con exito")


poblar()
