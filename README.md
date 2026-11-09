# Family Ledger

Family Ledger ayuda a cada familia a registrar compras, normalizar productos y comparar ofertas equivalentes con sus propios datos privados.

## Perfiles privados

Una familia nueva empieza sin código postal, cesta ni tiendas seleccionadas. El alta inicial solicita esos datos explícitamente antes de recoger precios o ejecutar el asesor. El nombre mostrado y las preferencias pertenecen a la familia autenticada; los ejemplos no se cargan como valores iniciales de producción.

El código y las pruebas públicas usan ejemplos sintéticos. Los tickets, preferencias y observaciones particulares se conservan fuera del repositorio. Consulta [privacidad y límites del historial](docs/data-privacy.md).

## Capacidades y límites

- Parsers de texto para formatos Makro, Lidl y Mercadona; un formato conocido no demuestra OCR real de una imagen.
- API autenticada para compras pendientes/confirmadas, lectura por familia y confirmación con claves idempotentes.
- Normalización exacta, aproximada y propuesta mediante un puerto de IA; los alias aprendidos y el historial se limitan a la familia autorizada.
- Evento interno y proyección transaccional de compras confirmadas. No representa consumo ni saldo físico completo de existencias.
- Comparador React de ofertas por kg/l/unidad, formatos, impuestos, zona y vigencia. El asesor inicial aplica reglas y no realiza pedidos.
- Adaptador experimental de escaparate público y contrato de feed configurable. No se afirman integraciones oficiales ni cobertura de todas las cadenas.

[API de tickets](docs/operations/api-v0.2.md) · [Base de datos](docs/operations/database.md) · [Comparador](docs/operations/shopping-v0.3.md) · [Fuentes](docs/operations/price-sources.md).

## Desarrollo

```sh
python -m pip install -e ".[dev]"
python -m pytest -q
uvicorn app.main:app --reload
```

La inicialización del esquema, provisión de familias y emisión de tokens son operaciones explícitas; sigue el procedimiento de la API. PostgreSQL se califica por ejecuciones específicas y no por resultados SQLite. No hay despliegue autorizado por este README: la publicación queda bloqueada hasta validar el alta y aislamiento de perfiles privados.

La aplicación web está en `web/`. El archivo `prototype/FamilyLedgerApp.jsx` es una **demostración sintética no productiva** que importa únicamente `prototype/demo-data.json`; no conecta una cuenta ni importa compras.

## Especificaciones y evidencia

[AGENTS.md](AGENTS.md) orienta el trabajo. Las [capas Spectra](.spectra/00-vision.md) distinguen comportamiento observado y objetivos. El [contrato del comparador](docs/changes/2026-11-08-shopping-comparator.md) y el [contrato de privacidad](docs/changes/2026-11-09-private-profiles.md) delimitan sus cambios.

El [diagnóstico histórico](docs/sdd-assessment/2026-11-07/README.md) conserva hallazgos metodológicos y límites, con datos particulares redactados. Las copias públicas modificadas no son evidencia original byte a byte ni una recertificación. No se asigna nivel organizativo ni resultado de reconstrucción.

Licencia: CC BY-NC-ND 4.0.

## Candidato 0.4.0 · frontal familiar y captura

Interfaz móvil con Inicio, Despensa, Cámara, Menús y Ahorro; comparador y perfil
accesibles desde la aplicación. Dashboard basado exclusivamente en tickets
confirmados; las vistas sin datos no contienen resultados de ejemplo.

La cámara extrae borradores privados mediante OCR local Tesseract para formatos
soportados. Se revisan campos ambiguos antes del guardado validado e idempotente.
Las fotos originales no se conservan en esta versión. Menús IA, consumo y
congelación física, y medición de ahorro siguen pendientes.

[Operación y límites](docs/operations/mobile-app-v0.4.md) ·
[Contrato](docs/changes/2026-11-09-mobile-family-app.md).

Acceso piloto 0.4.1: el operador puede emitir invitaciones privadas con caducidad mediante hash configurado. El enlace general no autentica. Ver docs/changes/2026-11-09-private-access.md.
