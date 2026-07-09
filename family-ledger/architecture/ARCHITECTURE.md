# Architecture

## Stack inicial propuesto

- Frontend: Flutter
- Backend: FastAPI
- Base de datos: PostgreSQL
- Contenedores: Docker
- Autenticación: JWT
- OCR: servicio desacoplado
- IA: agentes desacoplados

## Flujo principal

Foto ticket → OCR → Receipt Agent → Product Agent → Inventory Agent → Savings Agent → Dashboard.

## Regla clave

La IA no modifica directamente la base de datos. Siempre actúa mediante casos de uso controlados.
