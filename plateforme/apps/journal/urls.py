from django.urls import path

from . import views

app_name = "journal"

urlpatterns = [
    path("", views.EvenementListeView.as_view(), name="evenements"),
    path("modifications/", views.HistoriqueListeView.as_view(), name="historique"),
]
