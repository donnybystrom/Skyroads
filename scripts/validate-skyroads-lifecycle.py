#!/usr/bin/env python3
"""Original keyboard IRQ, notice wait, main retry/progression, chained attempts.

Main branches and notice helper execute separately from the whole attempt
oracle. Asset loading/drawing and profile disk writes are explicit boundaries.
"""
from collections import Counter
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_INSN
from unicorn.x86_const import *
from skyroads_cycle import Game,SCANS,UNDEFINED
from skyroads_session import Catalog
from skyroads_tick import TickConfig

ROOT=Path(__file__).resolve().parent.parent; OUT=ROOT/'analysis/skyroads'
spec=importlib.util.spec_from_file_location('cycle_fixture',ROOT/'scripts/validate-skyroads-cycle.py')
cycle=importlib.util.module_from_spec(spec);spec.loader.exec_module(cycle)
Base=cycle.fixture.fixture.Original; DATA=cycle.DATA; BASE=cycle.BASE


class Branches(Base):
    def __init__(self):
        super().__init__(allowed=[(0x030e,0x03ba),(0x4459,0x4485),(0x4153,0x417e),(0x3b9d,0x3c1b)])
        self.stop=None;self.boundary=None;self.pending=False;self.saved=0;self.scan=0;self.ports=[];self.resume_at=None
        self.uc.hook_add(UC_HOOK_INSN,self.in_port,None,1,0,UC_X86_INS_IN)
        self.uc.hook_add(UC_HOOK_INSN,self.out_port,None,1,0,UC_X86_INS_OUT)
    def put(self,o,v):self.uc.mem_write(DATA+o,struct.pack('<H',v&65535))
    def word(self,o):return struct.unpack('<H',self.uc.mem_read(DATA+o,2))[0]
    def in_port(self,uc,port,size,_):
        assert port in (0x60,0x61);return self.scan if port==0x60 else 0x15
    def out_port(self,uc,port,size,value,_):self.ports.append((port,size,value))
    def skip(self,value=0):
        sp=self.uc.reg_read(UC_X86_REG_SP);self.uc.reg_write(UC_X86_REG_AX,value)
        self.uc.reg_write(UC_X86_REG_IP,self.word(sp));self.uc.reg_write(UC_X86_REG_SP,sp+2)
    def code(self,uc,address,size,user):
        at=address-BASE
        resumed=at==self.resume_at;self.resume_at=None
        if at in (0x5fcc,0x5feb,0x578c):
            if at==0x578c:self.saved+=1;self.skip()
            elif at==0x5fcc:self.skip(int(self.pending))
            else:self.pending=False;self.skip()
            return
        if at==0x4153 and self.stop=='last_flag':self.skip();return
        if (self.stop=='return_branch' and at in (0x0339,0x03b7)) or (self.stop=='last_flag' and at==0x2b3d) or (self.stop=='notice' and at==0x4465 and self.word(0x1600)<27 and not self.word(0x54a0) and not self.pending and not resumed):
            self.boundary=at;uc.emu_stop();return
        super().code(uc,address,size,user)
    def registers(self):
        for reg,v in [(UC_X86_REG_CS,0x1000),(UC_X86_REG_DS,0x1676),(UC_X86_REG_SS,0x1676),
                      (UC_X86_REG_ES,0x1676),(UC_X86_REG_SP,0xf000),(UC_X86_REG_BP,0xf020),(UC_X86_REG_EFLAGS,0x202)]:self.uc.reg_write(reg,v)
    def main_result(self,result,selected,completed):
        self.registers();self.put(0x9332,selected);self.put(0x95f6,0)
        for i,n in enumerate(completed):self.put(0x451c+2*i,n)
        self.uc.reg_write(UC_X86_REG_DI,result);self.stop='return_branch';self.boundary=None;self.saved=0
        self.uc.emu_start(BASE+0x388,0,count=10000)
        assert self.boundary and not self.error
        return {'phase':'attempt' if self.boundary==0x339 else 'selection','selected':self.word(0x9332),
                'completed':[self.word(0x451c+2*i) for i in range(30)],'saved':self.saved}
    def last_flag(self,selected,completed):
        self.registers();self.put(0x9332,selected)
        for i,n in enumerate(completed):self.put(0x451c+2*i,n)
        self.stop='last_flag';self.boundary=None;self.uc.emu_start(BASE+0x30e,0,count=10000)
        assert self.boundary==0x2b3d;return self.word(self.uc.reg_read(UC_X86_REG_SP)+2)
    def notice_start(self,gate=0):
        self.registers();self.stop='notice';self.put(0xf000,0x6800);self.put(0xf002,27)
        self.put(0x54a0,0);self.put(0xaf32,gate);self.pending=False;self.returned=False;self.boundary=None
        self.uc.emu_start(BASE+0x4459,0,count=10000);assert self.boundary==0x4465
    def notice_advance(self,pending=False):
        self.pending=pending;self.put(0x1600,self.word(0x1600)+1);self.boundary=None
        self.resume_at=self.uc.reg_read(UC_X86_REG_IP)
        self.uc.emu_start(BASE+self.uc.reg_read(UC_X86_REG_IP),0,count=10000)
        return self.returned
    def irq(self,scan):
        self.scan=scan;self.ports=[];self.stop=None;self.registers()
        self.uc.mem_write(DATA+0xf000,struct.pack('<3H',0x6800,0x1000,0x202));self.returned=False;self.error=None
        self.uc.emu_start(BASE+0x3bcc,0,count=10000);assert self.returned and not self.error
        assert self.ports==[(0x61,1,0x95),(0x61,1,0x15),(0x20,1,0x20)]
        return sum(1<<i for i in range(11) if self.uc.mem_read(DATA+0xbd2+i,1)[0]&128)


def main():
    b=Branches();counts=Counter();counters=[0]*30
    for selected in (0,15,29):
        for reason in range(8):
            for old in (0,1,65535):
                counters=[0]*30;counters[selected]=old;got=b.main_result(reason,selected,counters)
                expected=counters[:];sel=selected
                if reason==0:expected[selected]=(old+1)&65535;sel+=1
                assert got=={'phase':'selection' if reason in (0,7) else 'attempt','selected':sel,'completed':expected,'saved':int(reason==0)}
                counts['main_return_branches']+=1
    for selected in range(30):
        for n in (0,1,28,29,30):
            counters=[int(i<n) for i in range(30)]
            assert b.last_flag(selected,counters)==int(counters[selected]==0 and sum(x!=0 for x in counters)==29)
            counts['last_road_branches']+=1
    for gate,pending in [(0,False),(0,True),(1,False),(1,True)]:
        b.notice_start(gate)
        for i in range(1,28):
            returned=b.notice_advance(pending and i==4);counts['notice_frames']+=1
            if returned:break
        assert i==(4 if gate and pending else 27)
    # Original installation clears pressed bits; original make/repeat/break ISR.
    b.uc.mem_write(DATA+0xbd2,bytes(x|128 for x in SCANS)+b'\x80')
    b.uc.mem_write(0x24,struct.pack('<HH',0x1234,0x5678));b.stop=None;b.call(0x3b9d,[])
    assert bytes(b.uc.mem_read(DATA+0xbd2,12))==bytes(SCANS)+b'\0'
    assert bytes(b.uc.mem_read(0x24,4))==struct.pack('<HH',0x3bcc,0x1000)
    for i,scan in enumerate(SCANS):
        assert b.irq(scan)==1<<i;assert b.irq(scan)==1<<i;assert b.irq(scan|128)==0;counts['keyboard_irq_sequences']+=3
    for scan in (0xe0,0x45,0xc5):assert b.irq(scan)==0;counts['keyboard_irq_sequences']+=1
    b.call(0x3c03,[]);assert bytes(b.uc.mem_read(0x24,4))==struct.pack('<HH',0x1234,0x5678)
    # Two actual contiguous failed attempts with canonical undefined locals.
    catalog=Catalog();original=cycle.OriginalAttempt();corpus=[]
    for index in (1,2,3):
        g=Game(catalog,index);original.start(catalog.bytes[index],catalog.config(index));frames=[]
        for n in range(3000):
            mask=1|(512 if g.attempt.state.tick_counter in (25,60) else 0);old=g.attempt;trace=[]
            original.advance(mask);sample=g.advance(mask);trace=sample['events']
            if old.result is not None:
                branch=b.main_result(old.result,index-1,g.completed)
                assert branch['phase']==('attempt' if g.phase=='attempt' else 'selection')
                if g.phase=='attempt':
                    seeds={k:getattr(old.state,k) for k in UNDEFINED}
                    original.start(catalog.bytes[index],catalog.config(index),seeds)
            assert original.snapshot()==g.attempt.snapshot()
            frames.append(sample);counts['chained_attempt_frames']+=1
            if g.attempt_number==3:break
        assert g.attempt_number==3
        # Validate persisted replay and identity separately after all JS files exist.
        from skyroads_cycle import replay
        assert replay(catalog,g.recording())['verified']
        corpus.append({'index':index,'assist':True,'completed':[0]*30,'frames':frames})
    # Success through the complete72-frame finish and27-tick notice. Synthetic
    # tunnel geometry isolates progression; it does not claim a solved real road.
    from copy import copy
    for index,wrap,last,dismiss in [(1,False,False,False),(1,True,False,False),(30,False,True,False),(1,False,False,True)]:
        custom=copy(catalog);custom.bytes=catalog.bytes.copy();custom.roads=catalog.roads.copy()
        road=struct.pack('<70H',*([0x101]*70));custom.bytes[index]=road
        import hashlib
        custom.roads[index]={**custom.roads[index],'metadata_words':[8,130,60],'decoded_sha256':hashlib.sha256(road).hexdigest()}
        completed=[1]*30 if last else [0]*30;completed[index-1]=65535 if wrap else 0
        g=Game(custom,index,completed=completed);original.start(road,custom.config(index));frames=[]
        g.attempt.state.forward=(10<<16)-32768;g.attempt.state.speed=4000;original.set_state(g.attempt.state)
        injected=g.snapshot()
        for n in range(120):
            notice=g.phase=='notice';key=bool(dismiss and notice and g.notice_ticks==3)
            if notice:
                returned=b.notice_advance(key)
            else:original.advance(0)
            sample=g.advance(0,1,key)
            if not notice:
                assert original.snapshot()==g.attempt.snapshot()
                if g.phase=='notice':b.notice_start(int(dismiss))
            else:
                assert returned==(g.phase=='selection')
                if returned:
                    branch=b.main_result(0,index-1,completed)
                    assert branch['completed']==g.completed and branch['selected']==g.selected
            if n==0:sample={**sample,'inject_before':injected}
            frames.append(sample);counts['success_lifecycle_frames']+=1
            if g.phase=='selection':break
        assert g.phase=='selection' and g.last_road==last
        corpus.append({'index':index,'assist':True,'completed':completed,'road_hex':road.hex(),'metadata':[8,130,60],'frames':frames})
    (OUT/'lifecycle-corpus.json').write_text(json.dumps(corpus,separators=(',',':'))+'\n')
    report={'verified':True,'counts':dict(counts),'limitations':[
        'Original main return/progression branches and keyboard install/IRQ/restore execute.',
        'Notice helper executes with BIOS key availability/read boundaries; af32=0 keys cannot dismiss.',
        'Attempts run contiguously; asset drawing/loading/profile file writes are virtualized.',
        'Three unspecified stack words use explicit seeds between attempts.']}
    (OUT/'lifecycle-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
