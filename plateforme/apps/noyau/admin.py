from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Agent, Parametre, Service, Site, Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rattachement", {"fields": ("agent",)}),)
    list_display = ("username", "agent", "is_active", "is_superuser", "last_login")


for modele in (Site, Service, Agent, Parametre):
    admin.site.register(modele)
