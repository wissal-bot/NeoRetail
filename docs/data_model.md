# Modèle de données — NeoRetail

Diagramme entité-relation des sources brutes (Bronze layer).
Rendu automatiquement par GitHub, VS Code (extension Markdown Preview Mermaid) et Notion.

```mermaid
erDiagram
    customers ||--o{ orders          : "passe"
    customers ||--o{ pos_sales        : "effectue (optionnel)"
    customers ||--o{ clickstream      : "génère"
    customers ||--o{ customer_updates : "est mis à jour via CDC"

    orders ||--|{ order_items : "contient"
    orders ||--o{ returns     : "génère"

    products ||--o{ order_items : "est commandé dans"
    products ||--o{ pos_sales   : "est vendu dans"
    products ||--o{ returns     : "est retourné via"
    products ||--o{ clickstream : "est consulté dans (optionnel)"
    products ||--o{ stock       : "a un stock par magasin"

    stores ||--o{ pos_sales : "accueille"
    stores ||--o{ stock     : "stocke des produits"

    customers {
        string  customer_id       PK
        bigint  customer_key
        string  region
        string  segment
        date    signup_date
        boolean consent_marketing
        string  email_pseudo
        string  phone_pseudo
        boolean is_active
    }

    products {
        string  product_id    PK
        string  sku
        string  category
        string  subcategory
        string  brand
        double  unit_cost
        double  list_price
        double  vat_rate
        boolean is_active
        date    effective_from
        date    effective_to
        boolean is_current
    }

    stores {
        string  store_id  PK
        string  city
        string  format
        boolean is_active
    }

    orders {
        string    order_id       PK
        timestamp order_ts
        string    customer_id    FK
        string    channel
        string    payment_method
        string    status
        string    promo_code
    }

    order_items {
        bigint order_item_id PK
        string order_id      FK
        string product_id    FK
        bigint qty
        double unit_price
        double discount_rate
        double net_amount
    }

    pos_sales {
        string    sale_id    PK
        timestamp sale_ts
        string    store_id   FK
        string    customer_id FK
        string    product_id  FK
        bigint    qty
        double    unit_price
        double    discount_rate
        double    net_amount
    }

    returns {
        string    return_id    PK
        timestamp return_ts
        string    order_id     FK
        string    product_id   FK
        bigint    return_qty
        string    reason
        double    return_amount
    }

    gl_entries {
        string entry_id     PK
        date   posting_date
        bigint account_code
        string cost_center
        string document_type
        double amount
        string currency
    }

    clickstream {
        string event_id   PK
        string event_ts
        string session_id
        string customer_id
        string event_type
        string product_id  FK
        string device
        string source
        bigint latency_ms
    }

    customer_updates {
        string  op
        string  customer_id           FK
        string  change_ts
        string  new_region
        string  new_segment
        boolean new_consent_marketing
    }

    stock {
        date    snapshot_date PK
        string  store_id      FK
        string  product_id    FK
        integer qty_on_hand
    }
```

## Notes

- **SCD2** : `products` a des colonnes `effective_from` / `effective_to` / `is_current` pour gérer l'historique des changements de prix. Le fichier `customer_updates` est la source CDC pour appliquer SCD2 sur `customers` en Silver.
- **Achat anonyme** : `pos_sales.customer_id` est nullable — 27.93% des ventes en magasin sont anonymes (sans carte de fidélité).
- **Clickstream partiel** : `clickstream.product_id` est nullable — les événements `page_view` et `search` ne sont pas liés à un produit précis.
- **stock** : table synthétique générée par `generate_stock.py`, absente du pack prof.
