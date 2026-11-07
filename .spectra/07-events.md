# 07 · Eventos
- EVT-001 SHOULD · ReceiptConfirmed: hecho interno durable de compra confirmada en 0.2.0. Se guarda y proyecta inline en la misma transacción; no hay entrega a broker/consumidores externos. AC-006.
No se convierte un archivo manual en evento. Solo la confirmación válida de la API genera el hecho y proyección una vez. Un ticket pendiente no produce existencias ni historial de precio.
