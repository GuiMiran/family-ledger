# Family Ledger · Entrada para agentes
Lee [.spectra/00-vision.md](.spectra/00-vision.md), el [análisis brownfield](docs/brownfield/README.md) y las capas relevantes antes de cambiar el proyecto.

| Tarea | Fuente | Verificación |
|---|---|---|
| Dominio y comportamiento | `.spectra/00` a `11`; detalles técnicos en `specs/` | Spectra validate; criterios vinculados |
| Interpretación de tickets | `app/infrastructure/parsers/`, `tests/test_*_parser.py` | pytest de parsers |
| Persistencia y normalización | `app/application/receipt_ingestion.py`, ORM, `tests/test_ingestion.py` | pytest; SQLite no prueba PostgreSQL |
| Registro manual | `data/purchases/` | `python scripts/verify_adoption.py` |
| Evolución | `docs/changes/`, matriz `.spectra/12-trace.md` | baseline → cambio → evidencia → revisión |

Las capas Spectra describen reglas y distinguen observado de objetivo. Las especificaciones técnicas originales se preservan; no hay dos fuentes nuevas del mismo contrato.
No marques un objetivo como implementado por tener un documento, una etiqueta o un mock. Las etiquetas @spectra son enlaces estáticos, no resultados de pruebas.
No alteres comportamiento durante la adopción brownfield sin especificación y criterios del cambio. Registra brechas y conserva comportamiento verificado.
No publiques fotos, credenciales, número de cliente, tarjeta ni identificadores de factura en este repositorio público. Los registros manuales no son el almacenamiento productivo.
No confirmes persistencia, despliegue, existencias o gasto mensual si no existe evidencia. Una fecha desconocida permanece nula.
Actualiza capas, cambios, trazabilidad y evidencia al terminar cada cambio. Las capacidades futuras siguen pendientes hasta su validación independiente.
