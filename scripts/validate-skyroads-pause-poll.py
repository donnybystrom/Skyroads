#!/usr/bin/env python3
"""Original paused busy-loop transitions without a timer increment."""
import importlib.util
import json
from pathlib import Path
import struct
from skyroads_cycle import Attempt
from skyroads_tick import TickConfig
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads'
spec=importlib.util.spec_from_file_location('cycle_fixture',ROOT/'scripts/validate-skyroads-cycle.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
road=struct.pack('<700H',*([1]*700));cfg=TickConfig(8,130,60,100)
corpus=[];counts=0
for resume in (1,512,1024,256):
    model=Attempt(road,cfg);old=f.OriginalAttempt();old.start(road,cfg)
    case={'group':'pause_busy_poll','config':cfg.__dict__,'seeds':{},'road_index':None,'road_hex':road.hex(),'initial':model.snapshot(),'frames':[]}
    for mask,elapsed in [(1,1),(1024,1),(1024,3),(0,0),(resume,0),(0,0),(1,1)]:
        if model.phase=='returned':break
        events=model.advance(mask,elapsed);old.advance(mask,elapsed)
        assert model.snapshot()==old.snapshot();assert events==old.events
        case['frames'].append({'input':{'mask':mask,'elapsed':elapsed},'snapshot':model.snapshot(),'events':events,'inject_before':None});counts+=1
    corpus.append(case)
(OUT/'pause-poll-corpus.json').write_text(json.dumps(corpus,separators=(',',':'))+'\n')
(OUT/'pause-poll-validation.json').write_text(json.dumps({'verified':True,'frames':counts,'boundary':'Original paused busy loops run with elapsed=0; resume restores timer then waits for next IRQ.'},indent=2)+'\n')
print('Original pause busy polling matched:',counts)
