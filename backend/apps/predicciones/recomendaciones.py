class GeneradorRecomendaciones:

    @staticmethod
    def recomendar_por_asistencia(porcentaje_asistencia):

        if porcentaje_asistencia < 70:
            return [
                "Asistir regularmente a clases es fundamental para tu aprendizaje.",
                "Establece alarmas o recordatorios para no olvidar tus clases.",
                "Si tienes dificultades para asistir, comunícate con tu profesor o tutor."
            ]
        elif porcentaje_asistencia < 85:
            return [
                "Tu asistencia podría mejorar. Intenta llegar puntualmente a todas las clases.",
                "Organiza tu horario para evitar ausencias innecesarias."
            ]
        else:
            return [
                "¡Excelente asistencia! Mantén esta disciplina.",
            ]

    @staticmethod
    def recomendar_por_participacion(promedio_participacion):

        if promedio_participacion < 5:
            return [
                "Participa más activamente en las discusiones de clase.",
                "Prepara una pregunta o comentario antes de cada clase.",
                "Forma un grupo de estudio para practicar la expresión de ideas."
            ]
        elif promedio_participacion < 8:
            return [
                "Tus participaciones son buenas, pero podrías profundizar más en tus aportes.",
                "Intenta relacionar los temas de clase con ejemplos prácticos al participar."
            ]
        else:
            return [
                "Tus participaciones son excelentes. Sigue contribuyendo con ese nivel de calidad."
            ]

    @staticmethod
    def recomendar_por_componente(ser_puntaje, saber_puntaje, hacer_puntaje, decidir_puntaje):

        recomendaciones = []

        if ser_puntaje < 7:
            recomendaciones.extend([
                "Trabaja en tu actitud y valores durante la clase.",
                "La puntualidad y responsabilidad son aspectos importantes de tu formación."
            ])

        if saber_puntaje < 25:  # Considerando que el máximo es 35
            recomendaciones.extend([
                "Dedica más tiempo a estudiar los conceptos teóricos.",
                "Crea mapas conceptuales o resúmenes para organizar mejor la información.",
                "Busca material complementario sobre los temas que te resultan difíciles."
            ])

        if hacer_puntaje < 25:  # Considerando que el máximo es 35
            recomendaciones.extend([
                "Practica más con ejercicios y problemas aplicados.",
                "Forma grupos de estudio para resolver ejercicios prácticos.",
                "No dejes los trabajos y tareas para último momento."
            ])

        if decidir_puntaje < 7:  # Considerando que el máximo es 10
            recomendaciones.extend([
                "Intenta conectar los diferentes temas y ver cómo se relacionan entre sí.",
                "Piensa en cómo aplicar lo aprendido en situaciones reales."
            ])

        return recomendaciones

    @staticmethod
    def recomendar_tecnicas_estudio(nota_total):

        if nota_total < 60:
            return [
                "Técnica Pomodoro: Estudia 25 minutos y descansa 5, repite el ciclo.",
                "Implementa un horario de estudio regular y estructurado.",
                "Busca un tutor o compañero de estudio que pueda ayudarte.",
                "Identifica tu estilo de aprendizaje (visual, auditivo, kinestésico) y adapta tus métodos."
            ]
        elif nota_total < 80:
            return [
                "Utiliza mapas mentales para organizar la información.",
                "Practica la técnica de explicación: enseña a otros lo que has aprendido.",
                "Alterna entre diferentes materias para mantener el interés."
            ]
        else:
            return [
                "Profundiza en temas avanzados relacionados con la materia.",
                "Considera formar grupos de estudio donde puedas compartir tu conocimiento."
            ]

    @staticmethod
    def generar_recomendaciones(prediccion, asistencias=None, participaciones=None, notas=None):

        todas_recomendaciones = []

        if prediccion.nivel_rendimiento == 'BAJO':
            todas_recomendaciones.append({
                "categoria": "Urgente",
                "mensaje": "Tu rendimiento está por debajo del nivel esperado. Es necesario tomar acciones inmediatas."
            })
        elif prediccion.nivel_rendimiento == 'MEDIO':
            todas_recomendaciones.append({
                "categoria": "Atención",
                "mensaje": "Tu rendimiento es aceptable, pero hay espacio para mejorar."
            })

        for rec in GeneradorRecomendaciones.recomendar_por_asistencia(float(prediccion.porcentaje_asistencia)):
            todas_recomendaciones.append({
                "categoria": "Asistencia",
                "mensaje": rec
            })

        for rec in GeneradorRecomendaciones.recomendar_por_participacion(float(prediccion.promedio_participaciones)):
            todas_recomendaciones.append({
                "categoria": "Participación",
                "mensaje": rec
            })

        if notas and notas.exists():
            ultima_nota = notas.order_by('-periodo__fecha_inicio').first()
            if ultima_nota:
                componentes_rec = GeneradorRecomendaciones.recomendar_por_componente(
                    float(ultima_nota.ser_puntaje),
                    float(ultima_nota.saber_puntaje),
                    float(ultima_nota.hacer_puntaje),
                    float(ultima_nota.decidir_puntaje)
                )
                for rec in componentes_rec:
                    todas_recomendaciones.append({
                        "categoria": "Componentes",
                        "mensaje": rec
                    })

        for rec in GeneradorRecomendaciones.recomendar_tecnicas_estudio(float(prediccion.valor_numerico)):
            todas_recomendaciones.append({
                "categoria": "Técnicas de Estudio",
                "mensaje": rec
            })

        return todas_recomendaciones
