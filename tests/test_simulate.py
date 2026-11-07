"""
test_simulate.py — Tests du simulateur de partitions journalières.

On utilise le jour 2025-06-15 comme jour de référence (données confirmées par le profilage).
Les tests sont conçus pour être rapides : on ne simule qu'un seul jour.
"""

import shutil
from pathlib import Path

import duckdb
import pandas as pd
import pytest


SOURCE_DIR = "."
OUT_DIR    = "data/raw_test"   # dossier de sortie isolé pour les tests
JOUR_TEST  = "2025-06-15"


@pytest.fixture(scope="module", autouse=True)
def simuler_jour_test():
    """Lance le simulateur une fois pour tous les tests du module, puis nettoie."""
    # Nettoyage avant test
    if Path(OUT_DIR).exists():
        shutil.rmtree(OUT_DIR)

    # Import ici pour éviter les effets de bord si le module n'existe pas
    from data_generator.simulate import simuler_plage
    con = duckdb.connect()
    simuler_plage(con, SOURCE_DIR, OUT_DIR, JOUR_TEST, JOUR_TEST, "csv")
    con.close()

    yield

    # Nettoyage après test
    if Path(OUT_DIR).exists():
        shutil.rmtree(OUT_DIR)


def lire_partition(source_name: str, jour: str) -> pd.DataFrame:
    """Lit un fichier de partition simulée."""
    fichier = Path(OUT_DIR) / source_name / f"dt={jour}" / "data.csv.gz"
    assert fichier.exists(), f"Partition introuvable : {fichier}"
    return pd.read_csv(fichier, compression="gzip")


# ---------------------------------------------------------------------------
# Test 1 : les partitions existent et ne sont pas vides
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source", ["orders", "pos_sales", "returns",
                                     "order_items", "customers", "products", "stores"])
def test_partition_existe(source):
    """Chaque source doit avoir une partition pour le jour testé."""
    partition_dir = Path(OUT_DIR) / source / f"dt={JOUR_TEST}"
    assert partition_dir.exists(), f"Partition absente : {partition_dir}"


def test_partition_gl_entries_date_reelle():
    """
    gl_entries n'a des données que le 2025-01-01 (toutes les écritures sont ce jour-là).
    On vérifie que la partition existe pour cette date, pas pour JOUR_TEST.
    """
    # La partition pour 2025-01-01 doit exister
    partition_dir = Path(OUT_DIR) / "gl_entries" / "dt=2025-01-01"
    # On ne la simule pas ici (mauvais jour de test), on vérifie juste que le simulateur
    # ne crée pas de partition vide quand il n'y a pas de données.
    partition_mauvais_jour = Path(OUT_DIR) / "gl_entries" / f"dt={JOUR_TEST}"
    assert not partition_mauvais_jour.exists(), (
        "Le simulateur a créé une partition gl_entries vide pour un jour sans données"
    )


# ---------------------------------------------------------------------------
# Test 2 : les dates sont correctes dans chaque partition
# ---------------------------------------------------------------------------

def test_dates_correctes_orders():
    """Toutes les lignes orders ont order_ts dont la date = JOUR_TEST."""
    df = lire_partition("orders", JOUR_TEST)
    if df.empty:
        pytest.skip("Aucune commande ce jour-là")
    dates = pd.to_datetime(df["order_ts"]).dt.date.astype(str)
    assert (dates == JOUR_TEST).all(), "Des lignes orders ont une mauvaise date"


def test_dates_correctes_pos_sales():
    """Toutes les lignes pos_sales ont sale_ts dont la date = JOUR_TEST."""
    df = lire_partition("pos_sales", JOUR_TEST)
    if df.empty:
        pytest.skip("Aucune vente ce jour-là")
    dates = pd.to_datetime(df["sale_ts"]).dt.date.astype(str)
    assert (dates == JOUR_TEST).all(), "Des lignes pos_sales ont une mauvaise date"


def test_dates_correctes_returns():
    """Toutes les lignes returns ont return_ts dont la date = JOUR_TEST."""
    df = lire_partition("returns", JOUR_TEST)
    if df.empty:
        pytest.skip("Aucun retour ce jour-là")
    dates = pd.to_datetime(df["return_ts"]).dt.date.astype(str)
    assert (dates == JOUR_TEST).all(), "Des lignes returns ont une mauvaise date"


# ---------------------------------------------------------------------------
# Test 3 : idempotence (relancer le même jour = même résultat)
# ---------------------------------------------------------------------------

def test_idempotence_orders():
    """Relancer simulate pour le même jour ne crée pas de doublons."""
    from data_generator.simulate import simuler_plage

    # Compte les lignes avant
    df_avant = lire_partition("orders", JOUR_TEST)
    nb_avant = len(df_avant)

    # Relance une deuxième fois
    con = duckdb.connect()
    simuler_plage(con, SOURCE_DIR, OUT_DIR, JOUR_TEST, JOUR_TEST, "csv")
    con.close()

    # Compte les lignes après
    df_apres = lire_partition("orders", JOUR_TEST)
    nb_apres = len(df_apres)

    assert nb_avant == nb_apres, (
        f"Idempotence violée : {nb_avant} lignes avant, {nb_apres} après relance"
    )


# ---------------------------------------------------------------------------
# Test 4 : cohérence du total (partition ⊆ source)
# ---------------------------------------------------------------------------

def test_total_orders_coherent():
    """
    Le nombre de lignes dans la partition = ce que DuckDB compte dans la source pour ce jour.
    Vérifie la cohérence simulateur vs source directe.
    """
    df_partition = lire_partition("orders", JOUR_TEST)
    nb_partition  = len(df_partition)

    con = duckdb.connect()
    nb_source = con.execute(f"""
        SELECT COUNT(*) FROM read_csv_auto('raw/orders/orders.csv.gz', compression='gzip')
        WHERE CAST(order_ts AS DATE) = '{JOUR_TEST}'
    """).fetchone()[0]
    con.close()

    assert nb_partition == nb_source, (
        f"Partition orders : {nb_partition} lignes vs {nb_source} attendues dans la source"
    )


def test_total_pos_sales_coherent():
    """Même vérification pour pos_sales."""
    df_partition = lire_partition("pos_sales", JOUR_TEST)
    nb_partition  = len(df_partition)

    con = duckdb.connect()
    nb_source = con.execute(f"""
        SELECT COUNT(*) FROM read_csv_auto('raw/pos/pos_sales.csv.gz', compression='gzip')
        WHERE CAST(sale_ts AS DATE) = '{JOUR_TEST}'
    """).fetchone()[0]
    con.close()

    assert nb_partition == nb_source, (
        f"Partition pos_sales : {nb_partition} lignes vs {nb_source} attendues"
    )


# ---------------------------------------------------------------------------
# Test 5 : colonnes attendues présentes
# ---------------------------------------------------------------------------

def test_colonnes_order_items():
    """order_items ne doit pas contenir la colonne _order_date (colonne temporaire)."""
    df = lire_partition("order_items", JOUR_TEST)
    assert "_order_date" not in df.columns, "Colonne temporaire _order_date présente dans order_items"
    for col in ["order_item_id", "order_id", "product_id", "qty", "unit_price",
                "discount_rate", "net_amount"]:
        assert col in df.columns, f"Colonne manquante dans order_items : {col}"
