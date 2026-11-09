> PRIVACY-REDACTED HISTORICAL MATERIAL (2026-11-09). Private case details have been removed. This public copy is not byte-original evidence, its former file digests are withdrawn, and it does not re-certify historical outcomes. See docs/data-privacy.md.

# Verificación de la adopción

Ejecución local: 2026-11-07. Baseline de producto: `9b371ad1bf3c6caffa0f79cc82e2470f3cdd7a45`.
Herramienta: Spectra 0.5.0 al commit `c6d1f36d3ec98ab48e47cafeaf24b4039fdb2e85`.

| Comprobación | Resultado | Alcance |
|---|---|---|
| `spectra validate` | PASS | 13 capas, unicidad y referencias de IDs |
| `spectra trace` | Generado | 39 definiciones, 32 elementos trazables, 16 con artefacto y criterio enlazado |
| `python scripts/verify_adoption.py` | Resultado histórico redactado | Salida particular retirada; no se presenta un PASS nuevo ni se conservan importes privados |
| `python -m pytest -q` | 34 passed, 1 warning, 0,73 s | Regresión original con dependencias de diagnóstico; persistencia en SQLite |
| `pip install -e ".[dev]"` | FAIL preexistente | Setuptools detecta múltiples paquetes superiores; BF-002 |
| PostgreSQL real / HTTP → persistencia | No ejecutado | Sin sesión configurada en API ni destino desplegado identificado |

La ejecución usó Python 3.12 y un entorno virtual temporal. Dependencias directas instaladas para el diagnóstico: FastAPI 0.162.1, Pydantic 2.14.3, pydantic-settings 2.16.2, Uvicorn 0.54.0, pytest 9.2.0, httpx 0.28.1 y SQLAlchemy 2.1.8. El warning corresponde al uso de httpx por el TestClient de Starlette; no hubo fallo de pruebas.

Reproducción de diagnóstico, desde la raíz:

```bash
python -m venv .venv
.venv/bin/python -m pip install 'fastapi>=0.115' 'pydantic>=2.9' 'pydantic-settings>=2.5' 'uvicorn>=0.30' 'pytest>=8' 'httpx>=0.27' 'SQLAlchemy>=2,<3'
.venv/bin/python -m pytest -q
python scripts/verify_adoption.py
git clone https://github.com/GuiMiran/spectra.git .tools/spectra
git -C .tools/spectra checkout c6d1f36d3ec98ab48e47cafeaf24b4039fdb2e85
node .tools/spectra/bin/spectra.js validate
node .tools/spectra/bin/spectra.js trace
```

La CI replica el diagnóstico, no una instalación productiva; las dependencias tienen rangos y no constituyen un lock de producción. Para reproducir exactamente este entorno, usar las versiones directas registradas arriba y generar un lock como parte de BF-002.

El 50 % que muestra la matriz es enlace estático de artefactos y criterios, **no cobertura de pruebas ni porcentaje de producto terminado**. Los criterios de confirmación, eventos y aislamiento no tienen prueba de entrega. No se ha generado evidencia PASS ficticia para `spectra verify`.

El control AST es una barrera para esta adopción sin cambios funcionales. Un cambio funcional posterior autorizado debe versionar de forma explícita su nuevo baseline y evidencia; no debe desactivar el control silenciosamente. La matriz se regenera al cerrar una iteración y puede avanzar su historial.

No se ejecutó despliegue, migración, inserción en BD remota ni actualización de existencias. Los detalles de la transacción particular fueron retirados.
