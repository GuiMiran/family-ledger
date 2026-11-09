# 08 · Agentes
- AG-001 SHOULD · Asistente de compras: actor asistido que transcribe, identifica dudas y presenta resultados. La transcripción es revisable; no dispone de autoridad implícita para despliegues, confirmar inventario ni ejecutar pagos. AC-005.
No se incorpora un agente autónomo ejecutable ni un proveedor IA real en esta adopción. El NullAIProposer actual es un adaptador sin propuestas, no una IA productiva.

- AG-002 SHOULD · Asesor acotado de compras: lee perfil, recopila fuentes, valida, compara, explica y registra. Máximo una llamada por adaptador, sin bucle autónomo, sin compra/pago. `llm_used=false` en 0.3.0; no se presenta una regla como inferencia de un modelo. AC-013.
