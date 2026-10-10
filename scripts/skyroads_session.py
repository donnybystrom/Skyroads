"""Deterministic sessions around the verified integer tick, shared by UI/CLI."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from skyroads_tick import TickState, TickConfig, TickInput, tick
from skyroads_timer import TICK_HZ, TICK_SECONDS, PIT_HZ, PIT_DIVISOR

ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / 'analysis/skyroads'
MODEL_FILES = ('skyroads_tick.py','skyroads_movement.py','skyroads_collision.py','skyroads_timer.py','skyroads_session.py')


def model_identity():
    return {name:hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest() for name in MODEL_FILES}


class Catalog:
    def __init__(self):
        self.manifest=json.loads((ANALYSIS/'roads/manifest.json').read_text())
        self.roads={r['index']:r for r in self.manifest['roads']}
        self.bytes={i:(ANALYSIS/'roads'/r['decoded_file']).read_bytes() for i,r in self.roads.items()}
        for i,r in self.roads.items():
            assert hashlib.sha256(self.bytes[i]).hexdigest()==r['decoded_sha256']
        verification=json.loads((ANALYSIS/'tick-validation.json').read_text())
        assert verification['verified']
        for name in ('skyroads_tick.py','skyroads_movement.py','skyroads_collision.py'):
            assert model_identity()[name]==verification['code_sha256'][name]

    def config(self,index,assist=True):
        r=self.roads[index]
        return TickConfig(*r['metadata_words'],len(self.bytes[index])//14,int(assist))


class Session:
    def __init__(self,catalog,index=0,assist=True):
        self.catalog=catalog;self.index=index
        self.config=catalog.config(index,assist)
        self.initial=TickState();self.state=TickState()
        self.samples=[];self.completion=False

    @property
    def stopped(self):
        return bool(self.completion or self.state.exit_state)

    def step(self,throttle=0,direction=0,jump=0):
        if self.stopped:return None
        if len(self.samples)>=20000:raise ValueError('Recording limit reached; reset the session')
        if type(throttle)!=int or throttle not in (-1,0,1):raise ValueError('Invalid throttle')
        if type(direction)!=int or direction not in (-1,0,1):raise ValueError('Invalid direction')
        if type(jump)!=int or jump not in (0,1):raise ValueError('Invalid jump')
        number=len(self.samples)
        controls=TickInput(throttle,direction,jump,(number+1)&65535)
        events=[]
        result=tick(self.catalog.bytes[self.index],self.state,self.config,controls,observer=events.append)
        self.state=result.state;self.completion=result.completion_requested
        sample={'tick':number,'input':asdict(controls),'state':asdict(self.state),
                'completion_requested':self.completion,
                'events':[list(e) for e in events if e[0] in ('resolve','sound','finish')]}
        self.samples.append(sample)
        return sample

    def snapshot(self):
        return {'road_index':self.index,'state':asdict(self.state),'ticks':len(self.samples),
                'elapsed_seconds':len(self.samples)*TICK_SECONDS,'stopped':self.stopped,
                'completion_requested':self.completion}

    def recording(self):
        return {'format':'skyroads-session-v1','road_index':self.index,
                'road_sha256':self.catalog.roads[self.index]['decoded_sha256'],
                'model_sha256':model_identity(),'config':asdict(self.config),'initial_state':asdict(self.initial),
                'clock':{'pit_hz':PIT_HZ,'pit_divisor':PIT_DIVISOR,'physics_hz':TICK_HZ},
                'timer_rule':'input timer=(zero-based sample index+1)&65535; fixed during each tick',
                'samples':self.samples,'final':self.snapshot()}


def replay(catalog,recording):
    if recording.get('format')!='skyroads-session-v1':raise ValueError('Unknown recording format')
    if recording['model_sha256']!=model_identity():raise ValueError('Recording model identity differs')
    index=recording['road_index']
    if recording['road_sha256']!=catalog.roads[index]['decoded_sha256']:raise ValueError('Road identity differs')
    cfg=TickConfig(**recording['config']);state=TickState(**recording['initial_state'])
    frames=[asdict(state)]
    for sample in recording['samples']:
        events=[]
        result=tick(catalog.bytes[index],state,cfg,TickInput(**sample['input']),observer=events.append)
        assert asdict(result.state)==sample['state'],f"State mismatch at tick{sample['tick']}"
        assert result.completion_requested==sample['completion_requested']
        filtered=[list(e) for e in events if e[0] in ('resolve','sound','finish')]
        assert filtered==sample['events'],f"Event mismatch at tick{sample['tick']}"
        state=result.state;frames.append(asdict(state))
    assert asdict(state)==recording['final']['state']
    return {'verified':True,'ticks':len(recording['samples']),'frames':frames,'final_state':asdict(state)}
