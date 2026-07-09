# FAMILY LEDGER — Modelo de Datos (Fase 1 MVP)

PostgreSQL 16. Un único esquema `family_ledger` en Fase 1, con prefijos lógicos por dominio para facilitar la futura separación en schemas/servicios.

Convenciones:
- Todas las tablas: `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at`, `updated_at` (trigger).
- Soft delete solo donde tenga sentido de negocio (`deleted_at`), no por defecto.
- Dinero: `NUMERIC(10,2)`. Nunca FLOAT.
- Pesos/cantidades: `NUMERIC(10,3)` (permite 0.250 kg).

---

## 1. Dominio: Identidad y Familia

### `families`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| name | TEXT | "Familia Miranda" |
| members_count | SMALLINT | 5 — usado para KPI coste/persona |
| created_at / updated_at | TIMESTAMPTZ | |

### `users`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| family_id | UUID FK → families | |
| email | CITEXT UNIQUE | |
| password_hash | TEXT | argon2id |
| display_name | TEXT | |
| role | TEXT CHECK ('admin','member') | admin gestiona familia |

> JWT: `sub = user_id`, claim `family_id` incluido en el token. Toda query filtra por `family_id` — multi-tenancy por fila desde el día 1.

---

## 2. Dominio: Tickets (Receipt)

### `supermarkets`
Catálogo semilla (Mercadona, Lidl, Bonpreu, Carrefour, Alcampo, Consum, Aldi, Makro...).
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| name | TEXT UNIQUE | |
| parser_key | TEXT | qué parser de tickets aplicar ('mercadona_v1', 'lidl_v1', 'generic') |

### `receipts`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| family_id | UUID FK | |
| supermarket_id | UUID FK → supermarkets | detectado por OCR, confirmable |
| purchase_date | DATE | |
| purchase_time | TIME NULL | si el ticket lo trae |
| total_amount | NUMERIC(10,2) | |
| total_vat | NUMERIC(10,2) NULL | |
| payment_method | TEXT CHECK ('card','cash','other') NULL | |
| image_url | TEXT | ruta en object storage (S3-compatible / disco en Fase 1) |
| raw_ocr | JSONB | respuesta completa del proveedor OCR |
| ocr_confidence | NUMERIC(4,3) | 0.000–1.000 global |
| status | TEXT CHECK ('pending_review','confirmed','rejected') | pending_review si algún campo < umbral |
| created_by | UUID FK → users | |

Índices: `(family_id, purchase_date DESC)`, `(supermarket_id)`.

### `receipt_lines`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| receipt_id | UUID FK → receipts ON DELETE CASCADE | |
| line_number | SMALLINT | orden en el ticket |
| raw_text | TEXT | línea tal cual la leyó el OCR — nunca se pierde |
| product_id | UUID FK → products NULL | NULL hasta que se normaliza |
| description | TEXT | descripción del ticket ("PLATANO CANARIAS") |
| quantity | NUMERIC(10,3) | unidades o kg |
| unit | TEXT CHECK ('unit','kg','l') | |
| unit_price | NUMERIC(10,4) NULL | precio/kg o precio/unidad |
| line_total | NUMERIC(10,2) | |
| discount_amount | NUMERIC(10,2) DEFAULT 0 | |
| promotion_text | TEXT NULL | "2ª unidad -50%" |
| vat_rate | NUMERIC(4,2) NULL | 4/10/21 |
| ocr_confidence | NUMERIC(4,3) | por línea |

---

## 3. Dominio: Catálogo de Productos (la pieza crítica)

El problema: "PLATANO CANARIAS" (Mercadona), "PLÁTANOS" (Lidl) y "PLATANO 1KG" (Bonpreu) son el mismo producto. Sin normalización, no hay comparación de precios ni evolución temporal.

### `products` (producto canónico)
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| family_id | UUID FK NULL | NULL = producto global compartido; con valor = producto privado de la familia |
| canonical_name | TEXT | "Plátano de Canarias" |
| category_id | UUID FK → categories | |
| brand | TEXT NULL | NULL = marca blanca / fresco |
| default_unit | TEXT CHECK ('unit','kg','l') | |
| typical_shelf_life_days | SMALLINT NULL | vida útil típica → alimenta alertas de caducidad |
| is_freezable | BOOLEAN DEFAULT false | |

### `product_aliases`
La tabla que hace la magia: mapea texto de ticket → producto canónico.
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK → products | |
| supermarket_id | UUID FK NULL | el alias puede ser específico de una cadena |
| alias_text | TEXT | "PLATANO CANARIAS" |
| match_type | TEXT CHECK ('exact','fuzzy','ai') | cómo se creó el mapeo |
| confidence | NUMERIC(4,3) | |

UNIQUE `(supermarket_id, alias_text)`.

**Flujo de normalización** (en `Receipt Service`, post-OCR):
1. Match exacto contra `product_aliases` → asigna `product_id`.
2. Sin match → fuzzy match (trigram, extensión `pg_trgm`) sobre aliases existentes.
3. Sin match fuzzy → llamada a IA (Claude) con la línea + categorías → propone producto canónico nuevo o mapping a existente, con confianza.
4. Confianza < umbral → cola de revisión (el usuario confirma una vez; el alias queda aprendido para siempre).

Con el tiempo, el paso 3 casi desaparece: la familia compra los mismos ~150-300 productos recurrentemente.

### `categories`
Jerarquía simple de dos niveles (Frescos → Fruta; Despensa → Pasta y arroz...).
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| parent_id | UUID FK NULL → categories | |
| name | TEXT | |

### `product_price_history`
Se inserta una fila por cada `receipt_line` normalizada. Es la tabla sobre la que se calcula evolución de precios e inflación familiar.
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| product_id | UUID FK | |
| supermarket_id | UUID FK | |
| family_id | UUID FK | |
| date | DATE | |
| unit_price | NUMERIC(10,4) | siempre normalizado a €/kg, €/l o €/unidad |
| had_promotion | BOOLEAN | |

Índice: `(product_id, supermarket_id, date DESC)`.

---

## 4. Dominio: Inventario

### `inventory_items`
Estado actual de despensa/nevera.
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| family_id | UUID FK | |
| product_id | UUID FK | |
| location | TEXT CHECK ('pantry','fridge','freezer') | |
| quantity | NUMERIC(10,3) | |
| unit | TEXT | |
| min_stock | NUMERIC(10,3) NULL | umbral de alerta stock bajo |
| expiry_date | DATE NULL | |
| source_receipt_line_id | UUID FK NULL | trazabilidad compra → inventario |

UNIQUE parcial `(family_id, product_id, location, expiry_date)` — permite lotes con caducidades distintas del mismo producto.

### `freezer_items` (extensión de inventario, ubicación 'freezer')
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| inventory_item_id | UUID FK → inventory_items | |
| frozen_date | DATE | |
| recommended_consume_by | DATE | frozen_date + regla por categoría (carne 6m, pan 3m...) |
| freezer_location | TEXT NULL | "cajón 2" |

### `inventory_movements` (event-sourcing ligero)
Todo cambio de inventario queda registrado — es lo que permite calcular desperdicio real.
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| inventory_item_id | UUID FK | |
| movement_type | TEXT CHECK ('purchase','consume','freeze','unfreeze','waste','adjust') | |
| quantity_delta | NUMERIC(10,3) | +/- |
| reason | TEXT NULL | |
| occurred_at | TIMESTAMPTZ | |
| created_by | UUID FK → users NULL | NULL si automático |

`movement_type = 'waste'` es la fuente del KPI "dinero desperdiciado": `quantity_delta × último unit_price conocido`.

---

## 5. Dominio: Menús

### `menu_suggestions`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| family_id | UUID FK | |
| suggested_for_date | DATE | |
| meal_type | TEXT CHECK ('lunch','dinner') | |
| title | TEXT | "Arroz con pollo" |
| recipe_body | TEXT | markdown generado por IA |
| status | TEXT CHECK ('suggested','accepted','rejected','cooked') | |
| ai_rationale | TEXT | "usa el pollo que caduca el jueves" |

### `menu_suggestion_ingredients`
| Campo | Tipo | Nota |
|---|---|---|
| menu_suggestion_id | UUID FK | |
| inventory_item_id | UUID FK | ingrediente concreto del inventario (lote/caducidad) |
| quantity_needed | NUMERIC(10,3) | |

Al marcar `cooked` → genera automáticamente `inventory_movements` tipo `consume`.

---

## 6. Dominio: Ahorro y Analytics

### `savings_records`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| family_id | UUID FK | |
| period | DATE | primer día del mes |
| savings_type | TEXT CHECK ('promotion','better_price','waste_avoided') | |
| amount | NUMERIC(10,2) | |
| detail | JSONB | desglose por producto |

Cálculo:
- `promotion`: suma de `discount_amount` de receipt_lines del periodo.
- `better_price`: (precio medio histórico del producto − precio pagado) × cantidad, solo si positivo.
- `waste_avoided`: valor de items consumidos que estaban a ≤3 días de caducar (se salvaron gracias a alerta/menú).

Los dashboards (gasto mensual/anual, coste por supermercado/categoría, €/kg medio, inflación familiar) se calculan con **vistas materializadas** refrescadas al confirmar cada ticket — no tablas propias. Menos estado que mantener.

### Vistas materializadas Fase 1
- `mv_monthly_spend` — gasto por familia/mes/supermercado/categoría
- `mv_price_evolution` — precio medio por producto/mes
- `mv_family_kpis` — coste/persona, coste/día, nº compras, valor despensa, valor congelador, desperdicio del mes

---

## 7. Dominio: Alertas

### `alerts`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| family_id | UUID FK | |
| alert_type | TEXT CHECK ('expiry_soon','low_stock','price_increase') | (promociones → Fase 2) |
| entity_id | UUID | inventory_item o product según tipo |
| message | TEXT | |
| severity | TEXT CHECK ('info','warning','urgent') | |
| status | TEXT CHECK ('pending','sent','dismissed','acted') | |
| trigger_at | TIMESTAMPTZ | |

Job diario (APScheduler en Fase 1, no necesita Celery aún) que evalúa reglas y genera alertas → push vía FCM.

---

## 8. Outbox (eventos internos)

### `outbox_events`
| Campo | Tipo | Nota |
|---|---|---|
| id | UUID PK | |
| event_type | TEXT | 'ReceiptConfirmed', 'InventoryLow', 'ItemExpiringSoon' |
| payload | JSONB | |
| status | TEXT CHECK ('pending','processed','failed') | |
| processed_at | TIMESTAMPTZ NULL | |

Poller cada pocos segundos procesa pendientes. Suficiente para Fase 1; sustituible por bus real sin tocar el dominio.

---

## 9. Diagrama de relaciones (resumen)

```
families ─┬─ users
          ├─ receipts ─── receipt_lines ──→ products ←── product_aliases
          │                    │                │
          │                    │                ├── categories
          │                    │                └── product_price_history
          │                    ▼
          ├─ inventory_items ─┬─ freezer_items
          │                   └─ inventory_movements
          ├─ menu_suggestions ── menu_suggestion_ingredients
          ├─ savings_records
          └─ alerts
```

---

## 10. Decisiones y trade-offs registrados

1. **`product_aliases` con aprendizaje**: el coste de IA por normalización tiende a cero con el uso — la familia compra productos recurrentes.
2. **`raw_text` y `raw_ocr` siempre se conservan**: si mañana mejora el parser, se pueden re-procesar tickets antiguos sin pedir nada al usuario.
3. **Vistas materializadas en vez de tablas de agregados**: menos código, refresco barato al volumen de una familia (~10-20 tickets/mes).
4. **`inventory_movements` como ledger**: la cifra de desperdicio sale de datos reales, no de estimaciones — coherente con la filosofía "cada euro tiene un propósito".
5. **Multi-tenancy por `family_id` desde el día 1**: si la app se comparte con más familias (o se publica), no hay migración dolorosa.
