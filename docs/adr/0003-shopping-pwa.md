# ADR 0003 · Comparador PWA y asesor acotado

Estado: propuesto en candidato 0.3.0, sujeto a revisión del propietario.

El usuario prioriza uso familiar sencillo desde móvil y valor temprano sin meses
de infraestructura. Conservar FastAPI/PostgreSQL y el monolito modular existente;
React/Vite PWA para el comparador conectado. No iniciar microservicios ni una
segunda aplicación Flutter hasta que una necesidad nativa lo justifique.
IA/OCR permanecen desacoplados; este asesor inicial usa reglas explícitas y no
se disfraza de LLM. Integraciones por adaptadores con cobertura, procedencia y
fallos explícitos. Ventajas: un frontend web móvil, despliegue empaquetado junto
a API y validación de precios independiente. Costes: enlaces de acceso temporales
como etapa inicial; login renovable, validación móvil real y OCR de foto pendientes.

Contrato: ../changes/2026-11-08-shopping-comparator.md. No se altera silenciosamente
la especificación técnica Flutter original: queda como opción futura, no implementación.
