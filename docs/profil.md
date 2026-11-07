# Rapport de profilage — NeoRetail
Généré le 2026-10-28 16:04 par `profile_data.py`

---

## customers

**Fichier :** `raw/customers/customers.csv.gz`

**Lignes :** 100,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| customer_id | VARCHAR | C00000001 | 0.0% |
| customer_key | BIGINT | 1 | 0.0% |
| region | VARCHAR | IDF | 0.1% |
| segment | VARCHAR | Standard | 0.0% |
| signup_date | DATE | 2025-01-01 | 0.0% |
| consent_marketing | BOOLEAN | False | 0.0% |
| email_pseudo | VARCHAR | u356a192b7913@synthetic.invalid | 0.0% |
| phone_pseudo | VARCHAR | 51ac9a419773a8 | 0.0% |
| is_active | BOOLEAN | False | 0.0% |

### Plage temporelle

- **signup_date** : 2025-01-01 → 2025-01-01

### Valeurs distinctes (colonnes catégorielles)

- **region** (9) : Centre, Est, IDF, International, Nord, Ouest, Sud-Est, Sud-Ouest, None
- **segment** (4) : Entreprise, Etudiant, Premium, Standard
- **is_active** (2) : False, True

### Clé primaire

- **customer_id** : 100,000 lignes, ✅ unique

---

## products

**Fichier :** `raw/products/products.csv.gz`

**Lignes :** 20,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| product_id | VARCHAR | P0000001 | 0.0% |
| product_key | BIGINT | 1 | 0.0% |
| sku | VARCHAR | SKU-00000001 | 0.0% |
| category | VARCHAR | Beauty | 0.0% |
| subcategory | VARCHAR | A | 0.0% |
| brand | VARCHAR | Brand_391 | 0.0% |
| unit_cost | DOUBLE | 48.99 | 0.0% |
| list_price | DOUBLE | 87.37 | 0.0% |
| vat_rate | DOUBLE | 0.2 | 0.0% |
| is_active | BOOLEAN | True | 0.0% |
| effective_from | DATE | 2025-01-01 | 0.0% |
| effective_to | VARCHAR | N/A | 100.0% |
| is_current | BOOLEAN | True | 0.0% |

### Plage temporelle

- **effective_from** : 2025-01-01 → 2025-01-01
- **effective_to** : None → None

### Valeurs distinctes (colonnes catégorielles)

- **category** (6) : Beauty, Electronics, Fashion, Grocery, Home, Sports
- **subcategory** (4) : A, B, C, D
- **brand** (20) : Brand_001, Brand_002, Brand_003, Brand_004, Brand_005, Brand_006, Brand_007, Brand_008, Brand_009, Brand_010, Brand_011, Brand_012, Brand_013, Brand_014, Brand_015, Brand_016, Brand_017, Brand_018, Brand_019, Brand_020
- **is_active** (2) : False, True
- **is_current** (1) : True

### Clé primaire

- **product_id** : 20,000 lignes, ✅ unique

---

## stores

**Fichier :** `raw/stores/stores.csv.gz`

**Lignes :** 200


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| store_id | VARCHAR | S0001 | 0.0% |
| store_key | BIGINT | 1 | 0.0% |
| city | VARCHAR | Bordeaux | 0.0% |
| format | VARCHAR | super | 0.0% |
| is_active | BOOLEAN | True | 0.0% |

### Valeurs distinctes (colonnes catégorielles)

- **city** (20) : Bordeaux, Clermont-Ferrand, Dijon, Grenoble, Lille, Lyon, Marseille, Metz, Montpellier, Nancy, Nantes, Nice, Orleans, Paris, Reims, Rennes, Rouen, Strasbourg, Toulouse, Tours
- **format** (4) : hyper, outlet, proximity, super
- **is_active** (2) : False, True

### Clé primaire

- **store_id** : 200 lignes, ✅ unique

---

## orders

**Fichier :** `raw/orders/orders.csv.gz`

**Lignes :** 500,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| order_id | VARCHAR | O0000000001 | 0.0% |
| order_ts | TIMESTAMP | 2026-03-09 02:34:37 | 0.0% |
| customer_id | VARCHAR | C00052834 | 0.0% |
| channel | VARCHAR | marketplace | 0.0% |
| payment_method | VARCHAR | card | 0.0% |
| status | VARCHAR | paid | 0.0% |
| promo_code | VARCHAR | NONE | 0.0% |

### Plage temporelle

- **order_ts** : 2025-01-01 00:01:55 → 2026-08-31 23:59:51

### Valeurs distinctes (colonnes catégorielles)

- **channel** (3) : marketplace, mobile, web
- **payment_method** (4) : card, gift_card, transfer, wallet
- **status** (4) : cancelled, delivered, paid, shipped

### Clé primaire

- **order_id** : 500,000 lignes, ✅ unique

### Clés étrangères

- **customer_id** → ✅ 0 orphelin

---

## order_items

**Fichier :** `raw/orders/order_items.csv.gz`

**Lignes :** 1,000,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| order_item_id | BIGINT | 1 | 0.0% |
| order_id | VARCHAR | O0000311489 | 0.0% |
| product_id | VARCHAR | P0005236 | 0.0% |
| qty | BIGINT | 4 | 0.0% |
| unit_price | DOUBLE | 29.36 | 0.0% |
| discount_rate | DOUBLE | 0.0 | 0.0% |
| net_amount | DOUBLE | 117.44 | 0.0% |

### Clé primaire

- **order_item_id** : 1,000,000 lignes, ✅ unique

### Clés étrangères

- **order_id** → ✅ 0 orphelin
- **product_id** → ✅ 0 orphelin

---

## pos_sales

**Fichier :** `raw/pos/pos_sales.csv.gz`

**Lignes :** 500,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| sale_id | VARCHAR | PS0000000001 | 0.0% |
| sale_ts | TIMESTAMP | 2025-11-14 21:12:20 | 0.0% |
| store_id | VARCHAR | S0121 | 0.0% |
| customer_id | VARCHAR | C00074559 | 27.93% |
| product_id | VARCHAR | P0001471 | 0.0% |
| qty | BIGINT | 6 | 0.0% |
| unit_price | DOUBLE | 18.23 | 0.0% |
| discount_rate | DOUBLE | 0.0 | 0.0% |
| net_amount | DOUBLE | 109.39 | 0.0% |

### Plage temporelle

- **sale_ts** : 2025-01-01 00:03:29 → 2026-08-31 23:49:33

### Clé primaire

- **sale_id** : 500,000 lignes, ✅ unique

### Clés étrangères

- **store_id** → ✅ 0 orphelin
- **product_id** → ✅ 0 orphelin
- **customer_id** → ✅ 0 orphelin

---

## returns

**Fichier :** `raw/returns/returns.csv.gz`

**Lignes :** 100,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| return_id | VARCHAR | R000000001 | 0.0% |
| return_ts | TIMESTAMP | 2025-10-12 01:23:37 | 0.0% |
| order_id | VARCHAR | O0000414893 | 0.0% |
| product_id | VARCHAR | P0008136 | 0.0% |
| return_qty | BIGINT | 2 | 0.0% |
| reason | VARCHAR | late | 0.0% |
| return_amount | DOUBLE | 94.29 | 0.0% |

### Plage temporelle

- **return_ts** : 2025-01-01 00:00:05 → 2026-08-31 23:57:15

### Valeurs distinctes (colonnes catégorielles)

- **reason** (6) : damaged, late, not_as_expected, other, size_issue, wrong_item

### Clé primaire

- **return_id** : 100,000 lignes, ✅ unique

### Clés étrangères

- **order_id** → ✅ 0 orphelin
- **product_id** → ✅ 0 orphelin

---

## gl_entries

**Fichier :** `raw/erp/gl_entries.csv.gz`

**Lignes :** 100,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| entry_id | VARCHAR | GL0000000001 | 0.0% |
| posting_date | DATE | 2025-01-01 | 0.0% |
| account_code | BIGINT | 707000 | 0.0% |
| cost_center | VARCHAR | CC032 | 0.0% |
| document_type | VARCHAR | PAYMENT | 0.0% |
| amount | DOUBLE | 514.73 | 0.0% |
| currency | VARCHAR | EUR | 0.0% |

### Plage temporelle

- **posting_date** : 2025-01-01 → 2025-01-01

### Valeurs distinctes (colonnes catégorielles)

- **document_type** (5) : ADJUSTMENT, PAYMENT, PURCHASE, REFUND, SALE
- **currency** (1) : EUR

### Clé primaire

- **entry_id** : 100,000 lignes, ✅ unique

---

## clickstream

**Fichier :** `stream/clickstream.jsonl.gz`

**Lignes :** 1,000,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| event_id | VARCHAR | E000000000001 | 0.0% |
| event_ts | VARCHAR | 2025-05-30T00:34:05 | 0.0% |
| session_id | VARCHAR | SESS0000373963 | 0.0% |
| customer_id | VARCHAR | C00096372 | 0.0% |
| event_type | VARCHAR | search | 0.0% |
| product_id | VARCHAR | P0016472 | 52.07% |
| device | VARCHAR | desktop | 0.0% |
| source | VARCHAR | direct | 0.0% |
| latency_ms | BIGINT | 115 | 0.0% |

### Plage temporelle

- **event_ts** : 2025-01-01T00:00:33 → 2026-08-31T23:59:24

### Valeurs distinctes (colonnes catégorielles)

- **event_type** (6) : add_to_cart, checkout, page_view, product_view, purchase, search
- **device** (3) : desktop, mobile, tablet
- **source** (5) : ads, direct, email, seo, social

### Clé primaire

- **event_id** : 1,000,000 lignes, ✅ unique

---

## customer_updates

**Fichier :** `cdc/customer_updates.jsonl.gz`

**Lignes :** 50,000


### Colonnes et types

| Colonne | Type DuckDB | Exemple | % Null |
|---|---|---|---|
| op | VARCHAR | U | 0.0% |
| customer_id | VARCHAR | C00097314 | 0.0% |
| change_ts | VARCHAR | 2026-08-01T12:00:00 | 0.0% |
| new_region | VARCHAR | International | 0.0% |
| new_segment | VARCHAR | Entreprise | 0.0% |
| new_consent_marketing | BOOLEAN | True | 0.0% |

### Plage temporelle

- **change_ts** : 2026-08-01T12:00:00 → 2026-08-01T12:00:00

### Valeurs distinctes (colonnes catégorielles)

- **op** (2) : D, U
- **new_region** (8) : Centre, Est, IDF, International, Nord, Ouest, Sud-Est, Sud-Ouest
- **new_segment** (4) : Entreprise, Etudiant, Premium, Standard

---

## Anomalies détectées

_Cette liste servira de base pour les règles Great Expectations en S4._

- `customers.region` : 0.1% de valeurs nulles
- `products.effective_to` : 100.0% de valeurs nulles
- `pos_sales.customer_id` : 27.93% de valeurs nulles
- `clickstream.product_id` : 52.07% de valeurs nulles