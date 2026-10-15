#!/usr/bin/env bash
# Restauration d'une sauvegarde produite par sauvegarde.sh.
#
# Usage : restauration.sh <dossier_de_sauvegarde> [base_cible] --oui
#   La base cible (défaut : POSTGRES_DB) est entièrement remplacée.
#   Le dossier des fichiers (MEDIA_ROOT) est remplacé par celui de la sauvegarde.
# Après restauration, le script compare le nombre de lignes de chaque table à
# l'inventaire enregistré lors de la sauvegarde.
set -euo pipefail

RACINE="$(cd "$(dirname "$0")/../.." && pwd)"
# Lit .env sans l'exécuter ; une variable déjà définie dans l'environnement est prioritaire.
if [ -f "$RACINE/.env" ]; then
  while IFS='=' read -r cle valeur; do
    valeur="${valeur%%[[:space:]]#*}"
    [ -z "${!cle:-}" ] && export "$cle=$valeur"
  done < <(grep -E '^[A-Z_]+=' "$RACINE/.env")
fi

CONFIRME=non
POSITIONNELS=()
for argument in "$@"; do
  if [ "$argument" = "--oui" ]; then CONFIRME=oui; else POSITIONNELS+=("$argument"); fi
done
SOURCE="${POSITIONNELS[0]:?Indiquez le dossier de sauvegarde}"
CIBLE="${POSITIONNELS[1]:-$POSTGRES_DB}"
if [ "$CONFIRME" != oui ]; then
  echo "La base « $CIBLE » et le dossier des fichiers seront remplacés. Relancez avec --oui pour confirmer." >&2
  exit 1
fi

export PGHOST="${POSTGRES_HOST:-localhost}" PGPORT="${POSTGRES_PORT:-5432}" PGPASSWORD="$POSTGRES_PASSWORD"
MEDIA_ROOT="${MEDIA_ROOT:-$RACINE/fichiers}"
TRAVAIL="$(mktemp -d)"
trap 'rm -rf "$TRAVAIL"' EXIT

echo "[$(date -Is)] Contrôle d'intégrité de la sauvegarde"
(cd "$SOURCE" && sha256sum --check --quiet SHA256SUMS)

for f in base.dump fichiers.tar.gz; do
  if [ -f "$SOURCE/$f.chiffre" ]; then
    : "${SAUVEGARDE_CLE:?Sauvegarde chiffrée : SAUVEGARDE_CLE requis}"
    openssl enc -d -aes-256-cbc -pbkdf2 -pass "file:$SAUVEGARDE_CLE" -in "$SOURCE/$f.chiffre" -out "$TRAVAIL/$f"
  else
    cp "$SOURCE/$f" "$TRAVAIL/$f"
  fi
done

echo "[$(date -Is)] Recréation de la base $CIBLE"
psql --username="$POSTGRES_USER" --dbname=postgres --quiet --command="DROP DATABASE IF EXISTS \"$CIBLE\" WITH (FORCE);"
psql --username="$POSTGRES_USER" --dbname=postgres --quiet --command="CREATE DATABASE \"$CIBLE\";"
pg_restore --username="$POSTGRES_USER" --dbname="$CIBLE" --no-owner --exit-on-error "$TRAVAIL/base.dump"

echo "[$(date -Is)] Restauration des fichiers dans $MEDIA_ROOT"
mkdir -p "$MEDIA_ROOT"
find "$MEDIA_ROOT" -mindepth 1 -delete
tar -xzf "$TRAVAIL/fichiers.tar.gz" -C "$MEDIA_ROOT"

echo "[$(date -Is)] Comparaison avec l'inventaire de la sauvegarde"
psql --username="$POSTGRES_USER" --dbname="$CIBLE" --tuples-only --no-align --command="
  SELECT table_name, (xpath('/row/n/text()', query_to_xml('SELECT count(*) AS n FROM ' || quote_ident(table_name), false, true, '')))[1]::text
  FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name" \
  > "$TRAVAIL/inventaire.txt"
if diff -q "$SOURCE/inventaire.txt" "$TRAVAIL/inventaire.txt" > /dev/null; then
  echo "[$(date -Is)] Restauration réussie : $(wc -l < "$TRAVAIL/inventaire.txt") tables, effectifs identiques."
else
  echo "ÉCHEC : les effectifs diffèrent de l'inventaire de la sauvegarde :" >&2
  diff "$SOURCE/inventaire.txt" "$TRAVAIL/inventaire.txt" >&2 || true
  exit 2
fi
