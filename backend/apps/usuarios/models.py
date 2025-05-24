from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError


def validar_estudiante(user):

    if user.role != 'ESTUDIANTE':
        raise ValidationError('Solo usuarios con rol ESTUDIANTE pueden ser asignados a cursos como estudiantes')


class User(AbstractUser):
    ROLE_CHOICES = [
        ('PROFESOR', 'Profesor'),
        ('ESTUDIANTE', 'Estudiante'),
        ('ADMINISTRATIVO', 'Administrativo'),
    ]
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='ESTUDIANTE'
    )
    curso = models.ForeignKey(
        'cursos.Curso',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='estudiantes',
        help_text='Curso al que pertenece el estudiante',
    )

    def clean(self):

        if self.curso and self.role != 'ESTUDIANTE':
            raise ValidationError('Solo los usuarios con rol ESTUDIANTE pueden ser asignados a un curso')

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
