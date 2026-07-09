# API Draft

## GET /health
Returns application status.

## POST /receipts/parse
Input:
```json
{
  "store_hint": "Makro",
  "ocr_text": "..."
}
```

Output:
```json
{
  "store": "Makro",
  "date": "2026-07-04",
  "items": [],
  "subtotal": 194.89,
  "tax_total": 16.98,
  "total": 211.87,
  "confidence": 0.82,
  "ambiguous_fields": [],
  "warnings": []
}
```
