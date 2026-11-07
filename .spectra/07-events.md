# 07 · Eventos
- EVT-001 SHOULD · ReceiptConfirmed: objetivo descrito en la arquitectura original para activar inventario y analítica. No existe publicador/outbox operativo en el código observado. AC-006.
No se convierte el registro manual en un evento de confirmación. El servicio interno actual usa escritura de sesión; eso no prueba entrega de eventos.
