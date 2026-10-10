#!/usr/bin/env python3
"""Decode original samples and execute the original AdLib sequencer to port writes.

Only IN/OUT hardware is virtualized; original 5880..5a96 instructions execute.
Music IRQ cadence comes from the recovered PIT divisor. Source files are read-only.
"""
import hashlib,importlib.util,json,struct,wave
from pathlib import Path
from unicorn import UC_HOOK_INSN
from unicorn.x86_const import UC_X86_INS_IN,UC_X86_INS_OUT
from skyroads_lzs import decode
from skyroads_timer import IRQ_HZ,PIT_HZ,PIT_DIVISOR
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads/audio';OUT.mkdir(exist_ok=True)
SOURCE=ROOT/'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10'
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=importlib.util.spec_from_file_location('audio_fixture',ROOT/'scripts/validate-skyroads-collision.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
class Player(fixture.Original):
 def __init__(self):
  super().__init__(allowed=[(0x5892,0x5a97)])
  self.irq=0;self.events=[];self.register=0;self.loops=[];self.marks=[]
  self.uc.hook_add(UC_HOOK_INSN,lambda *args:0,None,1,0,UC_X86_INS_IN)
  self.uc.hook_add(UC_HOOK_INSN,self.port,None,1,0,UC_X86_INS_OUT)
 def port(self,uc,port,size,value,user):
  assert size==1 and port in (0x388,0x389),(port,size)
  if port==0x388:self.register=value
  else:self.events.append([self.irq,self.register,value])
 def code(self,uc,address,size,user):
  if address==fixture.BASE+0x5a42:self.loops.append(self.irq)
  if address==fixture.BASE+0x5a49:self.marks.append(self.irq)
  super().code(uc,address,size,user)

def wav(name,data,rate):
 with wave.open(str(OUT/name),'wb') as w:w.setnchannels(1);w.setsampwidth(1);w.setframerate(rate);w.writeframes(data)

def main():
 sources={n:sha((SOURCE/n).read_bytes()) for n in ['MUZAX.LZS','SFX.SND','INTRO.SND']}
 b=(SOURCE/'SFX.SND').read_bytes();offsets=struct.unpack_from('<6H',b);assert offsets[0]==12 and offsets[-1]==len(b)
 effects=[]
 for i,(a,z) in enumerate(zip(offsets,offsets[1:])):
  time_constant=b[a];effective=min(time_constant,234);rate=1000000//(256-effective);data=b[a+1:z];name=f'effect-{i}.wav';wav(name,data,rate)
  effects.append({'index':i,'file':name,'source_offset':a,'source_end':z,'time_constant':time_constant,
   'sample_rate':rate,'effective_time_constant':effective,'requested_sample_rate':1000000/(256-time_constant),
   'exact_sample_rate':1000000/(256-effective),'samples':len(data),'pcm_sha256':sha(data),'wav_sha256':sha((OUT/name).read_bytes())})
 intro=(SOURCE/'INTRO.SND').read_bytes();wav('intro.wav',intro,round(1000000/(256-90)))
 b=(SOURCE/'MUZAX.LZS').read_bytes();tracks=[]
 for i in range(10):
  offset,instruments,length=struct.unpack_from('<3H',b,i*6);decoded=decode(b[offset:],length)
  assert offset+decoded.consumed_bytes==(struct.unpack_from('<H',b,(i+1)*6)[0] if i<9 else len(b))
  (OUT/f'track-{i}.bin').write_bytes(decoded.data)
  player=Player();player.call(0x58cd,[]);player.uc.mem_write(fixture.STACK+0x54b0,decoded.data)
  player.uc.mem_write(fixture.STACK+0xc83,b'\0');player.call(0x5a7d,[0x54b0+instruments*16,0x54b0])
  for irq in range(100000):
   player.irq=irq;player.call(0x5a55,[])
   if player.loops:break
  else:raise AssertionError('Music did not loop')
  # One call every original IRQ. Delays decrement in the same call that sets
  # them, so event timestamps must come from executed code rather than sums.
  events=player.events;binary=b''.join(struct.pack('<IBB',*event) for event in events)
  (OUT/f'track-{i}.opl').write_bytes(binary)
  track={'index':i,'source_offset':offset,'instrument_paragraphs':instruments,'decoded_length':length,'decoded_sha256':sha(decoded.data),
   'events':len(events),'events_file':f'track-{i}.opl','events_sha256':sha(binary),'loop_end_irq':player.loops[0],
   'loop_start_irq':player.marks[-1] if player.marks else 0,'duration_seconds':player.loops[0]/IRQ_HZ}
  tracks.append(track);print(json.dumps(track),flush=True)
 manifest={'format':'skyroads-audio-v1','source_sha256':sources,'music_irq_hz':IRQ_HZ,'pit_hz':PIT_HZ,'pit_divisor':PIT_DIVISOR,
  'effects':effects,'tracks':tracks,'intro':{'file':'intro.wav','samples':len(intro),'sample_rate':round(1000000/(256-90)),'time_constant':90,'rate_verified':True},
  'extractor_sha256':sha(Path(__file__).read_bytes()),'original_module_sha256':sha((ROOT/'analysis/skyroads/runtime-load-image.bin').read_bytes()),
  'limits':['Music port writes execute original code with virtualized hardware; native full-game comparison is separate.',
   'Intro sample rate is verified by native sample_arguments; intro is not wired to gameplay.',
   'Digital playback follows the native SB16 reference: time constant capped at 234 and integer-Hz DSP rate, per pinned DOSBox-X sblaster.cpp.']}
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 assert all(sha((SOURCE/n).read_bytes())==h for n,h in sources.items())
 print('Extracted five original digital effects and ten original AdLib score streams.',flush=True)
if __name__=='__main__':main()
