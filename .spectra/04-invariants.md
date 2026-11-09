# 04 · Invariantes
- INV-001 MUST: Para un registro manual validado, total pagado = base imponible + IVA declarado, en céntimos exactos. Alcance: control del registro, no garantía universal de toda ruta de ingesta. AC-005.
- INV-002 MUST: Fecha desconocida implica fecha nula y campo pendiente; la fecha de registro no es la fecha de compra. AC-002 y AC-005.
- INV-003 MUST: Las líneas no normalizadas conservan descripción e importe y se envían a revisión. Observado en ingesta interna. AC-003.
- INV-004 MUST: Las operaciones de una familia deben aislarse de las de otra familia. Requisito deseado del producto; el diagnóstico del commit 0616d2b86c2930a8c96a2c65e4cae0cd5ff1ddbd reproduce un fallo de aislamiento en normalización (OBL-006). Ver docs/sdd-assessment/2026-11-07/family-isolation.log; no corregido. AC-007.
