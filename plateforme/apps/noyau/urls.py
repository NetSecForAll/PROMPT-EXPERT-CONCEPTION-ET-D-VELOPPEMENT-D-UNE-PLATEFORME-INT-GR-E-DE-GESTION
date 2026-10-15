from django.urls import path

from . import views

app_name = "noyau"

urlpatterns = [
    path("sites/", views.SiteListeView.as_view(), name="sites"),
    path("sites/nouveau/", views.SiteCreationView.as_view(), name="site_creer"),
    path("sites/<int:pk>/", views.SiteModificationView.as_view(), name="site_modifier"),
    path("services/", views.ServiceListeView.as_view(), name="services"),
    path("services/nouveau/", views.ServiceCreationView.as_view(), name="service_creer"),
    path("services/<int:pk>/", views.ServiceModificationView.as_view(), name="service_modifier"),
    path("agents/", views.AgentListeView.as_view(), name="agents"),
    path("agents/nouveau/", views.AgentCreationView.as_view(), name="agent_creer"),
    path("agents/<int:pk>/", views.AgentModificationView.as_view(), name="agent_modifier"),
    path("parametres/", views.ParametreListeView.as_view(), name="parametres"),
    path("parametres/<int:pk>/", views.ParametreModificationView.as_view(), name="parametre_modifier"),
    path("comptes/", views.UtilisateurListeView.as_view(), name="utilisateurs"),
    path("comptes/nouveau/", views.UtilisateurCreationView.as_view(), name="utilisateur_creer"),
    path("comptes/<int:pk>/", views.UtilisateurModificationView.as_view(), name="utilisateur_modifier"),
    path("comptes/<int:pk>/mot-de-passe/", views.ReinitialisationMotDePasseView.as_view(), name="utilisateur_mdp"),
    path("profils/", views.ProfilListeView.as_view(), name="profils"),
]
