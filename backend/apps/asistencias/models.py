from django.db import models
from apps.usuarios.models import User
from apps.materias.models import Materia

class Asistencia(models.Model):
    estudiante = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'ESTUDIANTE'})
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    fecha = models.DateField()
    presente = models.BooleanField(default=True)
    justificacion = models.TextField(blank=True, null=True)

    def __str__(self):
        estado = "Presente" if self.presente else "Ausente"
        return f"{self.estudiante.username} - {self.materia.nombre} - {self.fecha}: {estado}"

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        unique_together = ('estudiante', 'materia', 'fecha')
