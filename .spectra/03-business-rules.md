# 03 · Reglas de negocio
- BR-001 MUST: En el formato Makro observado, los importes de línea son netos: suma de líneas menos descuentos netos debe reconciliarse con total pagado menos IVA. Fuente: parser Makro existente y tickets; no es una afirmación sobre todos los formatos Makro. AC-001.
- BR-002 MUST: Si falta fecha o total, el parser devuelve el campo pendiente para revisión; no inventa el dato. Fuente: parsers existentes. AC-002.
- BR-003 MUST: La normalización intenta coincidencia exacta, aproximada, propuesta IA y finalmente revisión. Fuente: servicio de ingesta. AC-003.
- BR-004 MUST: El aprendizaje de alias aproximado requiere confianza mínima 0,80; las propuestas IA aceptadas requieren 0,85. Fuente: constantes del servicio existente. AC-003.
- BR-005 MUST: Un ejemplo público sintético no acredita una compra guardada en una base de datos operativa ni existencias actualizadas. Las transacciones reales permanecen privadas; AC-005.
- BR-006 SHOULD: Los tipos y bases fiscales se transcriben del ticket y se conserva el redondeo declarado por grupo. Fuente: contrato genérico de interpretación; AC-005.

- BR-007 MUST: La identidad familiar proviene de token firmado, con emisor, audiencia y caducidad; no del cuerpo. Catálogo global autorizado o propio y alias de propiedad compatible. Contrato de corrección 0.2.0; AC-008.
- BR-008 MUST: Misma clave/cuerpo/familia devuelve una compra; clave reutilizada con otro contenido produce conflicto. Claves de familias distintas son independientes. AC-009.
- BR-009 MUST: Campos requeridos y reconciliación se verifican en servidor; ausencia de fecha mantiene pendiente y sin proyección. Confirmación válida conserva el ID. AC-010.

- BR-010 MUST: Normalizar IVA incluido por kg/l/unidad, mínimos de compra y peso variable; cashback no reduce desembolso. Productos de distinto grupo, tamaño o variante no compiten. AC-011.
- BR-011 MUST: Precios sin prueba del CP solicitado son referencias; fecha futura, antigüedad excesiva, promoción caducada o requisito no cumplido impiden clasificar la oferta como elegible. AC-012.

- BR-012 MUST: Perfil nuevo sin CP, cesta ni tiendas; la familia los configura explícitamente. Recogida y asesor requieren configuración completa. Ejemplos sintéticos separados, nunca semillas productivas. AC-014.
