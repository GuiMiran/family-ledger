"""Verifica baseline semántico, referencias y transcripción, sin red ni BD."""
import ast
import hashlib
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def require(condition, message):
    if not condition:
        raise SystemExit(message)

baseline = json.loads((ROOT / 'docs/brownfield/baseline.json').read_text())
for relative, expected in baseline['files'].items():
    p = ROOT / relative
    require(p.is_file(), f'Baseline file missing: {relative}')
    if 'ast_sha256' in expected:
        digest = hashlib.sha256(ast.dump(ast.parse(p.read_text()), include_attributes=False).encode()).hexdigest()
        require(digest == expected['ast_sha256'], f'Python semantics changed: {relative}')
    else:
        require(hashlib.sha256(p.read_bytes()).hexdigest() == expected['sha256'], f'Baseline changed: {relative}')

record = json.loads((ROOT / 'data/purchases/makro-36300-captured-20261107.json').read_text())
r = record['parsed_receipt']
D = Decimal
require(r['purchase_date'] is None, 'Unknown purchase date must remain null')
require(any(p['field_path'] == 'purchase_date' for p in r['pending_fields']), 'Date review missing')
require(record['status'] == 'pending_review', 'Transcription must remain pending')
require(record['database_imported'] is False and record['inventory_confirmed'] is False, 'No DB/inventory claim allowed')
require(r['invoice_number'] is None, 'Public record must omit invoice identifier')
require(len(r['lines']) == 20, 'Expected 20 monetary lines, without double-counting basket header')
require([l['line_number'] for l in r['lines']] == list(range(1, 21)), 'Line ordering invalid')
net = sum((D(l['line_total']) for l in r['lines']), D(0))
require(net == D(record['net_total']) == D('328.36'), 'Net lines do not reconcile')
vat = sum((D(g['vat']) for g in record['tax_summary']), D(0))
require(net + vat == D(r['total_amount']) == D('363.00'), 'Gross total mismatch')
require(vat == D(r['total_vat']) == D('34.64'), 'VAT mismatch')
require(sum((D(g['base']) for g in record['tax_summary']), D(0)) == net, 'Tax bases mismatch')
for group in record['tax_summary']:
    base = sum((D(l['line_total']) for l in r['lines'] if D(l['vat_rate']) == D(group['rate'])), D(0))
    require(base == D(group['base']), f"Tax group base mismatch: {group['rate']}")
    tax = (base * D(group['rate']) / 100).quantize(D('.01'), rounding=ROUND_HALF_UP)
    require(tax == D(group['vat']), 'Tax group rounding mismatch')
meat = [l for l in r['lines'] if l['unit'] == 'kg']
require(sum((D(l['quantity']) for l in meat), D(0)) == D('15.306'), 'Meat weight mismatch')
print(f'PASS: baseline Python AST preserved; {len(r["lines"])} lines; net {net}; VAT {vat}; gross {net + vat}. No database import performed.')
