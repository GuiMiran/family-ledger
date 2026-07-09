# FAMILY LEDGER — Arquitectura Técnica (MVP v1)

> "Cada euro tiene un propósito."

Documento de especificación técnica para la Fase 1 (MVP). Alcance reducido y ejecutable: OCR de tickets, inventario/despensa, alertas de caducidad, menús sugeridos y dashboard básico de ahorro. El resto del documento original (comparador de supermercados, integración bancaria, facturas, predicción avanzada) queda en el roadmap de Fases 2-4.

---

## 1. Principios de Arquitectura

- **Clean Architecture**: separación estricta Dominio → Aplicación → Infraestructura → Presentación.
- **IA desacoplada**: el motor de IA (clasificación, recomendaciones, menús) es un servicio independiente, invocable vía API interna. Ningún módulo de negocio depende directamente del proveedor de IA.
- **OCR desacoplado**: el proveedor de OCR es intercambiable (empezar con uno, poder sustituirlo sin tocar el dominio).
- **Contract-first**: cada servicio expone un contrato OpenAPI antes de implementarse.
- **Diseño mobile-first, API-first**: Flutter consume exclusivamente la REST API, sin lógica de negocio en el cliente.

---

## 2. Mapa de Servicios (Fase 1)

```
┌─────────────────────────────────────────────────────────────┐
│                      Flutter App (Cliente)                   │
│         Cámara → Captura ticket → UI inventario/menús        │
└───────────────────────────┬───────────────────────────────────┘
                             │ REST/JWT
┌───────────────────────────▼───────────────────────────────────┐
│                     API Gateway (FastAPI)                     │
│        Auth · Routing · Rate limiting · Validación            │
└──┬──────────────┬──────────────┬──────────────┬───────────────┘
   │              │              │              │
┌──▼───────┐  ┌───▼────────┐ ┌───▼──────────┐ ┌─▼─────────────┐
│ Receipt  │  │ Inventory  │ │  Menu/AI     │ │  Analytics     │
│ Service  │  │ Service    │ │  Service     │ │  Service       │
│(OCR +    │  │(Despensa+  │ │(Sugerencias  │ │(Dashboards +   │
│ parsing) │  │ Congelador)│ │ + IA texto)  │ │ KPIs)          │
└──┬───────┘  └───┬────────┘ └───┬──────────┘ └─┬─────────────┘
   │              │              │              │
   └──────────────┴──────┬───────┴──────────────┘
                          │
                 ┌────────▼─────────┐
                 │   PostgreSQL      │
                 │  (esquema único   │
                 │   Fase 1, futuros │
                 │   schemas por     │
                 │   dominio)        │
                 └───────────────────┘
```

Cada servicio es un módulo FastAPI independiente (mismo repo, distinto proceso/contenedor Docker). Se separan en microservicios reales solo cuando el volumen lo justifique — evita sobre-ingeniería prematura.

---

## 3. Flujo Principal (Foto de Ticket)

1. App captura foto → sube a `Receipt Service` (`POST /receipts`).
2. `Receipt Service` llama al proveedor OCR (desacoplado vía interfaz `OCRProvider`).
3. Resultado crudo del OCR pasa por un **parser de reglas por supermercado** (Mercadona, Lidl, Bonpreu, Carrefour tienen formatos de ticket distintos → un parser por cadena, con fallback genérico).
4. Se calcula `confianza_ocr` por campo. Si algún campo crítico (importe total, fecha) < umbral → se devuelve a la app **solo ese campo** para confirmación (nunca el ticket completo).
5. Ticket confirmado → dispara evento `ReceiptConfirmed`.
6. `Inventory Service` escucha el evento y actualiza despensa/congelador automáticamente.
7. `Analytics Service` escucha el evento y recalcula KPIs incrementalmente (no batch nocturno, para que el ahorro se vea al instante).

**Patrón**: eventos internos vía tabla `outbox` en Postgres (simple, sin necesidad de Kafka/RabbitMQ en Fase 1). Se migra a un bus de eventos real solo si Fase 2 lo requiere.

---

## 4. Modelo de Dominio (entidades núcleo Fase 1)

- `Receipt` (ticket): supermercado, fecha, importe, IVA, método de pago, imagen original, confianza OCR global
- `ReceiptLine` (línea de ticket): producto, cantidad, peso, precio, precio/kg, promoción, descuento
- `Product` (catálogo normalizado): nombre canónico, categoría, marca — para poder comparar el mismo producto entre tickets/fechas
- `InventoryItem`: producto, cantidad actual, ubicación (despensa/nevera/congelador), stock mínimo
- `FreezerItem`: fecha congelación, fecha recomendada consumo, cantidad, ubicación
- `MenuSuggestion`: fecha, ingredientes usados (prioriza los próximos a caducar), receta
- `SavingsRecord`: periodo, ahorro estimado, motivo (promoción / mejor precio / evitar desperdicio)

**Decisión de diseño clave**: `Product` normalizado es lo que permite comparar precios en el tiempo y detectar subidas — sin esto, la IA de analítica no tiene sobre qué comparar. Es la pieza más delicada del modelo y merece revisarse antes de tocar código.

---

## 5. Stack Tecnológico (Fase 1)

| Capa | Tecnología | Nota |
|---|---|---|
| Cliente | Flutter | multiplataforma iOS/Android desde el día 1 |
| API | FastAPI (Python) | tipado con Pydantic, contratos OpenAPI automáticos |
| BD | PostgreSQL | un único esquema en Fase 1, particionado lógico por dominio |
| Auth | JWT | refresh token + access token corto |
| OCR | Proveedor externo (a decidir: Google Vision / Azure Document Intelligence) detrás de interfaz `OCRProvider` | evaluar coste por ticket antes de elegir |
| IA (menús/recomendaciones) | Claude API (Anthropic) vía servicio interno desacoplado | mismo patrón que usas en a3innuva con FAB/Ali |
| Contenedores | Docker + docker-compose (Fase 1), Kubernetes solo si escala | no sobre-dimensionar desde el inicio |
| CI/CD | GitHub Actions | igual que tus otros repos (guido-agentic-pipeline) |

---

## 6. Fuera de alcance en Fase 1 (Roadmap futuro)

- Comparador multi-supermercado (Makro, Costco, Aldi, Consum) → Fase 2
- Predicción de hábitos ("en 5 días se acaban los huevos") → Fase 2, requiere histórico mínimo de 2-3 meses
- Integración bancaria, facturas (luz/gas/agua/hipoteca) → Fase 3
- Presupuestos, objetivos de ahorro, calendario familiar → Fase 4

---

## 7. Siguientes pasos sugeridos

1. Validar el modelo de `Product` normalizado (punto más crítico y más fácil de hacer mal)
2. Elegir proveedor OCR y probar con 5-10 tickets reales vuestros (Mercadona/Lidl/Bonpreu)
3. Definir el contrato OpenAPI de `Receipt Service` y `Inventory Service`
4. Prototipo de la pantalla de captura + confirmación de campos ambiguos en Flutter

¿Quieres que desarrolle el contrato OpenAPI de `Receipt Service` como siguiente entregable, o prefieres primero cerrar el modelo de datos completo (todas las entidades con sus campos)?
