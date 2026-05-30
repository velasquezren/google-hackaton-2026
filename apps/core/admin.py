from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from apps.core.models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Administración personalizada para los usuarios del sistema.
    Permite filtrar por roles y visualizar metadatos críticos en el listado principal.
    """
    fieldsets = UserAdmin.fieldsets + (
        (_('Atributos de Rol y Emergencias'), {'fields': ('role', 'phone_number')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (_('Atributos de Rol y Emergencias'), {
            'fields': ('role', 'phone_number', 'email'),
        }),
    )
    list_display = ('username', 'email', 'role', 'phone_number', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')
    ordering = ('username',)
    
    # Acciones masivas personalizadas en el admin
    actions = ['promote_to_analyst', 'promote_to_first_responder']

    @admin.action(description=_("Promover usuarios seleccionados a Analista de Riesgo"))
    def promote_to_analyst(self, request, queryset):
        rows_updated = queryset.update(role='ANALYST')
        self.message_user(request, f"{rows_updated} usuarios fueron promovidos exitosamente a Analistas de Riesgo.")

    @admin.action(description=_("Promover usuarios seleccionados a Bomberos / Rescatistas"))
    def promote_to_first_responder(self, request, queryset):
        rows_updated = queryset.update(role='FIRST_RESPONDER')
        self.message_user(request, f"{rows_updated} usuarios fueron promovidos exitosamente a Rescatistas.")
