# 04 · Invariantes
- INV-001 MUST: Para un registro manual validado, total pagado = base imponible + IVA declarado, en céntimos exactos. Alcance: control del registro, no garantía universal de toda ruta de ingesta. AC-005.
- INV-002 MUST: Fecha desconocida implica fecha nula y campo pendiente; la fecha de registro no es la fecha de compra. AC-002 y AC-005.
- INV-003 MUST: Las líneas no normalizadas conservan descripción e importe y se envían a revisión. Observado en ingesta interna. AC-003.
- INV-004 MUST: Las operaciones de una familia deben aislarse de las de otra familia. El diagnóstico histórico 0616d2b reproduce fallo OBL-006. Corrección 0.2.0: productos y alias globales autorizados o propios; contexto familiar en exact/fuzzy/IA/historial y API. Criterio negativo en tests/test_family_isolation.py y tests/test_receipt_api.py; no certifica seguridad integral. AC-007.

- INV-005 MUST: Compra, líneas, idempotencia, evento y proyección se confirman juntos o se revierten juntos; reintentos no duplican proyección. AC-009 y AC-010.

- INV-006 MUST: Perfil, observaciones personalizadas y auditoría de compras pertenecen exclusivamente a la familia autenticada. Una recomendación no crea compra, pago, inventario ni ahorro realizado. AC-013.

- INV-007 MUST: Ningún perfil o caso particular se publica como ejemplo ni se asigna a otra familia. El historial público redactado no acredita integridad byte a byte ni nueva certificación. AC-014.

- INV-008 MUST: Extraer una foto no escribe compras ni existencias. Solo el guardado validado e idempotente confirma y proyecta; fotos temporales y metadatos se eliminan. AC-016.
