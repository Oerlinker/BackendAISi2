from django.db import models
from apps.usuarios.models import User
from apps.materias.models import Materia

class Participacion(models.Model):
    TIPO_CHOICES = [
        ('VOLUNTARIA', 'Participación Voluntaria'),
        ('SOLICITADA', 'Participación Solicitada'),
        ('EJERCICIO', 'Resolución de Ejercicio'),
        ('PRESENTACION', 'Presentación'),
        ('DEBATE', 'Participación en Debate'),
    ]

    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'ESTUDIANTE'})
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    fecha = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='VOLUNTARIA')
    descripcion = models.TextField(blank=True, null=True)
    valor = models.PositiveSmallIntegerField(help_text="Valor de 1 a 10 que califica la calidad de la participación")

    def __str__(self):
        return f"{self.estudiante.username} - {self.materia.nombre} - {self.fecha}: {self.tipo} ({self.valor})"

    class Meta:
        verbose_name = "Participación"
        verbose_name_plural = "Participaciones"
