# 00 · Visión y contexto
Family Ledger ayuda a una familia a registrar compras, comparar precios propios y reducir desperdicio.
Adopción brownfield del código existente; baseline y límites en [el informe](../docs/brownfield/README.md).
Estado observado en 0.2.0: interpretación de texto de tickets; API con identidad familiar, persistencia, confirmación e idempotencia; evento interno y proyección transaccional de compras confirmadas a inventario y analítica básica. Prototipo visual separado.
Estado objetivo pendiente: OCR real de imagen, conexión del prototipo visual, consumo/reservas de existencias, menús IA y comparaciones por unidad normalizada. La API estructurada no demuestra ese recorrido completo desde una foto.
Las especificaciones técnicas originales siguen en [specs](../specs/01-architecture.md); no se reescriben como comportamiento ya entregado.
No se ha demostrado reconstrucción completa ni ejecución productiva. Los tickets particulares quedan fuera del repositorio público; no se afirma su ingreso en una BD desplegada.
Marco normativo: no se realiza una certificación legal; los tipos fiscales del registro proceden del ticket, no de una regla tributaria nueva.

Candidato 0.3.0: comparador de cesta familiar por CP con normalización kg/l/unidad, snapshots y asesor acotado de reglas; pantalla React PWA conectada a estas rutas. Adaptador experimental del escaparate público de Mercadona y contrato de feed para otras cadenas. Disponibilidad real depende de la fuente y se informa en cobertura; no acredita seis integraciones ni OCR de foto.

Privacidad: perfiles nuevos vacíos, configuración explícita por familia y ejemplos sintéticos separados. La recogida y el asesor requieren alta completa. La publicación queda bloqueada hasta validar ese recorrido y su aislamiento. docs/data-privacy.md.
