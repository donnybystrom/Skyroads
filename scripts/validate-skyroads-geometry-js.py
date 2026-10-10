#!/usr/bin/env python3
"""Compare the viewer's integer geometry model against the x86-checked port."""
import json
import hashlib
from pathlib import Path
import random
import subprocess
import tempfile
from skyroads_collision import TABLES, structure_hit, support_height, unsafe_landing, position_hit, inside_tunnel

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / 'analysis/skyroads'
NODE = '/Users/donnybystrom/.nvm/versions/node/v22.21.1/bin/node'


def main():
    rng = random.Random(1993)
    manifest = json.loads((ANALYSIS / 'roads/manifest.json').read_text())
    cases = []
    for _ in range(5000):
        tile, index, height = rng.randrange(65536), rng.randrange(64), rng.randrange(65536)
        cases.append(['structureHit', [tile, index, height], structure_hit(tile, index, height)])
    for kind in range(6):
        for low in range(256):
            tile = kind * 256 + low
            cases.extend([['supportHeight', [tile, 0], support_height(tile)],
                          ['supportHeight', [tile, 1], support_height(tile, 1)],
                          ['unsafeLanding', [tile], unsafe_landing(tile)]])
    road_cases = []
    for r in manifest['roads']:
        road = (ANALYSIS / 'roads' / r['decoded_file']).read_bytes()
        for _ in range(100):
            forward = rng.randrange(len(road) // 14) * 65536 + rng.randrange(65536)
            lateral, height = rng.randrange(65536), rng.randrange(65536)
            road_cases.append([r['index'], forward, lateral, height,
                               position_hit(road, forward, lateral, height), inside_tunnel(road, forward, lateral, height)])
    payload = {'tables': TABLES, 'cases': cases, 'road_cases': road_cases, 'roads': manifest['roads']}
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as fixture:
        json.dump(payload, fixture); fixture.flush()
        completed = subprocess.run([NODE, str(ROOT / 'scripts/test-skyroads-geometry.cjs'), fixture.name], capture_output=True, text=True, check=True)
    result = json.loads(completed.stdout)
    result['geometry_js_sha256'] = hashlib.sha256((ROOT / 'scripts/skyroads-geometry.js').read_bytes()).hexdigest()
    result['basis'] = 'JavaScript viewer model vs Python predicates already checked against original x86'
    (ANALYSIS / 'geometry-js-validation.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
