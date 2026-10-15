"""Vues génériques réutilisées par tous les modules : liste, création, modification.

Une liste propose recherche, filtres, tri, pagination et export Excel. L'export
porte exactement sur les lignes que l'utilisateur voit (même requête, sans
pagination).
"""

from io import BytesIO

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import CreateView, ListView, UpdateView
from openpyxl import Workbook
from openpyxl.styles import Font

from apps.journal.services import journaliser

from . import services
from .permissions import PermissionRequiseMixin

LIMITE_EXPORT = 10000


def valeur_attribut(objet, chemin):
    if callable(chemin):
        return chemin(objet)
    valeur = objet
    for partie in chemin.split("."):
        if valeur is None:
            return ""
        affichage = getattr(valeur, f"get_{partie}_display", None)
        valeur = affichage() if affichage else getattr(valeur, partie)
    if isinstance(valeur, bool):
        return "Oui" if valeur else "Non"
    return "" if valeur is None else valeur


class Filtre:
    """Filtre de liste : paramètre d'URL -> condition sur la requête."""

    def __init__(self, parametre, libelle, choix, lookup=None):
        self.parametre = parametre
        self.libelle = libelle
        self._choix = choix
        self.lookup = lookup or parametre

    def choix(self):
        return self._choix() if callable(self._choix) else self._choix

    def appliquer(self, queryset, valeur):
        if valeur in ("", None):
            return queryset
        if valeur in ("oui", "non"):
            valeur = valeur == "oui"
        return queryset.filter(**{self.lookup: valeur})


FILTRE_ACTIF = Filtre("actif", "Statut", [("oui", "Actifs"), ("non", "Désactivés")])


class ListeView(PermissionRequiseMixin, ListView):
    template_name = "composants/liste.html"
    paginate_by = 25
    titre = ""
    colonnes = []  # [(chemin d'attribut ou fonction, libellé, clé de tri ou None)]
    champs_recherche = []
    filtres = []
    tri_defaut = None
    url_creation = None
    permission_creation = None
    # Permission requise pour afficher le bouton « Ouvrir » vers la fiche ;
    # par défaut, la permission de modification du modèle.
    permission_ouverture = None

    def get_base_queryset(self):
        return super().get_queryset()

    def get_queryset(self):
        queryset = self.get_base_queryset()
        recherche = self.request.GET.get("q", "").strip()
        if recherche and self.champs_recherche:
            condition = Q()
            for champ in self.champs_recherche:
                condition |= Q(**{f"{champ}__icontains": recherche})
            queryset = queryset.filter(condition)
        for filtre in self.filtres:
            queryset = filtre.appliquer(queryset, self.request.GET.get(filtre.parametre))
        tri = self.request.GET.get("tri") or self.tri_defaut
        tris_autorises = {c[2] for c in self.colonnes if c[2]}
        if tri and tri.lstrip("-") in tris_autorises:
            queryset = queryset.order_by(tri)
        return queryset

    def peut_ouvrir(self):
        permission = self.permission_ouverture
        if permission is None:
            meta = self.model._meta
            permission = f"{meta.app_label}.change_{meta.model_name}"
        return self.request.user.has_perm(permission)

    def get(self, request, *args, **kwargs):
        if request.GET.get("export") == "xlsx":
            return self.exporter_excel()
        return super().get(request, *args, **kwargs)

    def exporter_excel(self):
        queryset = self.get_queryset()[:LIMITE_EXPORT]
        classeur = Workbook()
        feuille = classeur.active
        feuille.title = (self.titre or "Export")[:31]
        feuille.append([c[1] for c in self.colonnes])
        for cellule in feuille[1]:
            cellule.font = Font(bold=True)
        nombre = 0
        for objet in queryset:
            feuille.append([_cellule_excel(valeur_attribut(objet, c[0])) for c in self.colonnes])
            nombre += 1
        tampon = BytesIO()
        classeur.save(tampon)
        journaliser(self.request, "export", f"Export Excel « {self.titre} » ({nombre} lignes)")
        nom = f"{self.titre or 'export'}-{timezone.localdate():%Y%m%d}.xlsx".replace(" ", "_")
        reponse = HttpResponse(
            tampon.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        reponse["Content-Disposition"] = f'attachment; filename="{nom}"'
        return reponse

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        parametres = self.request.GET.copy()
        parametres.pop("page", None)
        parametres_sans_tri = parametres.copy()
        parametres_sans_tri.pop("tri", None)
        tri_courant = self.request.GET.get("tri") or self.tri_defaut or ""
        contexte.update(
            titre=self.titre,
            entetes=[
                {
                    "libelle": c[1],
                    "tri": c[2],
                    "actif": tri_courant.lstrip("-") == c[2] if c[2] else False,
                    "descendant": tri_courant.startswith("-"),
                }
                for c in self.colonnes
            ],
            lignes=[
                (o, [(c[1], valeur_attribut(o, c[0])) for c in self.colonnes]) for o in contexte["object_list"]
            ],
            peut_ouvrir=self.peut_ouvrir(),
            filtres=[(f, self.request.GET.get(f.parametre, "")) for f in self.filtres],
            recherche=self.request.GET.get("q", ""),
            avec_recherche=bool(self.champs_recherche),
            parametres=parametres.urlencode(),
            parametres_sans_tri=parametres_sans_tri.urlencode(),
            url_creation=self.url_creation
            if not self.permission_creation or self.request.user.has_perm(self.permission_creation)
            else None,
        )
        return contexte


def _cellule_excel(valeur):
    if isinstance(valeur, (int, float, str)) or valeur is None:
        return valeur
    if hasattr(valeur, "tzinfo") and valeur.tzinfo is not None:
        return timezone.localtime(valeur).replace(tzinfo=None)
    return str(valeur)


class EnregistrementMixin:
    """Création / modification passant par ``services.enregistrer``.

    Le formulaire porte la version affichée ; une modification concurrente
    est refusée avec un message clair au lieu d'écraser l'autre saisie.
    """

    template_name = "composants/formulaire.html"
    titre = ""
    url_retour = None
    message_succes = "Enregistrement effectué."

    def form_valid(self, form):
        instance = form.save(commit=False)
        try:
            services.enregistrer(instance, self.request.user, self.request.POST.get("version_formulaire"))
        except ValidationError as erreur:
            if hasattr(erreur, "error_dict"):
                for champ, liste in erreur.error_dict.items():
                    form.add_error(champ if champ in form.fields else None, liste)
            else:
                form.add_error(None, erreur)
            return self.form_invalid(form)
        form.save_m2m()
        self.object = instance
        messages.success(self.request, self.message_succes)
        return self.redirection()

    def redirection(self):
        from django.shortcuts import redirect

        return redirect(self.url_retour)

    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte.update(titre=self.titre, url_retour=self.url_retour)
        return contexte


class CreationView(PermissionRequiseMixin, EnregistrementMixin, CreateView):
    pass


class ModificationView(PermissionRequiseMixin, EnregistrementMixin, UpdateView):
    def get_context_data(self, **kwargs):
        contexte = super().get_context_data(**kwargs)
        contexte["version_formulaire"] = self.request.POST.get("version_formulaire", self.object.version)
        return contexte
