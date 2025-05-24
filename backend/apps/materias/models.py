from django.db import models
from django.core.exceptions import ValidationError
from apps.usuarios.models import User

def validar_profesor(usuario):
    """Valida que el usuario tenga el rol de PROFESOR"""
    if usuario.role != 'PROFESOR':
        raise ValidationError('El usuario debe tener el rol de PROFESOR')

class Materia(models.Model):
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True, null=True)
    creditos = models.PositiveSmallIntegerField()
    profesor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='materias_impartidas',
        validators=[validar_profesor]
    )

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
