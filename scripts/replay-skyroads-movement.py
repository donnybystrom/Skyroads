#!/usr/bin/env python3
"""Replay one saved x86-verified movement example without an emulator."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from skyroads_movement import Position, Flight, Environment, resolve_movement, predict_landing, adjust_jump

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'analysis/skyroads'


def main():
    examples = json.loads((OUT / 'movement-examples.json').read_text())
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--example', choices=sorted(examples), default='assist_adjusted')
    parser.add_argument('--trace', action='store_true', help='Include every probe/prediction step')
    args = parser.parse_args()
    case = examples[args.example]
    manifest = json.loads((OUT / 'roads/manifest.json').read_text())
    record = next(r for r in manifest['roads'] if r['index'] == case['road_index'])
    road = (OUT / 'roads' / record['decoded_file']).read_bytes()
    assert hashlib.sha256(road).hexdigest() == case['road_sha256']
    state = Flight(**{**case['state'], 'position': Position(**case['state']['position'])})
    env = Environment(**case['environment'])
    events = []
    if case['group'].startswith('resolve'):
        result = asdict(resolve_movement(road, state.position, Position(**case['target']), observer=events.append))
    elif case['group'].startswith('predict'):
        result = predict_landing(road, state, env, observer=events.append)
    else:
        result = asdict(adjust_jump(road, state, env, observer=events.append))
    assert result == case['result'], 'Result differs from saved x86-verified case'
    assert [list(event) for event in events] == case['events'], 'Trace differs from saved x86-verified case'
    output = {'example': args.example, 'road_index': case['road_index'], 'input': case['state'],
              'environment': case['environment'], 'target': case['target'], 'result': result,
              'matches_saved_x86_evidence': True, 'trace_events': len(events)}
    if args.trace:
        output['trace'] = events
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
