// Confirmation des actions sensibles : tout formulaire portant
// data-confirmation demande un accord explicite avant envoi.
document.addEventListener("submit", function (evenement) {
  var formulaire = evenement.target;
  var bouton = evenement.submitter;
  var message = (bouton && bouton.dataset.confirmation) || formulaire.dataset.confirmation;
  if (message && !window.confirm(message)) {
    evenement.preventDefault();
  }
});
// Jeton CSRF pour les requêtes HTMX.
document.addEventListener("htmx:configRequest", function (evenement) {
  var jeton = document.querySelector("input[name=csrfmiddlewaretoken]");
  if (jeton) { evenement.detail.headers["X-CSRFToken"] = jeton.value; }
});
