from django.urls import path

from . import views

app_name = "alertes"

urlpatterns = [
    path("", views.MesAlertesView.as_view(), name="liste"),
    path("<int:pk>/prise-en-compte/", views.PriseEnCompteView.as_view(), name="prendre_en_compte"),
]
