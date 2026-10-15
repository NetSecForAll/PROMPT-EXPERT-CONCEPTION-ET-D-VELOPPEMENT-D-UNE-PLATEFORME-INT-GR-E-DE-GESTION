from django.contrib import admin
from django.urls import include, path

from apps.noyau import views_auth
from apps.noyau.views import TableauDeBordView

admin.site.site_header = "Plateforme de gestion — administration technique"
admin.site.site_title = "Administration technique"

urlpatterns = [
    path("", TableauDeBordView.as_view(), name="tableau_de_bord"),
    path("connexion/", views_auth.ConnexionView.as_view(), name="connexion"),
    path("deconnexion/", views_auth.DeconnexionView.as_view(), name="deconnexion"),
    path("mot-de-passe/", views_auth.ChangementMotDePasseView.as_view(), name="mot_de_passe"),
    path("double-authentification/activer/", views_auth.ActivationOTPView.as_view(), name="otp_activation"),
    path("double-authentification/verifier/", views_auth.VerificationOTPView.as_view(), name="otp_verification"),
    path("administration/", include("apps.noyau.urls")),
    path("validations/", include("apps.validation.urls")),
    path("alertes/", include("apps.alertes.urls")),
    path("journal/", include("apps.journal.urls")),
    path("admin-technique/", admin.site.urls),
]

handler403 = "apps.journal.views.acces_refuse"
handler404 = "apps.noyau.views.page_introuvable"
