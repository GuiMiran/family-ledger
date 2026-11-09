# @spectra INV-007
"""Verify the authorized privacy baseline and explicitly synthetic public data."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise SystemExit(message)


baseline_path = ROOT / 'docs/brownfield/access-baseline.json'
if not baseline_path.is_file():
    baseline_path = ROOT / 'docs/brownfield/mobile-baseline.json'
if not baseline_path.is_file():
    baseline_path = ROOT / 'docs/brownfield/privacy-baseline.json'
baseline = json.loads(baseline_path.read_text())
require((ROOT / baseline['change_contract']).is_file(), 'Privacy change contract missing')
for relative, expected in baseline['parent_metadata_sha256'].items():
    require(hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected,
            'Redacted historical baseline metadata changed')
for relative, expected in baseline['files'].items():
    path = ROOT / relative
    require(path.is_file(), f'Baseline file missing: {relative}')
    if 'ast_sha256' in expected:
        digest = hashlib.sha256(ast.dump(ast.parse(path.read_text()), include_attributes=False).encode()).hexdigest()
        require(digest == expected['ast_sha256'], f'Python semantics changed: {relative}')
    else:
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected['sha256'],
                f'Baseline changed: {relative}')

names = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
for relative in set(names):
    if not relative or not (ROOT / relative).is_file():
        continue
    require(not relative.startswith(('data/purchases/', 'private/', 'private-data/')),
            'Private household data must not be versioned')
    require(not relative.endswith(('.private.json', '.private.txt')), 'Private file must not be versioned')
for path in (ROOT / 'tests/fixtures').glob('*_ticket.txt'):
    require('SYNTHETIC TEST DATA' in path.read_text()[:200], 'Public receipt fixtures must be synthetic')
demo = json.loads((ROOT / 'data/demo/shopping-profile.json').read_text())
require(demo['kind'] == 'synthetic_mock_data' and demo['auto_load'] is False,
        'Demo must be explicit and must never auto-load into a household profile')
require(not list((ROOT / 'data/purchases').glob('*')), 'No household purchase records may remain public')
print('PASS: privacy baseline matches; public examples are explicit synthetic data; private records are excluded. No history rewrite, database import or deployment performed.')
