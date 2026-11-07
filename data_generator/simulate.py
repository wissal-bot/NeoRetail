"""
simulate.py — Étape 4 NeoRetail
Simule l'arrivée des données jour par jour depuis les sources brutes.
Écrit dans data/raw/<source>/dt=YYYY-MM-DD/data.csv.gz (ou .parquet).

Idempotent : relancer le même jour écrase proprement la partition sans doublon.

Usages :
    python3 data_generator/simulate.py --day 2025-06-15
    python3 data_generator/simulate.py --from 2025-01-01 --to 2025-01-31
    python3 data_generator/simulate.py --day 2025-06-15 --format parquet
    python3 data_generator/simulate.py --replay-clickstream --speed 10
"""

import argparse
import shutil
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pandas as pd

from data_generator.common import table_ref, replay_clickstream

# ---------------------------------------------------------------------------
# Configuration des sources transactionnelles (filtrées par date)
# ---------------------------------------------------------------------------

SOURCES = [
    {"nom": "orders",           "chemin": "raw/orders/orders.csv.gz",      "fmt": "csv",   "col_date": "order_ts"},
    {"nom": "pos_sales",        "chemin": "raw/pos/pos_sales.csv.gz",       "fmt": "csv",   "col_date": "sale_ts"},
    {"nom": "returns",          "chemin": "raw/returns/returns.csv.gz",      "fmt": "csv",   "col_date": "return_ts"},
    {"nom": "gl_entries",       "chemin": "raw/erp/gl_entries.csv.gz",      "fmt": "csv",   "col_date": "posting_date"},
    {"nom": "customer_updates", "chemin": "cdc/customer_updates.jsonl.gz",   "fmt": "jsonl", "col_date": "change_ts"},
]

# Référentiels copiés en snapshot complet (pas de filtre par date)
REFERENTIELS = [
    {"nom": "customers", "chemin": "raw/customers/customers.csv.gz"},
    {"nom": "products",  "chemin": "raw/products/products.csv.gz"},
    {"nom": "stores",    "chemin": "raw/stores/stores.csv.gz"},
]

# Colonnes originales d'order_items (la colonne de date vient de orders, on ne l'écrit pas)
COLS_ORDER_ITEMS = ["order_item_id", "order_id", "product_id", "qty", "unit_price", "discount_rate", "net_amount"]


# ---------------------------------------------------------------------------
# Écriture d'une partition Hive-style : data/raw/<source>/dt=YYYY-MM-DD/
# ---------------------------------------------------------------------------

def ecrire_partition(df: pd.DataFrame, out_dir: str, source_name: str, day, fmt: str):
    """
    Écrit df dans data/raw/<source>/dt=<day>/.
    Idempotent : supprime le dossier existant avant d'écrire.
    """
    partition_dir = Path(out_dir) / source_name / f"dt={day}"

    # Supprime la partition existante → garantit l'idempotence
    if partition_dir.exists():
        shutil.rmtree(partition_dir)
    partition_dir.mkdir(parents=True)

    if fmt == "parquet":
        df.to_parquet(partition_dir / "data.parquet", index=False)
    else:
        df.to_csv(partition_dir / "data.csv.gz", index=False, compression="gzip")


def ecrire_toutes_partitions(df: pd.DataFrame, col_date: str, out_dir: str,
                              source_name: str, fmt: str, cols_finales=None):
    """
    Éclate df par date et écrit une partition par jour.
    Utilisé pour traiter un fichier source en une seule lecture (plage de dates).
    """
    df = df.copy()
    # Extraction de la date (gère timestamps et dates)
    df["_part"] = pd.to_datetime(df[col_date]).dt.date

    for day, grp in df.groupby("_part"):
        grp_clean = grp.drop(columns=["_part"])
        if cols_finales:
            grp_clean = grp_clean[cols_finales]
        ecrire_partition(grp_clean, out_dir, source_name, day, fmt)


# ---------------------------------------------------------------------------
# Lecture des sources avec DuckDB
# ---------------------------------------------------------------------------

def lire_source(con, chemin: str, fmt: str, col_date: str,
                from_date=None, to_date=None) -> pd.DataFrame:
    """Lit une source filtrée par plage de dates."""
    ref = table_ref(chemin, fmt)
    if from_date and to_date:
        where = f"WHERE CAST(\"{col_date}\" AS DATE) BETWEEN '{from_date}' AND '{to_date}'"
    elif from_date:
        where = f"WHERE CAST(\"{col_date}\" AS DATE) = '{from_date}'"
    else:
        where = ""
    return con.execute(f"SELECT * FROM {ref} {where}").df()


def lire_order_items(con, source_dir: str, from_date=None, to_date=None) -> pd.DataFrame:
    """
    Cas spécial : order_items n'a pas de date propre.
    On joint avec orders pour récupérer order_ts, puis on partitionne sur cette date.
    """
    ref_orders = table_ref(f"{source_dir}/raw/orders/orders.csv.gz",     "csv")
    ref_items  = table_ref(f"{source_dir}/raw/orders/order_items.csv.gz", "csv")

    if from_date and to_date:
        where = f"AND CAST(o.order_ts AS DATE) BETWEEN '{from_date}' AND '{to_date}'"
    elif from_date:
        where = f"AND CAST(o.order_ts AS DATE) = '{from_date}'"
    else:
        where = ""

    return con.execute(f"""
        SELECT oi.*, CAST(o.order_ts AS DATE) AS _order_date
        FROM {ref_items} oi
        JOIN {ref_orders} o ON oi.order_id = o.order_id
        WHERE 1=1 {where}
    """).df()


def lire_referentiel(con, chemin: str) -> pd.DataFrame:
    """Lit un référentiel complet (customers, products, stores)."""
    return con.execute(f"SELECT * FROM {table_ref(chemin, 'csv')}").df()


# ---------------------------------------------------------------------------
# Simulation pour une plage de dates
# ---------------------------------------------------------------------------

def simuler_plage(con, source_dir: str, out_dir: str, from_date: str, to_date: str, fmt: str):
    """
    Lit chaque fichier source UNE seule fois et écrit toutes les partitions de la plage.
    C'est la méthode performante pour plusieurs jours.
    """
    print(f"  Plage : {from_date} → {to_date}")

    # Sources transactionnelles
    for src in SOURCES:
        chemin = f"{source_dir}/{src['chemin']}"
        print(f"    {src['nom']}...")
        df = lire_source(con, chemin, src["fmt"], src["col_date"], from_date, to_date)
        ecrire_toutes_partitions(df, src["col_date"], out_dir, src["nom"], fmt)

    # Cas spécial : order_items (date via jointure avec orders)
    print("    order_items (via jointure orders)...")
    df_items = lire_order_items(con, source_dir, from_date, to_date)
    ecrire_toutes_partitions(df_items, "_order_date", out_dir, "order_items", fmt,
                              cols_finales=COLS_ORDER_ITEMS)

    # Référentiels : snapshot complet pour chaque jour de la plage
    print("    référentiels (snapshot complet par jour)...")
    d_debut = date.fromisoformat(from_date)
    d_fin   = date.fromisoformat(to_date)

    for ref in REFERENTIELS:
        df_ref = lire_referentiel(con, f"{source_dir}/{ref['chemin']}")
        d = d_debut
        while d <= d_fin:
            ecrire_partition(df_ref, out_dir, ref["nom"], d, fmt)
            d += timedelta(days=1)


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Simulateur de partitions journalières NeoRetail")
    parser.add_argument("--source",  default=".",        help="Dossier racine des données source")
    parser.add_argument("--out",     default="data/raw", help="Dossier de sortie")
    parser.add_argument("--format",  default="csv",      choices=["csv", "parquet"],
                        help="Format de sortie (défaut : csv)")

    groupe = parser.add_mutually_exclusive_group()
    groupe.add_argument("--day",  metavar="YYYY-MM-DD", help="Simule un seul jour")
    groupe.add_argument("--from", dest="from_date", metavar="YYYY-MM-DD", help="Début de plage")
    parser.add_argument("--to",   dest="to_date",   metavar="YYYY-MM-DD", help="Fin de plage")
    parser.add_argument("--replay-clickstream", action="store_true",
                        help="Rejoue le clickstream sur stdout (mode Kafka)")
    parser.add_argument("--speed", type=float, default=1.0,
                        help="Vitesse de rejeu clickstream (1=temps réel, 0=sans délai)")

    args = parser.parse_args()

    # Mode rejeu clickstream (pour le producer Kafka en S2)
    if args.replay_clickstream:
        print(f"Rejeu clickstream (speed={args.speed})...", flush=True)
        replay_clickstream(args.source, speed=args.speed)
        return

    # Détermine la plage de dates
    if args.day:
        from_date = to_date = args.day
    elif args.from_date and args.to_date:
        from_date, to_date = args.from_date, args.to_date
    else:
        parser.error("Spécifie --day OU --from + --to")

    print(f"Simulateur NeoRetail | source={args.source} | out={args.out} | format={args.format}")
    con = duckdb.connect()
    simuler_plage(con, args.source, args.out, from_date, to_date, args.format)
    con.close()
    print("Terminé.")


if __name__ == "__main__":
    main()
