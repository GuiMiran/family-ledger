# Diagnóstico GUIDO y conformidad Spectra

Repositorio: Family Ledger **0.1.0**. Commit evaluado: `0616d2b86c2930a8c96a2c65e4cae0cd5ff1ddbd`.
Protocolo: `spectra-adoption` **1.0.0**, Spectra `b7acc9a5ae1299a867db9a6a412d189eac056771`.
GUIDO: `4566a3529d833ea037eecc62efe907325ada32e1`, rúbrica `guido-scale-v0.1` (propuesta).

## Alcance y método
Se seleccionaron 8 obligaciones de interpretación, ingesta y límites de confirmación, aislamiento e inventario antes de ejecutar la regresión. El [alcance](scope.json) conserva el denominador y las exclusiones. No es una evaluación exhaustiva de la aplicación.

El auditor GUIDO se ejecutó desde un checkout separado y escribió [audit.json](audit.json) y [audit.md](audit.md) fuera del objetivo. Observó 6/8 categorías de archivos; no encontró coincidencias para las políticas de contribución y seguridad. Eso no demuestra ausencia de esas prácticas ni otorga una nota SDD.

Se conservaron [recibos](receipts.json), resultados y [huellas del paquete original](manifest.json), con objetivo limpio antes y después de ejecutar. Los informes [A](reviewer-a.json) y [B](reviewer-b.json) se produjeron independientemente y se validaron contra el [esquema de GUIDO](report-schema.json). Los revisores son subagentes analíticos de Codex; no se afirma diversidad de modelos ni aislamiento de reconstrucción.

## Resultados por obligación
| Obligación | Revisor A | Revisor B | Reconciliación provisional | Justificación |
|---|---|---|---|---|
| OBL-001 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |
| OBL-002 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |
| OBL-003 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |
| OBL-004 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |
| OBL-005 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |
| OBL-006 | FAILED | FAILED | FAILED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |
| OBL-007 | NOT_EVALUATED | NOT_EVALUATED | NOT_EVALUATED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |
| OBL-008 | DEMONSTRATED | DEMONSTRATED | DEMONSTRATED | Coinciden las dos revisiones sobre el mismo paquete y alcance. |

Coincidencia de resultados: **8/8 obligaciones comparables**. No se convierte en porcentaje de madurez. Discrepancias: ninguna en los estados de estas ocho obligaciones; los matices y límites originales se conservan en ambos informes.

## Seis dimensiones
| Dimensión | Revisor A | Revisor B |
|---|---|---|
| specCoverage | OBSERVED | OBSERVED |
| specQuality | OBSERVED | OBSERVED |
| traceability | OBSERVED | OBSERVED |
| invariantCoverage | OBSERVED | OBSERVED |
| domainExtraction | OBSERVED | OBSERVED |
| reconstructability | NOT_TESTED | NOT_TESTED |

OBSERVED significa observación sustentada, incluidos defectos; no significa aprobado. NOT_ASSESSED y NOT_TESTED conservan los límites de evidencia. La [reconciliación estructurada](reconciliation.json) no es una aprobación del propietario.

## Hallazgo prioritario: aislamiento entre familias
Una compra sintética de B se enlaza mediante alias exacto a un producto privado de A. La [sonda](probes.py), el [recibo](receipts.json) y la [salida](family-isolation.log) permiten reproducirlo. El código de normalización no limita esa búsqueda por familia. El resultado es un fallo demostrado de la obligación acotada OBL-006 / INV-004, no evidencia de exposición de datos reales ni de un ataque remoto.

Las **34 pruebas existentes pasan**, pero ninguna desafía este aislamiento. La sonda adicional de fecha ausente pasa. La verificación del registro manual también pasa: no equivale a ingreso en BD ni confirma existencias. PostgreSQL real y el flujo HTTP de confirmación siguen sin evaluarse.

## Siguiente cambio recomendado
Propietario: GuiMiran / responsable de Family Ledger. Prioridad: aislamiento antes de conectar datos privados a confirmación multiusuario.
Definir visibilidad de catálogo global frente a privado, pasar contexto familiar a normalización y comparación, añadir pruebas negativas para familias A/B en coincidencia exacta, aproximada, propuestas IA e historial. Cierre: B nunca resuelve productos privados de A y los casos globales autorizados y la regresión siguen funcionando. Estimar esfuerzo después de cerrar ese contrato; migración **NOT_ESTIMATED**.

## Reproducción
Desde un entorno de diagnóstico con las [dependencias registradas](environment.txt), ejecutar la sonda con la ruta a un checkout limpio del commit evaluado:

```sh
python probes.py /ruta/a/family-ledger missing-date
python probes.py /ruta/a/family-ledger family-isolation
```

La segunda ejecución devuelve 1 en la baseline: es el fallo esperado documentado, no una prueba omitida para presentar todo verde. No usa datos privados ni persiste una BD productiva. Para regresión, ejecutar `python -m pytest -q` en ese checkout. `scripts/verify_adoption.py` comprueba el registro manual; el inventario y los recibos no sustituyen la revisión semántica.

## Estado de la adopción
Conformidad documental propuesta en revisión: baseline histórica preservada, protocolo enlazado, registro de adopción, rutas para auditor, dos informes y brechas con cierre. El merge de la PR inicial no aprueba por anticipado esta nueva revisión ni corrige el defecto. No se asigna G1–G5, no se certifica reconstrucción y no se despliega ni modifica lógica de producto.
