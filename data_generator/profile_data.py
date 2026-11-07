"""
profile_data.py — Étape 2 NeoRetail
Profil complet de toutes les sources : lignes, types, nulls, cardinalités, PK, FK orphelines.
Génère docs/profil.md.

Usage :
    python3 data_generator/profile_data.py --source . --out docs/profil.md
"""

import argparse
import duckdb
import os
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration : tous les fichiers à profiler
# ---------------------------------------------------------------------------

# Chaque entrée décrit un fichier source
SOURCES = [
    {
        "nom":    "customers",
        "chemin": "raw/customers/customers.csv.gz",
        "format": "csv",
        "pk":     "customer_id",
        # Colonnes catégorielles dont on veut les valeurs distinctes
        "cat":    ["region", "segment", "is_active"],
        # Colonnes de date pour min/max
        "dates":  ["signup_date"],
    },
    {
        "nom":    "products",
        "chemin": "raw/products/products.csv.gz",
        "format": "csv",
        "pk":     "product_id",
        "cat":    ["category", "subcategory", "brand", "is_active", "is_current"],
        "dates":  ["effective_from", "effective_to"],
    },
    {
        "nom":    "stores",
        "chemin": "raw/stores/stores.csv.gz",
        "format": "csv",
        "pk":     "store_id",
        "cat":    ["city", "format", "is_active"],
        "dates":  [],
    },
    {
        "nom":    "orders",
        "chemin": "raw/orders/orders.csv.gz",
        "format": "csv",
        "pk":     "order_id",
        "cat":    ["channel", "payment_method", "status"],
        "dates":  ["order_ts"],
        # FK : colonne locale → (fichier parent, colonne parent)
        "fk":     [("customer_id", "raw/orders/orders.csv.gz",      "customer_id",
                                   "raw/customers/customers.csv.gz", "customer_id")],
    },
    {
        "nom":    "order_items",
        "chemin": "raw/orders/order_items.csv.gz",
        "format": "csv",
        "pk":     "order_item_id",
        "cat":    [],
        "dates":  [],
        "fk":     [
            ("order_id",   "raw/orders/order_items.csv.gz", "order_id",
                           "raw/orders/orders.csv.gz",      "order_id"),
            ("product_id", "raw/orders/order_items.csv.gz", "product_id",
                           "raw/products/products.csv.gz",  "product_id"),
        ],
    },
    {
        "nom":    "pos_sales",
        "chemin": "raw/pos/pos_sales.csv.gz",
        "format": "csv",
        "pk":     "sale_id",
        "cat":    [],
        "dates":  ["sale_ts"],
        "fk":     [
            ("store_id",    "raw/pos/pos_sales.csv.gz", "store_id",
                            "raw/stores/stores.csv.gz", "store_id"),
            ("product_id",  "raw/pos/pos_sales.csv.gz", "product_id",
                            "raw/products/products.csv.gz", "product_id"),
            ("customer_id", "raw/pos/pos_sales.csv.gz", "customer_id",
                            "raw/customers/customers.csv.gz", "customer_id"),
        ],
    },
    {
        "nom":    "returns",
        "chemin": "raw/returns/returns.csv.gz",
        "format": "csv",
        "pk":     "return_id",
        "cat":    ["reason"],
        "dates":  ["return_ts"],
        "fk":     [
            ("order_id",   "raw/returns/returns.csv.gz", "order_id",
                           "raw/orders/orders.csv.gz",   "order_id"),
            ("product_id", "raw/returns/returns.csv.gz", "product_id",
                           "raw/products/products.csv.gz", "product_id"),
        ],
    },
    {
        "nom":    "gl_entries",
        "chemin": "raw/erp/gl_entries.csv.gz",
        "format": "csv",
        "pk":     "entry_id",
        "cat":    ["document_type", "currency"],
        "dates":  ["posting_date"],
    },
    {
        "nom":    "clickstream",
        "chemin": "stream/clickstream.jsonl.gz",
        "format": "jsonl",
        "pk":     "event_id",
        "cat":    ["event_type", "device", "source"],
        "dates":  ["event_ts"],
    },
    {
        "nom":    "customer_updates",
        "chemin": "cdc/customer_updates.jsonl.gz",
        "format": "jsonl",
        "pk":     None,  # pas de PK sur les CDC
        "cat":    ["op", "new_region", "new_segment"],
        "dates":  ["change_ts"],
    },
]


# ---------------------------------------------------------------------------
# Fonctions utilitaires DuckDB
# ---------------------------------------------------------------------------

def table_ref(chemin: str, format: str) -> str:
    """Retourne la clause FROM DuckDB adaptée au format du fichier."""
    if format == "csv":
        return f"read_csv_auto('{chemin}', compression='gzip')"
    elif format == "jsonl":
        return f"read_json('{chemin}', format='newline_delimited', compression='gzip')"
    raise ValueError(f"Format inconnu : {format}")


def compter_lignes(con, ref: str) -> int:
    return con.execute(f"SELECT COUNT(*) FROM {ref}").fetchone()[0]


def obtenir_schema(con, ref: str) -> list[tuple]:
    """Retourne la liste (colonne, type) du fichier."""
    rows = con.execute(f"DESCRIBE SELECT * FROM {ref}").fetchall()
    # DESCRIBE retourne : column_name, column_type, null, key, default, extra
    return [(r[0], r[1]) for r in rows]


def profil_nulls(con, ref: str, colonnes: list[str]) -> dict:
    """
    Calcule le % de nulls pour chaque colonne.
    On construit une seule requête pour ne lire le fichier qu'une fois.
    """
    nb_total = compter_lignes(con, ref)
    if nb_total == 0:
        return {col: 0.0 for col in colonnes}

    # Construction dynamique : COUNT des non-null pour chaque colonne
    exprs = ", ".join(
        f"ROUND(100.0 * SUM(CASE WHEN \"{col}\" IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS \"{col}\""
        for col in colonnes
    )
    row = con.execute(f"SELECT {exprs} FROM {ref}").fetchone()
    return dict(zip(colonnes, row))


def exemple_valeur(con, ref: str, col: str) -> str:
    """Retourne la première valeur non-nulle d'une colonne."""
    row = con.execute(
        f"SELECT \"{col}\" FROM {ref} WHERE \"{col}\" IS NOT NULL LIMIT 1"
    ).fetchone()
    return str(row[0]) if row else "N/A"


def valeurs_distinctes(con, ref: str, col: str, max_vals: int = 20) -> list:
    """Retourne les valeurs distinctes d'une colonne catégorielle (triées)."""
    rows = con.execute(
        f"SELECT DISTINCT \"{col}\" FROM {ref} ORDER BY \"{col}\" LIMIT {max_vals}"
    ).fetchall()
    return [str(r[0]) for r in rows]


def date_min_max(con, ref: str, col: str) -> tuple:
    """Retourne (min, max) d'une colonne de date/timestamp."""
    row = con.execute(
        f"SELECT MIN(\"{col}\"), MAX(\"{col}\") FROM {ref}"
    ).fetchone()
    return (str(row[0]), str(row[1]))


def verifier_pk(con, ref: str, pk: str) -> dict:
    """
    Vérifie l'unicité de la clé primaire.
    Retourne : {"total": n, "doublons": k}
    """
    total = compter_lignes(con, ref)
    distincts = con.execute(
        f"SELECT COUNT(DISTINCT \"{pk}\") FROM {ref}"
    ).fetchone()[0]
    return {"total": total, "distincts": distincts, "doublons": total - distincts}


def verifier_fk(con, source_dir: str, fk_def: tuple) -> dict:
    """
    Vérifie les FK orphelines.
    fk_def = (col_enfant, chemin_enfant, col_enfant2,
               chemin_parent, col_parent)
    Retourne : {"orphelins": n, "total": n}
    """
    col_enfant, chemin_enfant, _, chemin_parent, col_parent = fk_def
    fmt_enfant = "jsonl" if chemin_enfant.endswith(".jsonl.gz") else "csv"
    fmt_parent = "jsonl" if chemin_parent.endswith(".jsonl.gz") else "csv"

    ref_e = table_ref(os.path.join(source_dir, chemin_enfant), fmt_enfant)
    ref_p = table_ref(os.path.join(source_dir, chemin_parent), fmt_parent)

    total = compter_lignes(con, ref_e)

    # Orphelin = une valeur de la table enfant qui n'existe pas dans le parent
    orphelins = con.execute(f"""
        SELECT COUNT(*) FROM {ref_e} e
        WHERE e."{col_enfant}" IS NOT NULL
          AND e."{col_enfant}" NOT IN (
              SELECT DISTINCT "{col_parent}" FROM {ref_p}
          )
    """).fetchone()[0]

    return {"col": col_enfant, "orphelins": orphelins, "total": total}


# ---------------------------------------------------------------------------
# Génération du rapport Markdown
# ---------------------------------------------------------------------------

def profiler_source(con, source_dir: str, src: dict) -> str:
    """Profil complet d'un fichier source. Retourne un bloc Markdown."""
    chemin_abs = os.path.join(source_dir, src["chemin"])
    ref = table_ref(chemin_abs, src["format"])

    lignes = []
    lignes.append(f"\n## {src['nom']}\n")
    lignes.append(f"**Fichier :** `{src['chemin']}`\n")

    # --- Nombre de lignes ---
    nb = compter_lignes(con, ref)
    lignes.append(f"**Lignes :** {nb:,}\n")

    # --- Schéma : colonnes et types ---
    schema = obtenir_schema(con, ref)
    colonnes = [col for col, _ in schema]

    lignes.append("\n### Colonnes et types\n")
    lignes.append("| Colonne | Type DuckDB | Exemple | % Null |")
    lignes.append("|---|---|---|---|")

    nulls = profil_nulls(con, ref, colonnes)

    for col, typ in schema:
        ex = exemple_valeur(con, ref, col)
        pct = nulls.get(col, 0.0)
        lignes.append(f"| {col} | {typ} | {ex} | {pct}% |")

    # --- Dates min/max ---
    if src.get("dates"):
        lignes.append("\n### Plage temporelle\n")
        for col in src["dates"]:
            mn, mx = date_min_max(con, ref, col)
            lignes.append(f"- **{col}** : {mn} → {mx}")

    # --- Valeurs distinctes ---
    if src.get("cat"):
        lignes.append("\n### Valeurs distinctes (colonnes catégorielles)\n")
        for col in src["cat"]:
            vals = valeurs_distinctes(con, ref, col)
            lignes.append(f"- **{col}** ({len(vals)}) : {', '.join(vals)}")

    # --- Unicité PK ---
    if src.get("pk"):
        lignes.append("\n### Clé primaire\n")
        pk_res = verifier_pk(con, ref, src["pk"])
        statut = "✅ unique" if pk_res["doublons"] == 0 else f"⚠️ {pk_res['doublons']:,} doublons"
        lignes.append(f"- **{src['pk']}** : {pk_res['total']:,} lignes, {statut}")

    # --- FK orphelines ---
    if src.get("fk"):
        lignes.append("\n### Clés étrangères\n")
        for fk_def in src["fk"]:
            res = verifier_fk(con, source_dir, fk_def)
            statut = "✅ 0 orphelin" if res["orphelins"] == 0 \
                else f"⚠️ {res['orphelins']:,} orphelins sur {res['total']:,}"
            lignes.append(f"- **{res['col']}** → {statut}")

    return "\n".join(lignes)


def collecter_anomalies(con, source_dir: str) -> list[str]:
    """Regroupe toutes les anomalies détectées pour la section finale."""
    anomalies = []

    for src in SOURCES:
        chemin_abs = os.path.join(source_dir, src["chemin"])
        ref = table_ref(chemin_abs, src["format"])

        # Nulls sur colonnes importantes (seuil : > 0%)
        colonnes = [col for col, _ in obtenir_schema(con, ref)]
        nulls = profil_nulls(con, ref, colonnes)
        for col, pct in nulls.items():
            if pct > 0:
                anomalies.append(
                    f"- `{src['nom']}.{col}` : {pct}% de valeurs nulles"
                )

        # Doublons PK
        if src.get("pk"):
            pk_res = verifier_pk(con, ref, src["pk"])
            if pk_res["doublons"] > 0:
                anomalies.append(
                    f"- `{src['nom']}.{src['pk']}` : {pk_res['doublons']:,} doublons de clé primaire"
                )

        # FK orphelines
        for fk_def in src.get("fk", []):
            res = verifier_fk(con, source_dir, fk_def)
            if res["orphelins"] > 0:
                anomalies.append(
                    f"- `{src['nom']}.{res['col']}` : {res['orphelins']:,} FK orphelines"
                )

    return anomalies


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Profilage des données NeoRetail")
    parser.add_argument("--source", default=".", help="Dossier racine des données source")
    parser.add_argument("--out", default="docs/profil.md", help="Fichier Markdown de sortie")
    args = parser.parse_args()

    source_dir = args.source
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Profilage en cours depuis : {source_dir}")
    print(f"Sortie : {out_path}\n")

    # Une seule connexion DuckDB pour toute l'exécution (plus efficace)
    con = duckdb.connect()

    blocs = []

    # En-tête du rapport
    blocs.append(f"# Rapport de profilage — NeoRetail")
    blocs.append(f"Généré le {datetime.now().strftime('%Y-%m-%d %H:%M')} par `profile_data.py`\n")
    blocs.append("---")

    # Profil de chaque source
    for src in SOURCES:
        chemin_abs = os.path.join(source_dir, src["chemin"])
        print(f"  → {src['nom']} ({src['chemin']})")
        bloc = profiler_source(con, source_dir, src)
        blocs.append(bloc)
        blocs.append("\n---")

    # Section anomalies finale
    print("\nCollecte des anomalies...")
    blocs.append("\n## Anomalies détectées\n")
    blocs.append("_Cette liste servira de base pour les règles Great Expectations en S4._\n")
    anomalies = collecter_anomalies(con, source_dir)
    if anomalies:
        blocs.extend(anomalies)
    else:
        blocs.append("Aucune anomalie détectée.")

    con.close()

    # Écriture du fichier Markdown
    out_path.write_text("\n".join(blocs), encoding="utf-8")
    print(f"\nRapport écrit dans {out_path} ({out_path.stat().st_size // 1024} Ko)")


if __name__ == "__main__":
    main()
