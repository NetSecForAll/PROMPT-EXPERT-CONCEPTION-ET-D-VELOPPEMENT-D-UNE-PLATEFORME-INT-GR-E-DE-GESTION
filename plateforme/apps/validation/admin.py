from django.contrib import admin

from .models import Circuit, Decision, Delegation, EtapeCircuit, InstanceValidation


class EtapeInline(admin.TabularInline):
    model = EtapeCircuit
    extra = 0


@admin.register(Circuit)
class CircuitAdmin(admin.ModelAdmin):
    inlines = [EtapeInline]


admin.site.register(Delegation)


@admin.register(InstanceValidation)
class InstanceAdmin(admin.ModelAdmin):
    list_display = ("circuit", "demandeur", "statut", "soumise_le")
    readonly_fields = [f.name for f in InstanceValidation._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ("instance", "valideur", "decision", "horodatage")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
