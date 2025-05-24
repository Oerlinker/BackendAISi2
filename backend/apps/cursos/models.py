from django.db import models
from apps.materias.models import Materia

class Curso(models.Model):
    NIVEL_CHOICES = [
        ('PRIMARIA', 'Primaria'),
        ('SECUNDARIA', 'Secundaria'),
    ]

    nombre   = models.CharField(max_length=20, unique=True)
    nivel    = models.CharField(max_length=12, choices=NIVEL_CHOICES)
    materias = models.ManyToManyField(Materia, related_name='cursos')

    def __str__(self):
        return f"{self.nombre} ({self.nivel})"
