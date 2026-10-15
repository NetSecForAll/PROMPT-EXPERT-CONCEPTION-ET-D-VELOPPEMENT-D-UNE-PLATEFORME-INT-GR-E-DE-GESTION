"""Le journal est en ajout seul : un déclencheur PostgreSQL refuse toute
modification ou suppression des événements de sécurité et de l'historique
des modifications (django-auditlog), quel que soit le chemin d'accès."""

from django.db import migrations

FONCTION = """
CREATE OR REPLACE FUNCTION journal_interdire_modification() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Le journal d''audit ne peut être ni modifié ni supprimé (table %).', TG_TABLE_NAME
        USING ERRCODE = 'insufficient_privilege';
END;
$$ LANGUAGE plpgsql;
"""

DECLENCHEUR = """
CREATE TRIGGER {table}_ajout_seul
BEFORE UPDATE OR DELETE ON {table}
FOR EACH ROW EXECUTE FUNCTION journal_interdire_modification();
"""

TABLES = ["journal_evenementsecurite", "auditlog_logentry"]


class Migration(migrations.Migration):
    dependencies = [
        ("journal", "0002_initial"),
        ("auditlog", "0017_add_actor_email"),
    ]

    operations = [
        migrations.RunSQL(FONCTION, "DROP FUNCTION IF EXISTS journal_interdire_modification();"),
    ] + [
        migrations.RunSQL(DECLENCHEUR.format(table=t), f"DROP TRIGGER IF EXISTS {t}_ajout_seul ON {t};")
        for t in TABLES
    ]
