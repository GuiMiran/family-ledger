# 05 · Contratos de operación
- OP-001 MUST · Interpretar: PRE texto disponible; POST ticket estructurado con líneas, confianza y campos pendientes; ERROR formato desconocido produce revisión del supermercado. US-001; AC-001 y AC-002.
- OP-002 MUST · Guardar internamente: PRE sesión y familia suministradas por el llamador; POST ticket, líneas y revisiones añadidos a la sesión; el llamador controla commit/rollback. No promete aislamiento ni idempotencia. US-002; AC-003.
- OP-003 SHOULD · Conservar transcripción: PRE fuente aportada y totales legibles; POST archivo versionado con fecha pendiente si no se ve y sin identificadores personales; no invoca una BD ni confirma existencias. US-004; AC-005.
- OP-004 MUST · Confirmar desde aplicación: PRE usuario autenticado y ticket revisado; POST persistencia y confirmación trazable. Implementado en API 0.2.0: Bearer firmado, familia del token, clave idempotente y transacción con proyección inline. El llamador resuelve campos pendientes antes de confirmar. US-003; AC-004.

- OP-005 MUST · Comparar compras: PRE familia autenticada y provisionada, perfil válido; POST ofertas por grupo y cobertura explícita. Actualización usa fuentes configuradas por operador; consulta usa snapshot propio; asesor registra plan sin compra. AC-011 AC-012 AC-013.
