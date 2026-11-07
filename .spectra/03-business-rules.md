# 03 · Reglas de negocio
- BR-001 MUST: En el formato Makro observado, los importes de línea son netos: suma de líneas menos descuentos netos debe reconciliarse con total pagado menos IVA. Fuente: parser Makro existente y tickets; no es una afirmación sobre todos los formatos Makro. AC-001.
- BR-002 MUST: Si falta fecha o total, el parser devuelve el campo pendiente para revisión; no inventa el dato. Fuente: parsers existentes. AC-002.
- BR-003 MUST: La normalización intenta coincidencia exacta, aproximada, propuesta IA y finalmente revisión. Fuente: servicio de ingesta. AC-003.
- BR-004 MUST: El aprendizaje de alias aproximado requiere confianza mínima 0,80; las propuestas IA aceptadas requieren 0,85. Fuente: constantes del servicio existente. AC-003.
- BR-005 MUST: Un registro manual en Git no acredita que la compra esté guardada en una base de datos operativa, ni que las existencias estén actualizadas. Decisión de esta adopción; AC-005.
- BR-006 SHOULD: Los tipos y bases fiscales se transcriben del ticket y se conserva el redondeo declarado por grupo. Fuente: ticket aportado; AC-005.
