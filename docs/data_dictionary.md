# Data Dictionary — NeoRetail
Généré manuellement à partir du profilage (`docs/profil.md`) et du dictionnaire du prof (`metadata/data_dictionary.csv`).

> **Sensible** = colonne soumise au RGPD. Voir colonne "Traitement RGPD".

---

## customers (`raw/customers/customers.csv.gz`) — 100 000 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| customer_id | VARCHAR | Identifiant client pseudonymisé | C00000001 | PK | Non | Non | — | CRM |
| customer_key | BIGINT | Clé technique séquentielle interne | 1 | — | Non | Non | — | CRM |
| region | VARCHAR | Région géographique du client | IDF | — | Oui (0.1%) | Non | — | CRM |
| segment | VARCHAR | Segment marketing (Standard/Premium/Etudiant/Entreprise) | Standard | — | Non | Non | — | CRM |
| signup_date | DATE | Date d'inscription | 2025-01-01 | — | Non | Non | — | CRM |
| consent_marketing | BOOLEAN | Consentement aux communications marketing (RGPD art. 7) | false | — | Non | Oui | À vérifier avant tout envoi marketing | CRM |
| email_pseudo | VARCHAR | Email pseudonymisé par hachage SHA-256 | u356a192b7913@synthetic.invalid | — | Non | Oui | Pseudonymisé — ne jamais exposer en clair | CRM |
| phone_pseudo | VARCHAR | Téléphone pseudonymisé par hachage partiel | 51ac9a419773a8 | — | Non | Oui | Pseudonymisé — ne jamais exposer en clair | CRM |
| is_active | BOOLEAN | Compte client actif | true | — | Non | Non | — | CRM |

---

## products (`raw/products/products.csv.gz`) — 20 000 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| product_id | VARCHAR | Identifiant produit | P0000001 | PK | Non | Non | — | ERP |
| product_key | BIGINT | Clé technique séquentielle | 1 | — | Non | Non | — | ERP |
| sku | VARCHAR | Code article unique (Stock Keeping Unit) | SKU-00000001 | — | Non | Non | — | ERP |
| category | VARCHAR | Catégorie principale (Beauty/Electronics/Fashion/Grocery/Home/Sports) | Beauty | — | Non | Non | — | ERP |
| subcategory | VARCHAR | Sous-catégorie (A/B/C/D) | A | — | Non | Non | — | ERP |
| brand | VARCHAR | Marque du produit | Brand_001 | — | Non | Non | — | ERP |
| unit_cost | DOUBLE | Coût unitaire d'achat HT (en €) | 48.99 | — | Non | Non | — | ERP |
| list_price | DOUBLE | Prix catalogue HT (en €) | 87.37 | — | Non | Non | — | ERP |
| vat_rate | DOUBLE | Taux de TVA (0.2 = 20%, 0.055 = 5.5%) | 0.2 | — | Non | Non | — | ERP |
| is_active | BOOLEAN | Produit en cours de commercialisation | true | — | Non | Non | — | ERP |
| effective_from | DATE | Date de début de validité — SCD2 | 2025-01-01 | — | Non | Non | — | ERP |
| effective_to | VARCHAR | Date de fin de validité — SCD2 (null si version courante) | null | — | Oui (100%) | Non | — | ERP |
| is_current | BOOLEAN | Vrai si version active du produit — SCD2 | true | — | Non | Non | — | ERP |

---

## stores (`raw/stores/stores.csv.gz`) — 200 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| store_id | VARCHAR | Identifiant magasin | S0001 | PK | Non | Non | — | ERP |
| store_key | BIGINT | Clé technique séquentielle | 1 | — | Non | Non | — | ERP |
| city | VARCHAR | Ville du magasin | Paris | — | Non | Non | — | ERP |
| format | VARCHAR | Format commercial (hyper/super/proximity/outlet) | super | — | Non | Non | — | ERP |
| is_active | BOOLEAN | Magasin ouvert | true | — | Non | Non | — | ERP |

---

## orders (`raw/orders/orders.csv.gz`) — 500 000 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| order_id | VARCHAR | Identifiant commande | O0000000001 | PK | Non | Non | — | E-commerce |
| order_ts | TIMESTAMP | Horodatage de la commande | 2025-06-15 14:32:00 | — | Non | Non | — | E-commerce |
| customer_id | VARCHAR | Client ayant passé la commande | C00052834 | FK→customers | Non | Non | — | E-commerce |
| channel | VARCHAR | Canal de vente (web/mobile/marketplace) | web | — | Non | Non | — | E-commerce |
| payment_method | VARCHAR | Moyen de paiement (card/wallet/transfer/gift_card) | card | — | Non | Non | — | E-commerce |
| status | VARCHAR | Statut de la commande (paid/shipped/delivered/cancelled) | paid | — | Non | Non | — | E-commerce |
| promo_code | VARCHAR | Code promotionnel utilisé (NONE si aucun) | PROMO10 | — | Non | Non | — | E-commerce |

---

## order_items (`raw/orders/order_items.csv.gz`) — 1 000 000 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| order_item_id | BIGINT | Identifiant ligne de commande | 1 | PK | Non | Non | — | E-commerce |
| order_id | VARCHAR | Commande parente | O0000311489 | FK→orders | Non | Non | — | E-commerce |
| product_id | VARCHAR | Produit commandé | P0005236 | FK→products | Non | Non | — | E-commerce |
| qty | BIGINT | Quantité commandée | 2 | — | Non | Non | — | E-commerce |
| unit_price | DOUBLE | Prix unitaire au moment de la commande (HT) | 29.36 | — | Non | Non | — | E-commerce |
| discount_rate | DOUBLE | Taux de remise (0.0 = aucune, 0.1 = 10%) | 0.1 | — | Non | Non | — | E-commerce |
| net_amount | DOUBLE | Montant net = qty × unit_price × (1 − discount_rate) | 52.85 | — | Non | Non | — | E-commerce |

---

## pos_sales (`raw/pos/pos_sales.csv.gz`) — 500 000 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| sale_id | VARCHAR | Identifiant vente caisse | PS0000000001 | PK | Non | Non | — | POS |
| sale_ts | TIMESTAMP | Horodatage de la vente en magasin | 2025-06-15 10:04:00 | — | Non | Non | — | POS |
| store_id | VARCHAR | Magasin | S0121 | FK→stores | Non | Non | — | POS |
| customer_id | VARCHAR | Client fidélisé (null si achat anonyme) | C00074559 | FK→customers | Oui (27.93%) | Oui | Rattachement à une personne physique — anonymiser si agrégation | POS |
| product_id | VARCHAR | Produit vendu | P0001471 | FK→products | Non | Non | — | POS |
| qty | BIGINT | Quantité vendue | 3 | — | Non | Non | — | POS |
| unit_price | DOUBLE | Prix unitaire (HT) | 18.23 | — | Non | Non | — | POS |
| discount_rate | DOUBLE | Taux de remise | 0.0 | — | Non | Non | — | POS |
| net_amount | DOUBLE | Montant net | 54.69 | — | Non | Non | — | POS |

---

## returns (`raw/returns/returns.csv.gz`) — 100 000 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| return_id | VARCHAR | Identifiant retour | R000000001 | PK | Non | Non | — | Logistique |
| return_ts | TIMESTAMP | Horodatage du retour | 2025-10-12 01:23:37 | — | Non | Non | — | Logistique |
| order_id | VARCHAR | Commande d'origine | O0000414893 | FK→orders | Non | Non | — | Logistique |
| product_id | VARCHAR | Produit retourné | P0008136 | FK→products | Non | Non | — | Logistique |
| return_qty | BIGINT | Quantité retournée | 2 | — | Non | Non | — | Logistique |
| reason | VARCHAR | Motif du retour (damaged/late/not_as_expected/other/size_issue/wrong_item) | late | — | Non | Non | — | Logistique |
| return_amount | DOUBLE | Montant remboursé (en €) | 94.29 | — | Non | Non | — | Logistique |

---

## gl_entries (`raw/erp/gl_entries.csv.gz`) — 100 000 lignes

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| entry_id | VARCHAR | Identifiant écriture comptable | GL0000000001 | PK | Non | Non | — | ERP/Compta |
| posting_date | DATE | Date comptable de l'écriture | 2025-06-15 | — | Non | Non | — | ERP/Compta |
| account_code | BIGINT | Code compte du plan comptable général | 707000 | — | Non | Non | — | ERP/Compta |
| cost_center | VARCHAR | Centre de coût | CC032 | — | Non | Non | — | ERP/Compta |
| document_type | VARCHAR | Type de document (SALE/PURCHASE/PAYMENT/REFUND/ADJUSTMENT) | SALE | — | Non | Non | — | ERP/Compta |
| amount | DOUBLE | Montant (positif = débit, négatif = crédit, en €) | 514.73 | — | Non | Non | — | ERP/Compta |
| currency | VARCHAR | Devise (toujours EUR) | EUR | — | Non | Non | — | ERP/Compta |

---

## clickstream (`stream/clickstream.jsonl.gz`) — 1 000 000 événements

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| event_id | VARCHAR | Identifiant unique de l'événement | E000000000001 | PK | Non | Non | — | Web/App |
| event_ts | VARCHAR (ISO 8601) | Horodatage de l'événement | 2025-05-30T00:34:05 | — | Non | Non | — | Web/App |
| session_id | VARCHAR | Identifiant de session navigateur | SESS0000373963 | — | Non | Non | — | Web/App |
| customer_id | VARCHAR | Client connecté | C00096372 | FK→customers | Non | Oui | Permet de reconstituer un profil de navigation — pseudonymiser en Silver | Web/App |
| event_type | VARCHAR | Type d'action (page_view/product_view/search/add_to_cart/checkout/purchase) | search | — | Non | Non | — | Web/App |
| product_id | VARCHAR | Produit concerné (null pour page_view et search) | P0016472 | FK→products | Oui (52.07%) | Non | — | Web/App |
| device | VARCHAR | Appareil utilisé (desktop/mobile/tablet) | desktop | — | Non | Non | — | Web/App |
| source | VARCHAR | Source de trafic (direct/seo/ads/email/social) | direct | — | Non | Non | — | Web/App |
| latency_ms | BIGINT | Latence serveur en millisecondes | 115 | — | Non | Non | — | Web/App |

---

## customer_updates (`cdc/customer_updates.jsonl.gz`) — 50 000 événements CDC

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| op | VARCHAR | Opération CDC (U = mise à jour, D = suppression) | U | — | Non | Non | — | CDC/CRM |
| customer_id | VARCHAR | Client mis à jour | C00097314 | FK→customers | Non | Oui | Rattachement à une personne physique — à traiter via SCD2 | CDC/CRM |
| change_ts | VARCHAR (ISO 8601) | Horodatage du changement | 2026-08-01T12:00:00 | — | Non | Non | — | CDC/CRM |
| new_region | VARCHAR | Nouvelle région du client | International | — | Non | Non | — | CDC/CRM |
| new_segment | VARCHAR | Nouveau segment marketing | Entreprise | — | Non | Non | — | CDC/CRM |
| new_consent_marketing | BOOLEAN | Nouveau consentement marketing | true | — | Non | Oui | Consentement RGPD — propager immédiatement aux systèmes marketing | CDC/CRM |

---

## stock (`data/raw/stock/`) — généré par `generate_stock.py`

> Table synthétique créée par nos soins — absente du pack prof.
> Logique : stock initial aléatoire (seed fixe), baisse avec les ventes POS, réassort tous les 7 jours ou quand le stock passe sous 10 unités, quelques ruptures (qty = 0).

| Colonne | Type | Description | Exemple | PK/FK | Nullable | Sensible | Traitement RGPD | Source |
|---|---|---|---|---|---|---|---|---|
| snapshot_date | DATE | Date du snapshot | 2025-01-01 | — | Non | Non | — | Généré |
| store_id | VARCHAR | Magasin | S0001 | FK→stores | Non | Non | — | Généré |
| product_id | VARCHAR | Produit | P0000001 | FK→products | Non | Non | — | Généré |
| qty_on_hand | INTEGER | Quantité disponible en stock (≥ 0) | 142 | — | Non | Non | — | Généré |
