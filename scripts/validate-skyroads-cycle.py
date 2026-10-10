#!/usr/bin/env python3
"""Execute the unchanged original init, input, HUD, waits and game loop.

Virtual boundaries: drawing calls, VGA page flip (VGA branch), IRQ timer and
held-key bytes. Real HUD arithmetic/sound calls and every physics instruction
execute. Registers/stack survive across frames and pause/finish transitions.
"""
from collections import Counter
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import time
from unicorn.x86_const import *
from skyroads_tick import TickState,GLOBALS,LOCALS,TickConfig
from skyroads_cycle import Attempt,decode_keyboard,SCANS,UNDEFINED
from skyroads_session import Catalog

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'analysis/skyroads'
spec=importlib.util.spec_from_file_location('movement_fixture',ROOT/'scripts/validate-skyroads-movement.py')
fixture=importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture)
BASE,DATA=fixture.BASE,fixture.DATA


class OriginalAttempt(fixture.Original):
    def __init__(self):
        super().__init__()
        self.allowed=[(0x1fd9,0x2b10),(0x074c,0x0afa),(0x0eeb,0x0f62),
                      (0x0ed0,0x0eeb),(0x12f8,0x1631),(0x04c0,0x05f6),
                      (0x1631,0x1fd9),(0x5d4c,0x5ded),(0x5e5a,0x5ef6),
                      (0x03c2,0x03d8),(0x0472,0x04a1),(0x04bc,0x04c0)]
        self.writable=[(o,o+w) for o,w,_ in GLOBALS.values()]+[
            (0x516e,0x5170),(0x54aa,0x54ac),(0x1600,0x1602),
            (0x9330,0x9332),(0x95f4,0x95f6),(0x547a,0x547c),
            (0x41be,0x41c0),(0x456c,0x456e),(0x960c,0x960e),
            (0x455c,0x455e),(0xaf1e,0xaf22)]
        self.frame=0xeffe; self.boundary=None; self.initializing=False
        self.phase='playing'; self.result=None; self.finish_mode=False
        self.resume_at=None
        self.boundaries=Counter()

    def skip_near(self):
        sp=self.uc.reg_read(UC_X86_REG_SP)
        self.uc.reg_write(UC_X86_REG_IP,self.word(sp)); self.uc.reg_write(UC_X86_REG_SP,sp+2)

    def code(self,uc,address,size,user):
        at=address-BASE
        resumed=at==self.resume_at
        self.resume_at=None
        if at in (0x0c98,0x0f8c,0x1218,0x1073,0x1282):
            self.instructions+=1; self.skip_near(); return
        if at==0x20aa and self.initializing:
            self.initializing=False; self.boundary='init'; uc.emu_stop(); return
        if at==0x0f05:
            self.events.append(('finish',)); self.finish_mode=True
        blocked=None
        if at==0x22f8 and self.word(0x1600)==self.word(self.frame-4): blocked='playing'
        elif at==0x0ef8 and self.word(0x1600)==uc.reg_read(UC_X86_REG_SI): blocked='finishing'
        elif at==0x20ea: blocked='pause_release'
        elif at==0x21a8: blocked='pause_press'
        elif at==0x227d: blocked='pause_clear'
        if blocked and not resumed:
            self.boundary=blocked; self.phase=blocked; self.boundaries[blocked]+=1
            uc.emu_stop(); return
        if at==0x6800:
            self.returned=True
            self.result=uc.reg_read(UC_X86_REG_AX); self.phase='returned'; self.boundary='returned'
            self.events.append(('return',self.result)); uc.emu_stop(); return
        if at==0x20d9 and self.phase=='playing': self.events.append(('pause',))
        if at==0x2280: self.events.append(('resume',))
        if at==0x0f3f: self.events.append(('finish_frame',))
        super().code(uc,address,size,user)
        if at==0x186b:
            sp=uc.reg_read(UC_X86_REG_SP); self.events.append(('resolve',self.dword(sp+2),self.word(sp+6),self.word(sp+8)))
        elif at==0x03c2: self.events.append(('sound',self.word(uc.reg_read(UC_X86_REG_SP)+2)))
        elif at==0x0476: self.events.append(('sound_busy',int(self.word(0x1600)<((self.word(0xaf38)+8)&65535))))

    def run(self,at=None):
        self.error=None; self.boundary=None
        self.resume_at=self.uc.reg_read(UC_X86_REG_IP) if at is None else None
        self.uc.emu_start(BASE+(at if at is not None else self.uc.reg_read(UC_X86_REG_IP)),0,count=self.instruction_limit)
        assert self.boundary and not self.error,self.error or 'Instruction budget exceeded'

    def mask(self,value):
        self.uc.mem_write(DATA+0xbd2,bytes(scan|(0x80 if value&(1<<i) else 0) for i,scan in enumerate(SCANS))+b'\0')

    def start(self,road,config,seeds=None):
        self.road(road)
        self.uc.mem_write(DATA+0xef80,bytes(0x90))
        for n in UNDEFINED: self.put(self.frame+LOCALS[n],(seeds or {}).get(n,0))
        for offset,value in [(0x4562,config.gravity_factor),(0x54a2,config.fuel_divisor),
                             (0x4566,config.oxygen_factor),(0x41c0,config.road_rows),
                             (0x4570,config.assist_enabled),(0x95f6,0),(0x451a,1),(0x0cb6,1),
                             (0x3c,1),(0xaf1e,0),(0x455c,0),(0x960c,0),(0x456c,0),
                             (0x41be,0),(0xaf20,65535)]: self.put(offset,value)
        for reg,value in [(UC_X86_REG_CS,0x1000),(UC_X86_REG_DS,0x1676),(UC_X86_REG_SS,0x1676),
                          (UC_X86_REG_ES,0x1676),(UC_X86_REG_SP,0xf000),(UC_X86_REG_BP,0),
                          (UC_X86_REG_EFLAGS,0x202)]: self.uc.reg_write(reg,value)
        self.put(0xf000,0x6800); self.mask(0); self.events=[]
        self.phase='playing'; self.result=None; self.finish_mode=False
        self.initializing=True; self.run(0x1fd9)
        initial=self.state()
        self.run() # execute first outer checks/HUD, park at timer wait.
        return initial

    def state(self):
        values={n:int.from_bytes(self.uc.mem_read(DATA+o,w),'little',signed=s) for n,(o,w,s) in GLOBALS.items()}
        values.update({n:self.word(self.frame+o) for n,o in LOCALS.items()})
        return TickState(**values)

    def set_state(self,state,timer=None):
        for n,(o,w,_) in GLOBALS.items(): self.put(o,getattr(state,n),w)
        for n,o in LOCALS.items(): self.put(self.frame+o,getattr(state,n))
        if timer is not None:
            self.put(0x1600,timer); self.put(self.frame-4,timer)

    def advance(self,mask,elapsed=1):
        self.events=[]
        if self.phase=='returned': return
        self.mask(mask); self.put(0x1600,self.word(0x1600)+elapsed)
        self.run()

    def snapshot(self):
        return {'state':asdict(self.state()),'timer':self.word(0x1600),'phase':self.phase,
                'result':self.result,'blink':self.word(0xaf1e),'pause_timer':self.word(self.frame-4)}


def main():
    start=time.monotonic(); original=OriginalAttempt(); counts=Counter(); digest=hashlib.sha256()
    catalog=Catalog(); cases=[]; current=None
    def begin(road,config,seeds=None,group='synthetic',index=None):
        nonlocal current
        model=Attempt(road,config,seeds)
        assert original.start(road,config,seeds)==model.state
        counts['initializers']+=1
        current={'group':group,'config':asdict(config),'seeds':seeds or {},'road_index':index,
                 'road_hex':road.hex() if index is None else None,'initial':model.snapshot(),'frames':[]}
        cases.append(current); return model
    def check(model,mask=0,elapsed=1):
        before=model.snapshot()
        previous=current['frames'][-1]['snapshot'] if current['frames'] else current['initial']
        injected=before if before!=previous else None
        events=model.advance(mask,elapsed); original.advance(mask,elapsed)
        actual=original.snapshot(); expected=model.snapshot()
        # BP-4 is the current saved outer timer in playing/paused states.
        if actual!=expected or events!=original.events:
            failure={'case':current,'input':{'mask':mask,'elapsed':elapsed},'expected':expected,'original':actual,
                     'events':events,'original_events':original.events,'ip':hex(original.uc.reg_read(UC_X86_REG_IP))}
            (OUT/'cycle-failure.json').write_text(json.dumps(failure,indent=2)+'\n')
            raise AssertionError('Cycle comparison failed; see cycle-failure.json')
        frame={'input':{'mask':mask,'elapsed':elapsed},'snapshot':expected,'events':events,'inject_before':injected}
        current['frames'].append(frame); counts[current['group']]+=1
        digest.update(json.dumps(frame,separators=(',',':')).encode())
    uniform=lambda tile,rows=100:struct.pack('<'+str(rows*7)+'H',*([tile]*(rows*7)))
    cfg=TickConfig(8,130,60,100)
    # Every one of 2^11 simultaneous-key combinations, real decoder074c.
    for mask in range(2048):
        original.mask(mask); original.put(0x95f6,0); original.events=[]
        original.call(0x074c,[])
        observed={'throttle':struct.unpack('<h',original.uc.mem_read(DATA+0x9330,2))[0],
                  'direction':struct.unpack('<h',original.uc.mem_read(DATA+0x95f4,2))[0],
                  'jump':original.word(0x547a)}
        assert observed==decode_keyboard(mask); counts['keyboard_combinations']+=1
    model=begin(uniform(1),cfg,group='pause_input')
    for mask in [1,1,1024,1024,0,0,1024,1024,0,1,3,0,512,0,256]: check(model,mask)
    for poison in (0,1,0x7fff,0x8000,0xffff,0xa5a5):
        model=begin(uniform(1),cfg,{n:poison for n in UNDEFINED},'initial_stack_seeds')
        for i in range(45): check(model,1|(512 if i==10 else 0))
    for tile,group in [(12,'hazard_cycle'),(0,'fall_cycle'),(1,'resource_cycle')]:
        model=begin(uniform(tile),cfg,group=group)
        if group=='resource_cycle':
            model.state.oxygen=1; original.set_state(model.state)
        for i in range(250):
            check(model,1)
            if model.phase=='returned': break
        assert model.phase=='returned'
    # Finish tunnel, including exact72 waits and Escape boundary.
    for elapsed,escape_frame in [(1,None),(3,None),(1,5)]:
        model=begin(uniform(0x101,10),TickConfig(8,130,60,10),group='finish_cycle')
        model.state.forward=(10<<16)-32768; model.state.speed=4000
        original.set_state(model.state)
        check(model,0)
        assert model.phase=='finishing'
        for i in range(80):
            check(model,256 if i==escape_frame else 0,elapsed)
            if model.phase=='returned': break
        assert model.phase=='returned'
    model=begin(uniform(1),cfg,group='catchup_wrap')
    for elapsed in (1,2,3,9,1): check(model,1,elapsed)
    model.timer=65535; model.state.tick_counter=65535; original.set_state(model.state,65535)
    check(model,1); check(model,1)
    for reason,crash,end in [(1,0,0),(1,41,0),(1,42,0),(1,43,0),(3,0,107),(4,0,107),(5,0,108)]:
        model=begin(uniform(1),cfg,group='exit_gate_boundaries')
        model.state.exit_state=reason;model.state.crash_ticks=crash;model.state.end_ticks=end
        original.set_state(model.state);check(model,0)
    for index in catalog.roads:
        model=begin(catalog.bytes[index],catalog.config(index),group='real_road_cycle',index=index)
        for i in range(1500):
            check(model,1|(512 if i in (25,60) else 0))
            if model.phase=='returned':break
        assert model.phase=='returned',index
        (OUT/'cycle-validation.progress.json').write_text(json.dumps({'road':index,'counts':dict(counts)})+'\n')
        print(f'Whole original road cycle {index:02d} passed',flush=True)
    (OUT/'cycle-corpus.json').write_text(json.dumps(cases,separators=(',',':'))+'\n')
    report={'verified':True,'counts':dict(counts),'total_frames':sum(len(c['frames']) for c in cases),
            'boundaries':dict(original.boundaries),'result_stream_sha256':digest.hexdigest(),
            'instructions':original.instructions,'elapsed_seconds':round(time.monotonic()-start,2),
            'limitations':['Drawing calls virtualized; HUD arithmetic and sound timestamp writes execute.',
                           'Timer and held-key IRQ state injected at original wait boundaries; DOS/BIOS latency not emulated.',
                           'Explicit seeds for three unspecified stack words; no historical DOS stack reconstruction.',
                           'Actual roads exercise failed attempts; successful finish uses a synthetic tunnel fixture.']}
    (OUT/'cycle-validation.json').write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
