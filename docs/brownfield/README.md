# Adopción brownfield de Family Ledger

Fecha de observación: 2026-11-07. Baseline: `9b371ad1bf3c6caffa0f79cc82e2470f3cdd7a45`.
Spectra 0.5.0 fijado en `c6d1f36d3ec98ab48e47cafeaf24b4039fdb2e85`.

## Protocolo vigente y diagnóstico
[Mapeo de entregables y límites](protocol-conformance.md).
La PR Spectra #32 ya fusionada publica el [protocolo 1.0.0](https://github.com/GuiMiran/spectra/blob/b7acc9a5ae1299a867db9a6a412d189eac056771/docs/guides/adoption-protocol.md). Esta propuesta mapea la adopción inicial a ese protocolo; ver [registro](../../.spectra/adoption/record.json) y [diagnóstico GUIDO](../sdd-assessment/2026-11-07/README.md). La aceptación de esta conformidad está pendiente de revisión.

## Protocolo inicial aplicado
En la baseline inicial no se encontró un comando ni un protocolo publicado llamado brownfield en aquella versión de Spectra. Esta adopción documenta explícitamente el procedimiento local: inventariar → preservar baseline → contrastar especificaciones/código/pruebas → extraer reglas observadas → separar objetivos → enlazar trazas → verificar → proponer PR. No se atribuye a Spectra una capacidad inexistente.

1. Inventario reproducible: [baseline.json](baseline.json), hashes SHA-256 de los artefactos anteriores y AST de Python.
2. Fuente original: [arquitectura](../../specs/01-architecture.md), [modelo](../../specs/02-data-model.md), contratos OpenAPI y código al commit indicado.
3. Reglas extraídas: [13 capas](../../.spectra/00-vision.md). Las reglas de negocio observadas no se sustituyen por intenciones del roadmap.
4. Trazabilidad: [matriz generada](../../.spectra/12-trace.md) y [mapa de evidencia](traceability.md). Las etiquetas añadidas son comentarios; se comprueba igualdad del AST del código de baseline.
5. Verificación: [resultado y límites](verification.md). Instalar dependencias de diagnóstico no corrige por sí mismo el empaquetado del producto.
6. Revisión: PR; rollback mediante revert del commit de adopción. No hay migración de datos ni despliegue.

## Estado histórico y brechas al commit evaluado
Los estados siguientes describen 0616d2b. La corrección funcional posterior 0.2.0 se detalla en [su contrato](../changes/2026-11-07-remediation-contract.md) y [operación](../operations/api-v0.2.md). Instalación, sesiones, aislamiento y flujo API se corrigen sin reescribir el diagnóstico original; OCR/menús IA, consumo real y reconstrucción siguen fuera de esta entrega.
| ID | Observación verificable | Estado / siguiente cambio |
|---|---|---|
| BF-001 | `.spectra/` y entrada para agentes no existían en baseline | Incorporados por esta adopción |
| BF-002 | `pip install -e ".[dev]"` falla por detección de múltiples paquetes superiores | Pendiente: configurar empaquetado y declarar SQLAlchemy/driver PostgreSQL, actualmente ausentes del manifiesto |
| BF-003 | API solo expone `/health` y `/api/v1/receipts/parse`; la ingesta interna no se invoca desde HTTP | Pendiente: especificar y conectar confirmación y consultas autenticadas |
| BF-004 | PostgreSQL 16 está definido en Docker Compose; no se observa conexión de sesión en el arranque API | Pendiente: configuración, migraciones y prueba real PostgreSQL |
| BF-005 | Pruebas de ingesta usan SQLite en memoria | Pendiente: prueba PostgreSQL, atomicidad, idempotencia y aislamiento entre familias |
| BF-006 | OCR, evento de confirmación, inventario y analítica se describen en contratos pero carecen de flujo operativo | Objetivos pendientes, sin declarar entrega |
| BF-007 | No existe configuración de CI en baseline | Esta adopción añade control estructural y pruebas de diagnóstico; no despliega |
| BF-008 | Ticket de 363 EUR sin fecha de venta legible | Registro pendiente; no atribuir automáticamente a noviembre ni afirmar inserción BD |
| BF-009 | Railway accesible: solo proyecto `guido-autonomous-intelligence`; no se identifica un despliegue Family Ledger | Observación limitada a la cuenta conectada; no descarta otros proveedores o equipos |
| BF-010 | Una sonda sintética de normalización reproduce asociación de compra B con producto privado A | Fallo demostrado OBL-006 / INV-004; pendiente corregir antes de conectar datos privados multiusuario |

## Orden de evolución propuesto
1. Hacer reproducible la instalación, fijar dependencias y resolver creación de sesiones/migraciones.
2. Probar persistencia PostgreSQL, aislamiento y rollback con datos sintéticos.
3. Conectar confirmación/importación y lectura con autenticación, autorización e idempotencia.
4. Importar el ticket revisado en almacenamiento privado, con fecha confirmada o estado pendiente.
5. Completar existencias y analítica; desplegar solo como cambio independiente autorizado.

## Límites
No se asigna un nivel GUIDO ni una puntuación automática sin evaluación. No se declara cobertura funcional total ni reconstrucción completa. Los registros públicos son transcripciones autorizadas reducidas y no sustituyen una BD privada.
