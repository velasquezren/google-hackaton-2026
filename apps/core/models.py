from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from config.settings import SystemRoles

class User(AbstractUser):
    """
    Modelo de usuario del sistema con roles especializados.
    Permite diferenciar entre Administradores, Analistas, Bomberos/Rescatistas y Ciudadanos.
    """
    role = models.CharField(
        max_length=20,
        choices=SystemRoles.CHOICES,
        default=SystemRoles.CITIZEN,
        help_text=_("Rol de acceso asignado al usuario.")
    )
    phone_number = models.CharField(
        max_length=15, 
        blank=True, 
        null=True,
        help_text=_("Número telefónico para alertas de emergencia sms.")
    )

    class Meta:
        db_table = 'core_users'
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')

    def __str__(self) -> str:
        return f"{self.username} ({self.get_role_display()})"
