#!/usr/bin/env python3
"""Run recovered SkyRoads physics without DOS, Unicorn, graphics or sound.

Writes a JSON trajectory and a CSV table in the requested output directory.
The starting state is explicitly defined by TickState, including stack locals.
"""
import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from skyroads_tick import TickState, TickConfig, TickInput, tick

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / 'analysis/skyroads'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--road', type=int, choices=range(31), default=0)
    parser.add_argument('--ticks', type=int, default=160)
    parser.add_argument('--throttle', type=int, choices=(-1,0,1), default=1)
    parser.add_argument('--direction', type=int, choices=(-1,0,1), default=0)
    parser.add_argument('--jump-at', default='25,60', help='Comma-separated zero-based tick indices')
    parser.add_argument('--no-assist', action='store_true')
    parser.add_argument('--output', type=Path, default=ANALYSIS / 'simulations/latest')
    parser.add_argument('--replay-example', help='Replay a named saved tick example and compare its complete evidence')
    args = parser.parse_args()
    if args.replay_example:
        examples = json.loads((ANALYSIS / 'tick-examples.json').read_text())
        if args.replay_example not in examples:
            parser.error('Unknown example. Available: ' + ', '.join(sorted(examples)))
        case = examples[args.replay_example]
        events = []
        result = tick(bytes.fromhex(case['road_hex']), TickState(**case['state']),
                      TickConfig(**case['config']), TickInput(**case['input']), observer=events.append)
        assert asdict(result) == case['result']
        assert [list(e) for e in events] == case['events']
        print(json.dumps({'example':args.replay_example,'matches_saved_x86_evidence':True,
                          'input':case['input'],'result':asdict(result),'trace_events':len(events)},indent=2))
        return
    if not 1 <= args.ticks <= 10000:
        parser.error('--ticks must be between1 and10000')
    try:
        jumps = {int(value) for value in args.jump_at.split(',') if value.strip()}
    except ValueError:
        parser.error('--jump-at must contain comma-separated integers')
    manifest = json.loads((ANALYSIS / 'roads/manifest.json').read_text())
    record = next(r for r in manifest['roads'] if r['index'] == args.road)
    road = (ANALYSIS / 'roads' / record['decoded_file']).read_bytes()
    config = TickConfig(*record['metadata_words'], len(road)//14, int(not args.no_assist))
    state = TickState()
    initial = asdict(state)
    samples = []
    stop = 'requested_tick_count'
    for number in range(args.ticks):
        controls = TickInput(args.throttle,args.direction,int(number in jumps),(number+50)&65535)
        events = []
        result = tick(road,state,config,controls,observer=events.append)
        state = result.state
        samples.append({'tick':number,'input':asdict(controls),'state':asdict(state),
                        'completion_requested':result.completion_requested,
                        'events':[list(e) for e in events if e[0] in ('sound','finish','resolve')]})
        if result.completion_requested or state.exit_state:
            stop = 'finish_animation_boundary' if result.completion_requested else f'exit_state_{state.exit_state}'
            break
    args.output.mkdir(parents=True,exist_ok=True)
    report = {'road_index':args.road,'road_sha256':hashlib.sha256(road).hexdigest(),
              'model_sha256':hashlib.sha256((ROOT/'scripts/skyroads_tick.py').read_bytes()).hexdigest(),
              'config':asdict(config),'initial_state':initial,'ticks_executed':len(samples),'stop_reason':stop,
              'boundary':'Defined initial frame, post-poll controls, synthetic timer; no graphics/audio/scheduling or finish animation.',
              'samples':samples}
    (args.output/'trajectory.json').write_text(json.dumps(report,indent=2)+'\n')
    with (args.output/'trajectory.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['tick',*initial])
        writer.writeheader()
        for sample in samples:
            writer.writerow({'tick':sample['tick'],**sample['state']})
    print(json.dumps({'ticks_executed':len(samples),'stop_reason':stop,'final_state':asdict(state),
                      'json':str((args.output/'trajectory.json').resolve()),
                      'csv':str((args.output/'trajectory.csv').resolve())},indent=2))


if __name__ == '__main__':
    main()
