# 02 · Historias
- US-001 MUST: Como responsable de compras quiero interpretar texto de un ticket para revisar importes y campos ambiguos. Observado; AC-001 y AC-002.
- US-002 MUST: Como responsable de compras quiero conservar líneas y normalizar productos para comparar precios propios. Servicio interno observado; AC-003.
- US-003 MUST: Como responsable de compras quiero guardar un ticket desde la aplicación para no depender de archivos manuales. Implementado en API autenticada 0.2.0 con compras pendientes/confirmadas; AC-004. No demuestra conexión del prototipo visual.
- US-004 SHOULD: Como responsable de compras quiero conservar una compra documentada aunque falte su fecha sin atribuirla a un mes incorrecto. Registro manual; AC-005.
- US-005 SHOULD: Como responsable de compras quiero que una compra confirmada actualice las existencias. Proyección de compras confirmadas implementada transaccionalmente en 0.2.0; consumo/reservas fuera de alcance. AC-006.
