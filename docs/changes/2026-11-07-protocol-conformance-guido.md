> Documento histórico con referencias redactadas por privacidad. Se retienen hallazgos, no una garantía de integridad byte a byte de las copias actuales.

# Cambio · Conformidad con protocolo 1.0.0 y diagnóstico GUIDO
El protocolo ya fusionado en Spectra se aplica documentalmente a la adopción inicial. Se preservan baseline histórica y lógica de producto; se añaden registro estructurado, rutas del auditor, inventario y dos revisiones con reconciliación.
Commit evaluado: 0616d2b86c2930a8c96a2c65e4cae0cd5ff1ddbd. Evidencia y límites: [diagnóstico](../sdd-assessment/2026-11-07/README.md).
Hallazgo: la sonda sintética OBL-006 falla por asociación de producto privado entre familias; se actualiza el estado de evidencia de INV-004 / AC-007, sin cambiar el requisito ni su implementación. El plan de cierre queda abierto y no se presenta el producto como listo para datos privados multiusuario.
Verificación de conformidad: capas y enlaces, registro y esquema de informes, huellas y preservación de lógica. Los recibos de regresión corresponden al commit evaluado, no a un despliegue ni a un PostgreSQL real.
Rollback: revertir este cambio documental; no hay migración ni importación de datos. La fusión previa de PR #1 no implica aprobación de esta nueva propuesta ni cierre de brechas.
