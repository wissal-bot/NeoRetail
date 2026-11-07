"""
common.py — Utilitaires partagés NeoRetail
Fonctions réutilisables par simulate.py ET par le futur producer Kafka (S2).
"""

import gzip
import json
import sys
import time
from pathlib import Path


def table_ref(chemin: str, fmt: str) -> str:
    """Retourne la clause FROM DuckDB selon le format du fichier."""
    if fmt == "csv":
        return f"read_csv_auto('{chemin}', compression='gzip')"
    if fmt == "jsonl":
        return f"read_json('{chemin}', format='newline_delimited', compression='gzip')"
    raise ValueError(f"Format non supporté : {fmt}")


def replay_clickstream(source_dir: str, speed: float = 1.0, out=None):
    """
    Lit clickstream.jsonl.gz trié par event_ts et émet les événements ligne par ligne.

    Paramètres :
        source_dir : dossier racine du projet
        speed      : facteur de compression temporelle
                     1.0 = temps réel, 10.0 = 10× plus vite, 0 = sans délai
        out        : fichier de sortie (None → stdout)

    Usage Kafka (S2) :
        from data_generator.common import replay_clickstream
        for ligne in replay_clickstream('.', speed=0):
            producer.send('clickstream', ligne.encode())
    """
    import duckdb

    chemin = str(Path(source_dir) / "stream" / "clickstream.jsonl.gz")
    con = duckdb.connect()

    # DuckDB lit et trie par event_ts sans tout charger en mémoire Python
    cursor = con.execute(f"""
        SELECT *
        FROM read_json('{chemin}', format='newline_delimited', compression='gzip')
        ORDER BY event_ts
    """)
    cols = [d[0] for d in cursor.description]

    prev_ts_str = None

    while True:
        batch = cursor.fetchmany(500)
        if not batch:
            break

        for row in batch:
            evt = dict(zip(cols, row))
            ts_str = str(evt["event_ts"])

            # Délai proportionnel à l'écart temporel entre deux événements consécutifs
            if prev_ts_str and speed > 0:
                delta = _delta_secondes(prev_ts_str, ts_str) / speed
                if 0 < delta < 2.0:  # cap à 2 s pour ne pas bloquer indéfiniment
                    time.sleep(delta)

            ligne = json.dumps(evt, ensure_ascii=False, default=str) + "\n"
            if out:
                out.write(ligne)
            else:
                sys.stdout.write(ligne)
                sys.stdout.flush()

            prev_ts_str = ts_str

    con.close()


def _delta_secondes(ts1: str, ts2: str) -> float:
    """Calcule la différence en secondes entre deux timestamps ISO 8601."""
    from datetime import datetime
    fmt = "%Y-%m-%dT%H:%M:%S"
    try:
        t1 = datetime.strptime(ts1[:19], fmt)
        t2 = datetime.strptime(ts2[:19], fmt)
        return max(0.0, (t2 - t1).total_seconds())
    except ValueError:
        return 0.0
