#!/usr/bin/env python3
"""Check saved local UI cycles against Python AND unchanged original loop."""
import argparse
from collections import Counter
import importlib.util
import json
import math
from pathlib import Path
from skyroads_cycle import Game,replay,UNDEFINED
from skyroads_session import Catalog
from skyroads_timer import TICK_SECONDS
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads'
spec=importlib.util.spec_from_file_location('cycle_fixture',ROOT/'scripts/validate-skyroads-cycle.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
parser=argparse.ArgumentParser();parser.add_argument('recordings',nargs='+',type=Path);args=parser.parse_args()
catalog=Catalog();counts=Counter();reports=[]
for file in args.recordings:
    rec=json.loads(file.read_text());assert replay(catalog,rec)['verified']
    game=Game(catalog,rec['road_index'],rec['assist'],rec['initial_completed']);original=fixture.OriginalAttempt()
    original.start(catalog.bytes[game.index],catalog.config(game.index,game.assist))
    timing=rec.get('browser_timing',{});events=timing.get('input_events',[]);quanta=0;mask=0
    resets={s['frame'] for s in timing.get('clock_segments',[])}
    polls={e['sample']:e for e in events if e.get('applied')=='pause_poll'}
    pending={}
    for e in events:
        if e.get('applied')=='pause_poll':continue
        assert e['frame']>=e['intended_frame'] and e['late_frames']==e['frame']-e['intended_frame']
        pending.setdefault(e['frame'],[]).append(e)
    def change(e):
        global mask
        mask=mask|(1<<e['index']) if e['down'] else mask&~(1<<e['index'])
    for sample in rec['samples']:
        number=sample['frame'];i=sample['input'];before=game.attempt
        if number in resets:mask=0
        if events:
            if i['elapsed']==0:change(polls[number])
            else:
                for e in pending.get(quanta,[]):change(e)
                quanta+=i['elapsed']
            assert mask==i['mask'],f'Input audit mismatch sample {number}'
        if game.phase=='attempt':
            original.advance(i['mask'],i['elapsed']);counts['original_attempt_samples']+=1
        actual=game.advance(**i);assert actual==sample
        if before.result is not None and game.phase=='attempt':
            seeds={n:getattr(before.state,n) for n in UNDEFINED}
            original.start(catalog.bytes[game.index],catalog.config(game.index,game.assist),seeds);mask=0
            counts['restarts']+=1
        if game.phase=='attempt' or before is game.attempt:assert original.snapshot()==game.attempt.snapshot()
        counts['samples']+=1
    reports.append({'file':str(file),'samples':len(rec['samples']),'timer_quanta':quanta,
                    'cpu_max_ms':timing.get('physics_cpu_max_ms'),'cpu_mean_ms':timing.get('physics_cpu_mean_ms'),
                    'render_interval_max_ms':timing.get('render_interval_max_ms'),'late_input_events':timing.get('late_input_events'),
                    'final_game_phase':game.phase,'attempts':game.attempt_number,'input_events':len(events)})
report={'verified':True,'counts':dict(counts),'recordings':reports,
        'limits':'Native browser events and exact simulated step effects checked; physical keyboard-to-photon/DOS latency not measured.'}
(OUT/'cycle-ui-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
