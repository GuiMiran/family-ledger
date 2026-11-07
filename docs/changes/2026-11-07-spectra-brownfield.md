# Cambio · Adopción Spectra brownfield
Motivo: el proyecto ya tenía código y contratos; faltaban una entrada inequívoca para agentes, capas de dominio y separación verificable entre entregado y planificado.
Baseline y protocolo: [informe](../brownfield/README.md).
Alcance: 13 capas, entrada AGENTS, etiquetas como comentarios, registro manual del ticket de 363 EUR, verificación y CI. No cambia lógica de negocio, endpoints ni esquema.
Aceptación: capas válidas, trazabilidad generada, Python AST conservado, bases/IVA del ticket reconciliados y regresión existente ejecutada con sus límites documentados.
Datos: se excluyen foto e identificadores personales. Fecha de compra desconocida, importación BD y existencias sin confirmar.
Rollback: revertir el commit de adopción; no se requiere rollback de BD porque no se ejecutó ninguna migración/importación.
Pendientes: BF-002 a BF-006 y BF-008 a BF-010 del informe; completar la adopción documental no los cierra.
