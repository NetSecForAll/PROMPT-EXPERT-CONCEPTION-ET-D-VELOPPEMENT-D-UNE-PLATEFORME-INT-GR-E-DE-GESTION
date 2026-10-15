from django.urls import path

from . import views

app_name = "validation"

urlpatterns = [
    path("", views.AValiderView.as_view(), name="a_valider"),
    path("<int:pk>/", views.DetailView.as_view(), name="detail"),
    path("toutes/", views.HistoriqueValidationsView.as_view(), name="toutes"),
    path("delegations/", views.DelegationsView.as_view(), name="delegations"),
    path("circuits/", views.CircuitListeView.as_view(), name="circuits"),
    path("circuits/nouveau/", views.CircuitCreationView.as_view(), name="circuit_creer"),
    path("circuits/<int:pk>/", views.CircuitModificationView.as_view(), name="circuit_modifier"),
    path("circuits/<int:circuit>/etapes/nouvelle/", views.EtapeCreationView.as_view(), name="etape_creer"),
    path("etapes/<int:pk>/", views.EtapeModificationView.as_view(), name="etape_modifier"),
]
