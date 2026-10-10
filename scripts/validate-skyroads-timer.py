#!/usr/bin/env python3
"""Replay installer and unchanged IRQ0 code; virtualize OUT, stop before BIOS."""
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
from unicorn import UC_HOOK_INSN, UC_HOOK_MEM_WRITE
from unicorn.x86_const import *
from skyroads_timer import *

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'analysis/skyroads'
spec = importlib.util.spec_from_file_location('fixture', ROOT / 'scripts/validate-skyroads-collision.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
BASE, DATA = fixture.BASE, fixture.STACK


class Timer(fixture.Original):
    def __init__(self):
        super().__init__(allowed=[(0x3acc,0x3b6b),(0x5a55,0x5a64)])
        self.ports = []
        self.chain = False
        self.uc.hook_add(UC_HOOK_INSN,self.out,None,1,0,UC_X86_INS_OUT)
        self.uc.hook_add(UC_HOOK_MEM_WRITE,self.write)

    def out(self,uc,port,size,value,user):
        assert port in (0x20,0x40,0x42,0x43) and size==1
        self.ports.append([port,value])

    def write(self,uc,access,address,size,value,user):
        allowed=[(0x20,0x24),(0x90,0x94),(BASE+0x3b67,BASE+0x3b6b),
                 (DATA+0x3192,DATA+0x3193),(DATA+0xc83,DATA+0xc84),
                 (DATA+0x1600,DATA+0x1602),(DATA+0xbd0,DATA+0xbd2),
                 (DATA+0xef00,DATA+0xf020)]
        assert any(a<=address and address+size<=b for a,b in allowed),(hex(address),size)

    def code(self,uc,address,size,user):
        if address==BASE+0x3b66:
            self.chain=True;self.returned=True;uc.emu_stop();return
        super().code(uc,address,size,user)

    def run_irq(self,phase,counter,sound_word=0):
        self.uc.mem_write(DATA+0x3192,bytes([phase]))
        self.uc.mem_write(DATA+0x1600,struct.pack('<H',counter))
        self.uc.mem_write(DATA+0xc83,b'\x01') # Idle audio delay path, actual helper executes.
        self.uc.mem_write(DATA+0xbd0,struct.pack('<H',0x1200))
        self.uc.mem_write(DATA+0x1200,struct.pack('<HH',sound_word,0))
        self.ports=[];self.chain=False;self.returned=False;self.error=None
        regs=[(UC_X86_REG_CS,0x1000),(UC_X86_REG_DS,0x1555),(UC_X86_REG_SS,0x1676),
              (UC_X86_REG_SP,0xf000),(UC_X86_REG_AX,0x1234),(UC_X86_REG_BX,0x2345),
              (UC_X86_REG_CX,0x3456),(UC_X86_REG_DX,0x4567),(UC_X86_REG_SI,0x5678),
              (UC_X86_REG_DI,0x6789),(UC_X86_REG_BP,0x789a),(UC_X86_REG_EFLAGS,0x202)]
        for r,v in regs:self.uc.reg_write(r,v)
        self.uc.mem_write(DATA+0xf000,struct.pack('<3H',0x6800,0x1000,0x202))
        self.uc.emu_start(BASE+0x3b17,0,count=1000)
        assert self.returned and not self.error
        for r,v in regs:
            if r not in (UC_X86_REG_CS,UC_X86_REG_SP,UC_X86_REG_EFLAGS):assert self.uc.reg_read(r)==v
        assert self.uc.reg_read(UC_X86_REG_SP)==(0xf000 if self.chain else 0xf006)
        return self.uc.mem_read(DATA+0x3192,1)[0],struct.unpack('<H',self.uc.mem_read(DATA+0x1600,2))[0],self.chain


def main():
    original=Timer()
    original.uc.mem_write(0x20,struct.pack('<HH',0x1234,0xabcd))
    original.call(0x3acc,[])
    assert original.ports==[[0x43,0x36],[0x40,0xe4],[0x40,0x19],[0x43,0xb6],[0x42,2],[0x42,0]]
    assert bytes(original.uc.mem_read(0x20,4))==struct.pack('<HH',0x3b17,0x1000)
    assert bytes(original.uc.mem_read(0x90,4))==struct.pack('<HH',0x3b14,0x1000)
    assert bytes(original.uc.mem_read(BASE+0x3b67,4))==struct.pack('<HH',0x1234,0xabcd)
    digest=hashlib.sha256();cases=0
    for phase in range(256):
        for count in (0,65535):
            for sound in (0,1000):
                observed=original.run_irq(phase,count,sound)
                expected=irq_phase(phase,count)
                assert observed==expected,(phase,count,expected,observed)
                ports=([[0x43,0xb6],[0x42,(sound+2)&255],[0x42,(sound+2)>>8]] if phase in (0,5) else [])
                if not expected[2]:ports.append([0x20,0x20])
                assert original.ports==ports
                pointer=struct.unpack('<H',original.uc.mem_read(DATA+0xbd0,2))[0]
                assert pointer==0x1200+(2 if phase in (0,5) and sound else 0)
                digest.update(json.dumps([phase,count,sound,observed,ports]).encode());cases+=1
    phase,counter=0,0;ticks=[];bios=[]
    for irq in range(1,301):
        observed=original.run_irq(phase,counter)
        expected=irq_phase(phase,counter)
        assert observed==expected
        if observed[1]!=counter:ticks.append(irq)
        if observed[2]:bios.append(irq)
        phase,counter,_=observed
    assert len(ticks)==60 and len(bios)==30
    assert all(b-a==5 for a,b in zip(ticks,ticks[1:]))
    report={'verified':True,'cases':cases+300,'phase_boundary_cases':cases,'stream_irqs':300,
            'stream_game_ticks':counter,'stream_bios_chains':len(bios),'first_game_tick_irqs':ticks[:12],
            'pit_hz':PIT_HZ,'pit_divisor':PIT_DIVISOR,'irq_hz':IRQ_HZ,'physics_hz':TICK_HZ,
            'tick_seconds':TICK_SECONDS,'result_stream_sha256':digest.hexdigest(),
            'exe_sha256':hashlib.sha256((OUT/'unpacked/SKYROADS_UNPACKED.EXE').read_bytes()).hexdigest(),
            'clock_source':'https://github.com/dosbox-staging/dosbox-staging/blob/main/src/hardware/timer.h',
            'limitations':['OUT captured in virtual hooks; no physical hardware timing measured.',
                           'Audio helper runs its idle delay branch; audio stream processing excluded.',
                           'Stops before chaining old BIOS handler; verifies restored registers and chain decision.']}
    (OUT/'timer-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
