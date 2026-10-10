#!/usr/bin/env python3
"""Capture original RenderShip request positions at the actual outer boundary."""
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import struct
from unicorn.x86_const import UC_X86_REG_SP
from skyroads_cycle import Attempt
from skyroads_tick import TickConfig
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads'
spec=importlib.util.spec_from_file_location('cycle_fixture',ROOT/'scripts/validate-skyroads-cycle.py')
f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
class PresentationOriginal(f.OriginalAttempt):
    def code(self,uc,address,size,user):
        if address==f.BASE+0xc98:
            self.presented=asdict(self.state())
            if self.word(uc.reg_read(UC_X86_REG_SP)+2):self.presented['height']=(self.presented['height']-128)&65535
        super().code(uc,address,size,user)
def view(s):return {k:s[k] for k in ('forward','lateral','height','crash_ticks')}
corpus=[];counts=0
for tile in (1,2,12,0x101):
    road=struct.pack('<70H',*([tile]*70));cfg=TickConfig(8,130,60,10)
    a=Attempt(road,cfg);old=PresentationOriginal();old.start(road,cfg)
    case={'road_hex':road.hex(),'config':asdict(cfg),'initial':a.snapshot(),'initial_display':view(old.presented),'frames':[]}
    if tile==0x101:a.state.forward=(10<<16)-32768;a.state.speed=4000;old.set_state(a.state)
    inputs=[(1,1)]*5+[(1024,1),(0,0),(512,0),(0,0),(1,1),(256,1)] if tile in (1,2) else [(1,1)]*120
    for mask,elapsed in inputs:
        if a.phase=='returned':break
        before=a.snapshot();old.advance(mask,elapsed);a.advance(mask,elapsed)
        case['frames'].append({'before':before,'after':a.snapshot(),'display':view(old.presented),'input':{'mask':mask,'elapsed':elapsed}});counts+=1
    corpus.append(case)
(OUT/'presentation-corpus.json').write_text(json.dumps(corpus,separators=(',',':'))+'\n')
print('Original render request boundaries captured:',counts)
