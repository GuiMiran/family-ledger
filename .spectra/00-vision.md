# 00 · Visión y contexto
Family Ledger ayuda a una familia a registrar compras, comparar precios propios y reducir desperdicio.
Adopción brownfield del código existente; baseline y límites en [el informe](../docs/brownfield/README.md).
Estado observado: interpretación de texto de tickets Makro, Lidl y Mercadona; servicio interno de persistencia y normalización; prototipo visual separado.
Estado objetivo, todavía sin implementar de extremo a extremo: foto → OCR → confirmación → inventario → menús → analítica.
Las especificaciones técnicas originales siguen en [specs](../specs/01-architecture.md); no se reescriben como comportamiento ya entregado.
No se ha demostrado reconstrucción completa ni ejecución productiva. El ticket actual se conserva como registro pendiente, no como ingreso en una BD desplegada.
Marco normativo: no se realiza una certificación legal; los tipos fiscales del registro proceden del ticket, no de una regla tributaria nueva.
