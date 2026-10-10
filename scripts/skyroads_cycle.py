"""Original gameplay scheduling around the unchanged, verified integer tick.

An advance releases ONE original timer wait, not a rendering frame. Input at
that boundary is decoded before catch-up ticks; P/Escape are checked at the
following outer-loop boundary. Graphics are replaceable; HUD sound writes are
preserved. Uninitialized stack words have explicit canonical seeds.
"""
from dataclasses import asdict
import hashlib
from skyroads_tick import TickState, TickInput, tick
from skyroads_movement import u32
from skyroads_collision import u16
from skyroads_session import ROOT

SCANS = (0x48,0x50,0x4b,0x4d,0x47,0x49,0x4f,0x51,0x01,0x39,0x19)
ESCAPE, PAUSE = 1 << 8, 1 << 10
UNDEFINED = ('jump_height','edge_distance','previous_target_height')


def decode_keyboard(mask):
    if type(mask) is not int or not 0 <= mask < 2048:
        raise ValueError('Expected an eleven-key mask')
    def held(*indices): return int(any(mask & (1 << i) for i in indices))
    return {'throttle':held(0,4,5)-held(1,6,7),
            'direction':held(3,5,7)-held(2,4,6),'jump':held(9)}


def initial_state(seeds=None):
    return TickState(**{name:u16((seeds or {}).get(name,0)) for name in UNDEFINED})


class Attempt:
    def __init__(self,road,config,seeds=None):
        self.road=road; self.config=config; self.state=initial_state(seeds)
        self.timer=0; self.phase='playing'; self.result=None
        self.blink=0; self.pause_timer=0

    def snapshot(self):
        return {'state':asdict(self.state),'timer':self.timer,'phase':self.phase,
                'result':self.result,'blink':self.blink,'pause_timer':self.pause_timer}

    def prepare(self,mask,events):
        s=self.state
        if self.timer < s.tick_counter:
            self.timer=s.tick_counter=0
        self.pause_timer=self.timer
        if mask & PAUSE:
            self.phase='pause_release'; self.pause_timer=self.timer
            events.append(('pause',))
            return
        self.gate(mask,events)

    def gate(self,mask,events):
        s=self.state
        if mask & ESCAPE:
            self.finish(7,events); return
        if (s.crash_ticks==0 or s.crash_ticks>42) and (
            s.exit_state in (1,2) or (s.exit_state==3 and s.crash_ticks!=0) or s.end_ticks>=108):
            self.finish(s.exit_state,events); return
        # 12f8: only the resource flash's sound timestamp affects gameplay.
        blink=int(self.timer % 9 > 4)
        if s.exit_state in (4,5) and blink!=self.blink and blink:
            events.append(('sound',3)); s.sound_tick=self.timer
        self.blink=blink; self.phase='playing'

    def finish(self,result,events):
        self.result=result; self.phase='returned'; events.append(('return',result))

    def advance(self,mask,elapsed=1,observer=None):
        decode_keyboard(mask)
        minimum=0 if self.phase.startswith('pause_') else 1
        if type(elapsed) is not int or not minimum<=elapsed<=1024: raise ValueError('Invalid elapsed timer ticks')
        events=[]
        if self.phase=='returned': return events
        self.timer=u16(self.timer+elapsed)
        if self.phase.startswith('pause_'):
            if self.phase=='pause_release' and not mask & PAUSE: self.phase='pause_press'
            if self.phase=='pause_press' and mask:
                if mask & ESCAPE: self.finish(7,events)
                else: self.phase='pause_clear'
            if self.phase=='pause_clear' and not mask:
                self.timer=self.pause_timer; self.phase='playing'
                events.append(('resume',)); self.gate(0,events)
        elif self.phase=='finishing':
            self.state.forward=u32(self.state.forward+self.state.speed)
            events.append(('finish_frame',))
            if self.timer>=72: self.finish(0,events)
            elif mask & ESCAPE: self.finish(7,events)
        else:
            controls=decode_keyboard(mask)
            while self.state.tick_counter < self.timer:
                result=tick(self.road,self.state,self.config,TickInput(**controls,timer=self.timer),observer=events.append)
                self.state=result.state
                if result.completion_requested:
                    self.state.height=0; self.timer=0; self.phase='finishing'
                    if mask & ESCAPE: self.finish(7,events)
                    break
            if self.phase=='playing': self.prepare(mask,events)
        if observer is not None:
            for event in events: observer(event)
        return events


MODEL_FILES=('skyroads_cycle.py','skyroads_tick.py','skyroads_movement.py',
             'skyroads_collision.py','skyroads_timer.py','skyroads-geometry.js',
             'skyroads-physics.js','skyroads-cycle.js','skyroads-ui.js','skyroads-presentation.js')


def identity():
    return {name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in MODEL_FILES}


class Game:
    """RunRoadSession/main caller: automatic retry, success notice, selection.

    Notice input is an explicit BIOS-buffer flag (the original helper4153),
    independent of the gameplay keyboard IRQ's held bits.
    """
    def __init__(self,catalog,index=1,assist=True,completed=None):
        self.catalog=catalog; self.index=index; self.assist=assist
        self.completed=list(completed or [0]*30)
        if len(self.completed)!=30: raise ValueError('Expected thirty completion counters')
        self.completed=[u16(n) for n in self.completed]
        self.initial_completed=self.completed[:]
        self.attempt_number=1; self.phase='attempt'; self.notice_ticks=0
        self.selected=index-1 if index else 0; self.last_road=False
        self.attempt=Attempt(catalog.bytes[index],catalog.config(index,assist))
        self.samples=[]

    def snapshot(self):
        return {'road_index':self.index,'attempt_number':self.attempt_number,
                'game_phase':self.phase,'notice_ticks':self.notice_ticks,
                'selected':self.selected,'completed':self.completed[:],
                'last_road':self.last_road,**self.attempt.snapshot()}

    def advance(self,mask,elapsed=1,notice_key=False):
        if len(self.samples)>=20000: raise ValueError('Recording limit reached')
        decode_keyboard(mask)
        minimum=0 if self.phase=='attempt' and self.attempt.phase.startswith('pause_') else 1
        if type(elapsed) is not int or not minimum<=elapsed<=1024: raise ValueError('Invalid elapsed timer ticks')
        if type(notice_key) is not bool: raise ValueError('Invalid notice key')
        events=[]
        if self.phase=='notice':
            self.notice_ticks=u16(self.notice_ticks+elapsed)
            if self.notice_ticks>=27 or notice_key:
                # Main01b8 increments after the wrapper's completion notice.
                if self.index:
                    self.completed[self.index-1]=u16(self.completed[self.index-1]+1)
                    self.selected=self.index  # picker clamps30 back to29.
                self.phase='selection'; events.append(('selection',self.selected))
        elif self.phase=='attempt':
            events=self.attempt.advance(mask,elapsed)
            if self.attempt.result is not None:
                result=self.attempt.result
                if result==0:
                    self.last_road=bool(self.index and self.completed[self.index-1]==0 and
                                        sum(n!=0 for n in self.completed)==29)
                    self.phase='notice'; self.notice_ticks=0; events.append(('notice',int(self.last_road)))
                elif result==7 or self.index==0:
                    self.phase='selection'; events.append(('selection',self.selected))
                else:
                    seeds={n:getattr(self.attempt.state,n) for n in UNDEFINED}
                    self.attempt=Attempt(self.catalog.bytes[self.index],self.catalog.config(self.index,self.assist),seeds)
                    self.attempt_number+=1; events.append(('restart',self.attempt_number))
        sample={'frame':len(self.samples),'input':{'mask':mask,'elapsed':elapsed,'notice_key':notice_key},
                'snapshot':self.snapshot(),'events':[list(e) for e in events if e[0] in
                    ('sound','finish','finish_frame','pause','resume','return','restart','notice','selection')]}
        self.samples.append(sample); return sample

    def recording(self):
        return {'format':'skyroads-cycle-v2','road_index':self.index,'assist':self.assist,
                'road_sha256':self.catalog.roads[self.index]['decoded_sha256'],
                'model_sha256':identity(),'initial_completed':self.initial_completed,
                'samples':self.samples,'final':self.snapshot()}


def replay(catalog,recording):
    if recording.get('format')!='skyroads-cycle-v2': raise ValueError('Unknown recording format')
    if recording['model_sha256']!=identity(): raise ValueError('Recording model identity differs')
    index=recording['road_index']
    if recording['road_sha256']!=catalog.roads[index]['decoded_sha256']: raise ValueError('Road identity differs')
    game=Game(catalog,index,recording['assist'],recording['initial_completed'])
    frames=[game.snapshot()]
    for number,sample in enumerate(recording['samples']):
        actual=game.advance(**sample['input'])
        if actual!=sample: raise ValueError(f'Cycle replay mismatch at frame {number}')
        frames.append(actual['snapshot'])
    if game.snapshot()!=recording['final']: raise ValueError('Final snapshot differs')
    return {'verified':True,'frames':frames,'ticks':len(game.samples),'final':game.snapshot()}
