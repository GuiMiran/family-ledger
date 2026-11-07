# Mapa brownfield de evidencia
| Dominio | Artefactos existentes | Pruebas existentes | Límite |
|---|---|---|---|
| Parsing Makro | `app/infrastructure/parsers/makro.py` | `tests/test_makro_parser.py` | Formato de fixture conocido |
| Parsing Lidl/Mercadona | parsers correspondientes y registry | `tests/test_lidl_parser.py`, `tests/test_mercadona_parser.py` | No OCR real |
| API de parsing | `app/main.py` | `tests/test_api.py` | Sin confirmación ni BD |
| Ingesta y normalización | `app/application/receipt_ingestion.py`, ORM, matchers | `tests/test_ingestion.py` | SQLite, llamador gestiona transacción |
| Registro de 363 EUR | `data/purchases/makro-36300-captured-20261107.json` | `scripts/verify_adoption.py` | Sin importación ni stock confirmado |
| Prototipo visual | `prototype/FamilyLedgerApp.jsx` | Sin prueba de conexión API | No aplicación desplegada |
| Inventario/menús/analítica | contratos `specs/04` a `06` | Sin prueba ejecutable de entrega | Objetivo |

El mapa inverso agrupa los archivos por su responsabilidad original. Los módulos vacíos de paquetes son soporte de importación. Dockerfile, Compose y pyproject describen ejecución e instalación; no prueban un despliegue. La matriz de Spectra detecta etiquetas desconocidas, no todo código sin etiqueta; este mapa complementa ese límite.
