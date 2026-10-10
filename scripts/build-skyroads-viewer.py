#!/usr/bin/env python3
"""Build an offline, self-contained viewer of the recovered seven-lane road data."""
import json
import collections
import hashlib
from pathlib import Path
from skyroads_collision import TABLES, EXE

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'analysis/skyroads/roads/manifest.json'
TEMPLATE = ROOT / 'scripts/skyroads-viewer.template.html'
OUTPUT = ROOT / 'analysis/skyroads/road-viewer.html'


def main():
    manifest = json.loads(MANIFEST.read_text())
    validation = json.loads((ROOT / 'analysis/skyroads/lzs-validation.json').read_text())
    assert validation['verified'] and len(validation['results']) == manifest['road_count']
    for road, result in zip(manifest['roads'], validation['results']):
        assert road['index'] == result['index'] and road['decoded_sha256'] == result['x86_sha256']
    manifest['verification'] = {'blocks': len(validation['results']), 'bytes': validation['compared_bytes']}
    collision = json.loads((ROOT / 'analysis/skyroads/collision-validation.json').read_text())
    assert collision['verified'] and collision['roads_sha256'] == manifest['source_sha256']
    assert collision['tables'] == TABLES
    assert collision['exe_sha256'] == hashlib.sha256(EXE.read_bytes()).hexdigest()
    js_check = json.loads((ROOT / 'analysis/skyroads/geometry-js-validation.json').read_text())
    assert js_check['verified'] and js_check['geometry_js_sha256'] == hashlib.sha256((ROOT / 'scripts/skyroads-geometry.js').read_bytes()).hexdigest()
    words = [v for road in manifest['roads'] for row in road['rows_as_seven_uint16_le'] for v in row]
    manifest['geometry'] = {
        'tables': TABLES, 'verified_cases': collision['total_cases'],
        'names': ['Ingen struktur', 'Valv', 'Block · 12800', 'Tunnelblock · 12800', 'Block · 15360', 'Tunnelblock · 15360'],
        'nibble_counts': {str(shift): dict(collections.Counter((v >> shift) & 15 for v in words)) for shift in (0,4,8,12)},
    }
    (ROOT / 'analysis/skyroads/collision-geometry.json').write_text(json.dumps(manifest['geometry'], indent=2) + '\n')
    payload = json.dumps(manifest, separators=(',', ':')).replace('<', '\\u003c')
    html = TEMPLATE.read_text().replace('/*__MANIFEST__*/', payload).replace('/*__GEOMETRY_CODE__*/', (ROOT / 'scripts/skyroads-geometry.js').read_text())
    OUTPUT.write_text(html)
    print(OUTPUT)


if __name__ == '__main__':
    main()
