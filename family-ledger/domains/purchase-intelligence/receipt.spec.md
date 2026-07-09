# Receipt Specification

## Goal

Procesar una foto de ticket y extraer datos estructurados.

## Fields

- supermarket
- date
- total_amount
- tax_amount
- discounts
- products
- original_image
- raw_ocr_text
- ocr_confidence

## Business Rules

- El usuario no debe introducir todo manualmente.
- Si hay campos ambiguos, solo se pedirá confirmación de esos campos.
- El ticket original siempre debe conservarse.

## Acceptance Criteria

Given una foto de ticket legible,
When el sistema procesa la imagen,
Then debe extraer supermercado, fecha, total y productos principales.
