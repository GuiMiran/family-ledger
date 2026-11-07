# 10 · Flujos
- WF-001 MUST · Texto → identificación de supermercado → parser → campos pendientes. Flujo implementado de parsing; AC-001 y AC-002.
- WF-002 MUST · Ticket estructurado → sesión → normalización → historial/revisión → commit del llamador. Conectado a API autenticada en 0.2.0; transacción e idempotencia del llamador. AC-003.
- WF-003 SHOULD · Foto → transcripción manual → reconciliación → archivo pendiente → futura importación privada. Esta adopción termina en archivo pendiente. AC-005.
- WF-004 SHOULD · Confirmación → evento → inventario → analítica. Flujo implementado de proyección interna de compras confirmadas y analítica de recibos; no acredita entrega externa ni consumo de existencias. AC-006.
