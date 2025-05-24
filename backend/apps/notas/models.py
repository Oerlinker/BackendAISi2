from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.usuarios.models import User
from apps.materias.models import Materia


class Periodo(models.Model):
    TRIMESTRE_CHOICES = [
        ('PRIMERO', 'Primer Trimestre'),
        ('SEGUNDO', 'Segundo Trimestre'),
        ('TERCERO', 'Tercer Trimestre'),
    ]

    nombre = models.CharField(max_length=100)
    trimestre = models.CharField(max_length=10, choices=TRIMESTRE_CHOICES)
    año_academico = models.CharField(max_length=9, help_text="Formato: AAAA-AAAA (ej: 2024-2025)")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    def __str__(self):
        return f"{self.nombre} - {self.get_trimestre_display()} ({self.año_academico})"

    class Meta:
        verbose_name = "Periodo"
        verbose_name_plural = "Periodos"
        unique_together = ('trimestre', 'año_academico')


class Nota(models.Model):
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'ESTUDIANTE'})
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE)

    ser_puntaje = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Asistencia, disciplina, participaciones (10 puntos)"
    )
    saber_puntaje = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(35)],
        help_text="Exámenes (35 puntos)"
    )
    hacer_puntaje = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(35)],
        help_text="Tareas, prácticos (35 puntos)"
    )
    decidir_puntaje = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Promedio de ser, saber y hacer (10 puntos)"
    )

    autoevaluacion_ser = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Autoevaluación del estudiante para el ser (0-5 puntos)",
        default=0
    )
    autoevaluacion_decidir = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Autoevaluación del estudiante para el decidir (0-5 puntos)",
        default=0
    )

    fecha_registro = models.DateTimeField(auto_now_add=True)
    ultima_modificacion = models.DateTimeField(auto_now=True)
    comentario = models.TextField(blank=True, null=True)

    @property
    def ser_total(self):
        return self.ser_puntaje + self.autoevaluacion_ser

    @property
    def decidir_total(self):
        return self.decidir_puntaje + self.autoevaluacion_decidir

    @property
    def nota_total(self):
        return self.ser_puntaje + self.saber_puntaje + self.hacer_puntaje + self.decidir_puntaje + self.autoevaluacion_ser + self.autoevaluacion_decidir

    @property
    def aprobado(self):
        return self.nota_total >= 60

    def save(self, *args, **kwargs):
        if not self.decidir_puntaje:
            promedio = (self.ser_puntaje + self.saber_puntaje + self.hacer_puntaje) / 3

            self.decidir_puntaje = min(promedio, 10)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.estudiante.username} - {self.materia.nombre} - {self.periodo}: {self.nota_total}/100"

    class Meta:
        verbose_name = "Nota"
        verbose_name_plural = "Notas"
        unique_together = ('estudiante', 'materia', 'periodo')
