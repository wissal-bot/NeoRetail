"""
test_stock.py — Tests du générateur de stock.
"""

import shutil
from pathlib import Path

import pandas as pd
import pytest


OUT_DIR_STOCK = "data/raw_test_stock"
FICHIER_STOCK = Path(OUT_DIR_STOCK) / "stock_snapshots.csv.gz"


@pytest.fixture(scope="module", autouse=True)
def generer_stock():
    """Génère le stock une fois pour tous les tests du module, puis nettoie."""
    if Path(OUT_DIR_STOCK).exists():
        shutil.rmtree(OUT_DIR_STOCK)

    from data_generator.generate_stock import charger_ventes_quotidiennes, simuler_stock

    pivot, dates, paires_keys = charger_ventes_quotidiennes(".")
    df_stock = simuler_stock(pivot, dates, paires_keys)

    Path(OUT_DIR_STOCK).mkdir(parents=True, exist_ok=True)
    df_stock.to_csv(FICHIER_STOCK, index=False, compression="gzip")

    yield df_stock

    if Path(OUT_DIR_STOCK).exists():
        shutil.rmtree(OUT_DIR_STOCK)


# ---------------------------------------------------------------------------
# Test 1 : le stock n'est jamais négatif
# ---------------------------------------------------------------------------

def test_stock_jamais_negatif(generer_stock):
    """qty_on_hand doit être >= 0 sur toute la période."""
    df = generer_stock
    nb_negatifs = (df["qty_on_hand"] < 0).sum()
    assert nb_negatifs == 0, f"{nb_negatifs} lignes avec stock négatif"


# ---------------------------------------------------------------------------
# Test 2 : reproductibilité avec le même seed
# ---------------------------------------------------------------------------

def test_reproductibilite():
    """Deux exécutions avec le même seed doivent produire exactement le même résultat."""
    from data_generator.generate_stock import charger_ventes_quotidiennes, simuler_stock

    pivot, dates, paires = charger_ventes_quotidiennes(".")
    df1 = simuler_stock(pivot, dates, paires)
    df2 = simuler_stock(pivot, dates, paires)

    assert df1.equals(df2), "Le générateur n'est pas reproductible (seed non fixe ?)"


# ---------------------------------------------------------------------------
# Test 3 : colonnes attendues et types
# ---------------------------------------------------------------------------

def test_colonnes_stock(generer_stock):
    """Le fichier stock doit contenir les 4 colonnes attendues."""
    df = generer_stock
    for col in ["snapshot_date", "store_id", "product_id", "qty_on_hand"]:
        assert col in df.columns, f"Colonne manquante dans le stock : {col}"


# ---------------------------------------------------------------------------
# Test 4 : cohérence du nombre de paires par jour
# ---------------------------------------------------------------------------

def test_nb_paires_constant_par_jour(generer_stock):
    """Chaque jour doit avoir le même nombre de paires (toutes les paires à chaque snapshot)."""
    df = generer_stock
    nb_par_jour = df.groupby("snapshot_date")["store_id"].count()
    assert nb_par_jour.nunique() == 1, (
        "Le nombre de paires varie selon les jours — toutes les paires doivent apparaître chaque jour"
    )
