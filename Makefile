# Makefile NeoRetail — S0 Data Engineering
# Usage : make <cible>

# Données source du prof (dans ce même dossier, lecture seule)
SOURCE_DIR := .

# Sortie du simulateur
RAW_DIR    := data/raw

.PHONY: setup profile simulate stock test

## Installe les dépendances Python
setup:
	pip3 install -r requirements.txt

## Étape 2 — Profilage de toutes les sources → docs/profil.md
profile:
	PYTHONPATH=. python3 data_generator/profile_data.py --source $(SOURCE_DIR) --out docs/profil.md

## Étape 4 — Simulateur de partitions journalières
## Exemple : make simulate DAY=2025-06-15
## Exemple : make simulate FROM=2025-01-01 TO=2025-01-31
simulate:
	PYTHONPATH=. python3 data_generator/simulate.py \
	  --source $(SOURCE_DIR) \
	  --out $(RAW_DIR) \
	  $(if $(DAY),--day $(DAY),) \
	  $(if $(FROM),--from $(FROM),) \
	  $(if $(TO),--to $(TO),)

## Étape 5 — Génération du stock manquant → data/raw/stock/
stock:
	PYTHONPATH=. python3 data_generator/generate_stock.py \
	  --source $(SOURCE_DIR) \
	  --out $(RAW_DIR)/stock

## Étape 6 — Lance tous les tests pytest
test:
	PYTHONPATH=. python3 -m pytest tests/ -v
