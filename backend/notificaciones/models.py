from django.db import models
from apps.usuarios.models import User
from django.utils import timezone

class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('INFO', 'Información'),
        ('ALERTA', 'Alerta'),
        ('PREDICCION', 'Predicción'),
        ('RECORDATORIO', 'Recordatorio'),
        ('SISTEMA', 'Sistema'),
    ]

    ESTADO_CHOICES = [
        ('NO_LEIDA', 'No Leída'),
        ('LEIDA', 'Leída'),
        ('ARCHIVADA', 'Archivada'),
    ]

    usuario = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notificaciones',
        help_text='Usuario destinatario de la notificación'
    )
    titulo = models.CharField(
        max_length=100,
        help_text='Título breve de la notificación'
    )
    mensaje = models.TextField(
        help_text='Contenido completo de la notificación'
    )
    tipo = models.CharField(
        max_length=15,
        choices=TIPO_CHOICES,
        default='INFO',
        help_text='Categoría de la notificación'
    )
    estado = models.CharField(
        max_length=15,
        choices=ESTADO_CHOICES,
        default='NO_LEIDA',
        help_text='Estado de la notificación'
    )
    fecha_creacion = models.DateTimeField(
        default=timezone.now,
        help_text='Fecha y hora de creación de la notificación'
    )
    fecha_lectura = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Fecha y hora en que se leyó la notificación'
    )
    url_accion = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='URL opcional para dirigir al usuario a una acción específica'
    )

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"{self.titulo} - {self.usuario.username} ({self.get_estado_display()})"

    def marcar_como_leida(self):

        self.estado = 'LEIDA'
        self.fecha_lectura = timezone.now()
        self.save()

    def archivar(self):

        self.estado = 'ARCHIVADA'
        self.save()
