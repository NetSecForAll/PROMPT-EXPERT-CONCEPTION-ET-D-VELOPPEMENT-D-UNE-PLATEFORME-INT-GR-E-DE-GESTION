#!/usr/bin/env bash
# Sauvegarde de la base PostgreSQL et des fichiers de la plateforme.
#
# Variables lues (fichier .env ou environnement) :
#   POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_PORT
#   MEDIA_ROOT            dossier des fichiers documentaires (défaut : ./fichiers)
#   SAUVEGARDE_DIR        dossier de destination (défaut : ./sauvegardes)
#   SAUVEGARDE_CLE        fichier contenant la phrase de chiffrement (facultatif mais
#                         fortement recommandé dès qu'une copie quitte le serveur)
#   SAUVEGARDE_JOURS      nombre de sauvegardes quotidiennes conservées (défaut : 30)
#
# Planification conseillée (crontab de l'utilisateur système) :
#   30 1 * * * /chemin/plateforme/deploiement/scripts/sauvegarde.sh >> /var/log/plateforme-sauvegarde.log 2>&1
set -euo pipefail

RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
# Lit .env sans l'exécuter ; une variable déjà définie dans l'environnement est prioritaire.
if [ -f "$RACINE/.env" ]; then
  while IFS='=' read -r cle valeur; do
    valeur="${valeur%%[[:space:]]#*}"
    [ -z "${!cle:-}" ] && export "$cle=$valeur"
  done < <(grep -E '^[A-Z_]+=' "$RACINE/.env")
fi

: "${POSTGRES_DB:?POSTGRES_DB manquant}" "${POSTGRES_USER:?}" "${POSTGRES_PASSWORD:?}"
export PGHOST="${POSTGRES_HOST:-localhost}" PGPORT="${POSTGRES_PORT:-5432}" PGPASSWORD="$POSTGRES_PASSWORD"
MEDIA_ROOT="${MEDIA_ROOT:-$RACINE/fichiers}"
DESTINATION="${SAUVEGARDE_DIR:-$RACINE/sauvegardes}"
JOURS="${SAUVEGARDE_JOURS:-30}"
HORODATAGE="$(date +%Y%m%d-%H%M%S)"
DOSSIER="$DESTINATION/$HORODATAGE"
mkdir -p "$DOSSIER"
chmod 700 "$DESTINATION" "$DOSSIER"

echo "[$(date -Is)] Sauvegarde de la base $POSTGRES_DB"
pg_dump --format=custom --compress=6 --no-owner --file="$DOSSIER/base.dump" "$POSTGRES_DB" --username="$POSTGRES_USER"

echo "[$(date -Is)] Sauvegarde des fichiers ($MEDIA_ROOT)"
mkdir -p "$MEDIA_ROOT"
tar -czf "$DOSSIER/fichiers.tar.gz" -C "$MEDIA_ROOT" .

# Inventaire pour le contrôle après restauration.
psql --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --tuples-only --no-align --command="
  SELECT table_name, (xpath('/row/n/text()', query_to_xml('SELECT count(*) AS n FROM ' || quote_ident(table_name), false, true, '')))[1]::text
  FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name" \
  > "$DOSSIER/inventaire.txt"

if [ -n "${SAUVEGARDE_CLE:-}" ]; then
  for f in base.dump fichiers.tar.gz; do
    openssl enc -aes-256-cbc -pbkdf2 -salt -pass "file:$SAUVEGARDE_CLE" -in "$DOSSIER/$f" -out "$DOSSIER/$f.chiffre"
    rm "$DOSSIER/$f"
  done
fi
(cd "$DOSSIER" && sha256sum ./* > SHA256SUMS)

echo "[$(date -Is)] Suppression des sauvegardes au-delà des $JOURS plus récentes"
ls -1d "$DESTINATION"/[0-9]*-[0-9]* 2>/dev/null | sort -r | tail -n +$((JOURS + 1)) | xargs -r rm -rf

echo "[$(date -Is)] Terminé : $DOSSIER"
