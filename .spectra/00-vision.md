# 00 · Visión y contexto
Family Ledger ayuda a una familia a registrar compras, comparar precios propios y reducir desperdicio.
Adopción brownfield del código existente; baseline y límites en [el informe](../docs/brownfield/README.md).
Estado observado en 0.2.0: interpretación de texto de tickets; API con identidad familiar, persistencia, confirmación e idempotencia; evento interno y proyección transaccional de compras confirmadas a inventario y analítica básica. Prototipo visual separado.
Estado objetivo pendiente: OCR real de imagen, conexión del prototipo visual, consumo/reservas de existencias, menús IA y comparaciones por unidad normalizada. La API estructurada no demuestra ese recorrido completo desde una foto.
Las especificaciones técnicas originales siguen en [specs](../specs/01-architecture.md); no se reescriben como comportamiento ya entregado.
No se ha demostrado reconstrucción completa ni ejecución productiva. El ticket actual se conserva como registro pendiente, no como ingreso en una BD desplegada.
Marco normativo: no se realiza una certificación legal; los tipos fiscales del registro proceden del ticket, no de una regla tributaria nueva.
