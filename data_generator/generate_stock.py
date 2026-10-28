"""
generate_stock.py — Étape 5 NeoRetail
Génère un snapshot quotidien de stock (snapshot_date, store_id, product_id, qty_on_hand)
cohérent avec les ventes POS.

Logique :
- Limité aux paires magasin-produit avec >= 2 ventes (vendus régulièrement).
- Stock initial aléatoire entre 100 et 500 unités (seed fixe → reproductible).
- Chaque jour : stock = stock - ventes du jour.
- Réassort périodique tous les 7 jours (quantité aléatoire pré-générée, seed fixe).
- Réassort d'urgence quand le stock passe sous 10 unités (compteur séparé par paire).
- Le stock ne peut jamais être négatif (rupture = 0).

Usage :
    python3 data_generator/generate_stock.py --source . --out data/raw/stock
"""

import argparse
from datetime import timedelta
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd


SEED = 42
VENTES_MIN       = 2     # seuil minimum de ventes pour inclure une paire
STOCK_INIT_MIN   = 100
STOCK_INIT_MAX   = 500
RESTOCK_MIN      = 50
RESTOCK_MAX      = 200
RESTOCK_FREQ     = 7     # réassort périodique tous les N jours
SEUIL_ALERTE     = 10    # réassort d'urgence sous ce seuil
MAX_URGENCES     = 100   # pool de quantités d'urgence pré-générées par paire


def charger_ventes_quotidiennes(source_dir: str):
    """
    Agrège les ventes POS par (store_id, product_id, date).
    Retourne le pivot et la liste des paires retenues.
    """
    con = duckdb.connect()

    print("  Lecture et agrégation des ventes POS...")
    df_ventes = con.execute(f"""
        SELECT
            store_id,
            product_id,
            CAST(sale_ts AS DATE) AS sale_date,
            SUM(qty) AS qty_vendue
        FROM read_csv_auto('{source_dir}/raw/pos/pos_sales.csv.gz', compression='gzip')
        GROUP BY store_id, product_id, CAST(sale_ts AS DATE)
    """).df()

    print(f"  Filtrage des paires avec >= {VENTES_MIN} ventes au total...")
    paires_ok = con.execute(f"""
        SELECT store_id, product_id
        FROM read_csv_auto('{source_dir}/raw/pos/pos_sales.csv.gz', compression='gzip')
        GROUP BY store_id, product_id
        HAVING COUNT(*) >= {VENTES_MIN}
    """).df()
    con.close()

    # Filtre les ventes sur les paires valides
    paires_set = set(zip(paires_ok["store_id"], paires_ok["product_id"]))
    df_ventes["paire_key"] = df_ventes["store_id"] + "|" + df_ventes["product_id"]
    df_ventes = df_ventes[
        df_ventes.apply(lambda r: (r["store_id"], r["product_id"]) in paires_set, axis=1)
    ]
    paires_keys = sorted(df_ventes["paire_key"].unique())
    print(f"  {len(paires_keys)} paires retenues")

    # Plage de dates complète
    # On force datetime.date pour éviter les problèmes de type avec le reindex
    df_ventes["sale_date"] = pd.to_datetime(df_ventes["sale_date"]).dt.date
    date_min = df_ventes["sale_date"].min()
    date_max = df_ventes["sale_date"].max()
    toutes_dates = [date_min + timedelta(days=i)
                    for i in range((date_max - date_min).days + 1)]
    print(f"  Période : {date_min} → {date_max} ({len(toutes_dates)} jours)")

    # Pivot : index=date, colonnes=paire_key, valeurs=qty vendue (0 si pas de vente)
    pivot = (
        df_ventes
        .pivot_table(index="sale_date", columns="paire_key",
                     values="qty_vendue", aggfunc="sum")
        .reindex(index=toutes_dates, columns=paires_keys, fill_value=0)
        .fillna(0)
    )

    return pivot, toutes_dates, paires_keys


def simuler_stock(pivot: pd.DataFrame, dates: list, paires_keys: list) -> pd.DataFrame:
    """
    Simule l'évolution du stock jour par jour (vectorisé sur numpy).
    Retourne un DataFrame long (snapshot_date, store_id, product_id, qty_on_hand).
    """
    rng = np.random.default_rng(SEED)
    n_paires = len(paires_keys)
    n_jours  = len(dates)

    # Stock initial (100–500 par paire)
    stock = rng.integers(STOCK_INIT_MIN, STOCK_INIT_MAX + 1,
                         size=n_paires).astype(np.float64)

    # Quantités de réassort périodique : (nb_périodes × n_paires)
    nb_periods = n_jours // RESTOCK_FREQ + 2
    qtes_periodiques = rng.integers(RESTOCK_MIN, RESTOCK_MAX + 1,
                                    size=(nb_periods, n_paires)).astype(np.float64)

    # Quantités de réassort d'urgence : (n_paires × MAX_URGENCES)
    qtes_urgence = rng.integers(RESTOCK_MIN, RESTOCK_MAX + 1,
                                size=(n_paires, MAX_URGENCES)).astype(np.float64)
    # Compteur d'urgence indépendant par paire (séparé du compteur périodique)
    compteur_urgence = np.zeros(n_paires, dtype=np.int32)

    ventes = pivot.values  # shape : (n_jours, n_paires)
    snapshots = np.empty((n_jours, n_paires), dtype=np.int32)
    period_count = 0

    for i in range(n_jours):
        # Soustrait les ventes du jour
        stock -= ventes[i]

        # Réassort périodique tous les RESTOCK_FREQ jours (même quantité pour toutes les paires)
        if i % RESTOCK_FREQ == 0:
            stock += qtes_periodiques[period_count]
            period_count += 1

        # Réassort d'urgence (vectorisé) : paires dont le stock passe sous le seuil
        rupture = stock < SEUIL_ALERTE
        if rupture.any():
            # Indice sécurisé (évite dépassement si > MAX_URGENCES urgences)
            idx = np.minimum(compteur_urgence, MAX_URGENCES - 1)
            qte = qtes_urgence[np.arange(n_paires), idx]
            stock = np.where(rupture, stock + qte, stock)
            compteur_urgence += rupture.astype(np.int32)

        # Stock jamais négatif
        stock = np.maximum(stock, 0.0)
        snapshots[i] = stock.astype(np.int32)

    # Reconstruction en DataFrame long
    print("  Reconstruction du DataFrame final...")
    store_ids   = [k.split("|")[0] for k in paires_keys]
    product_ids = [k.split("|")[1] for k in paires_keys]

    blocs = [
        pd.DataFrame({
            "snapshot_date": day,
            "store_id":      store_ids,
            "product_id":    product_ids,
            "qty_on_hand":   snapshots[i],
        })
        for i, day in enumerate(dates)
    ]
    return pd.concat(blocs, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description="Générateur de stock NeoRetail")
    parser.add_argument("--source", default=".",              help="Dossier racine des données source")
    parser.add_argument("--out",    default="data/raw/stock", help="Dossier de sortie")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Génération du stock | source={args.source} | out={out_dir}")
    pivot, dates, paires_keys = charger_ventes_quotidiennes(args.source)
    df_stock = simuler_stock(pivot, dates, paires_keys)

    sortie = out_dir / "stock_snapshots.csv.gz"
    df_stock.to_csv(sortie, index=False, compression="gzip")

    nb_lignes  = len(df_stock)
    taille_ko  = sortie.stat().st_size // 1024
    nb_ruptures = (df_stock["qty_on_hand"] == 0).sum()
    print(f"Stock écrit : {nb_lignes:,} lignes → {sortie} ({taille_ko} Ko)")
    print(f"Stock min={df_stock['qty_on_hand'].min()}, max={df_stock['qty_on_hand'].max()}, "
          f"ruptures={nb_ruptures:,} ({100*nb_ruptures/nb_lignes:.1f}%)")


if __name__ == "__main__":
    main()
