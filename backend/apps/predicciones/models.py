from django.db import models
from apps.usuarios.models import User
from apps.materias.models import Materia


class Prediccion(models.Model):
    NIVEL_CHOICES = [
        ('BAJO', 'Rendimiento Bajo'),
        ('MEDIO', 'Rendimiento Medio'),
        ('ALTO', 'Rendimiento Alto'),
    ]

    estudiante = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'ESTUDIANTE'}
    )
    materia = models.ForeignKey(
        Materia,
        on_delete=models.CASCADE
    )
    fecha_prediccion = models.DateTimeField(auto_now_add=True)
    valor_numerico = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text='Valor numérico predicho'
    )
    nivel_rendimiento = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES
    )
    # Variables predictoras
    promedio_notas = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text='Promedio de notas usado para predecir'
    )
    porcentaje_asistencia = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text='Porcentaje de asistencia usado para predecir'
    )
    promedio_participaciones = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        help_text='Promedio de participaciones usado para predecir'
    )

    class Meta:
        verbose_name = "Predicción"
        verbose_name_plural = "Predicciones"

    def __str__(self):
        return f"Predicción para {self.estudiante.username} en {self.materia.nombre}: {self.nivel_rendimiento}"

