#!/usr/bin/env python3
"""Check original DSP requests and full-game native OPL stream observations."""
import hashlib,importlib.util,json,struct,sys,wave
from pathlib import Path
from unicorn import UC_HOOK_INSN
from unicorn.x86_const import UC_X86_INS_IN,UC_X86_INS_OUT,UC_X86_REG_SP
from skyroads_tick import TickState,TickConfig,TickInput,tick
from skyroads_session import Catalog
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads';A=OUT/'audio'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((A/'manifest.json').read_text())
assert sha(ROOT/'scripts/extract-skyroads-audio.py')==meta['extractor_sha256']
assert sha(ROOT/'scripts/render-skyroads-audio.py')==meta['synthesizer']['renderer_sha256']
for name,h in meta['synthesizer']['source_sha256'].items():
 assert sha(ROOT/'tools/dosbox-x/src/hardware'/name)==h
for track in meta['tracks']:
 assert sha(A/track['file'])==track['audio_sha256']
 assert sha(A/f"track-{track['index']}.bin")==track['decoded_sha256']
spec=importlib.util.spec_from_file_location('audio_fixture',ROOT/'scripts/validate-skyroads-collision.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
class Effects(fixture.Original):
 def __init__(self):
  super().__init__(allowed=[(0x3c2,0x476),(0x5b39,0x5bdb)])
  self.ports=[];self.arguments=[]
  self.uc.hook_add(UC_HOOK_INSN,lambda *args:0,None,1,0,UC_X86_INS_IN)
  self.uc.hook_add(UC_HOOK_INSN,lambda u,p,s,v,d:self.ports.append([p,v]),None,1,0,UC_X86_INS_OUT)
 def code(self,uc,address,size,user):
  if address==fixture.BASE+0x5b76:self.arguments.append(list(struct.unpack('<4H',uc.mem_read(fixture.STACK+uc.reg_read(UC_X86_REG_SP)+2,8))))
  super().code(uc,address,size,user)
original=Effects();source=ROOT/'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10'
for n,h in meta['source_sha256'].items():assert sha(source/n)==h
sample_bytes=(source/'SFX.SND').read_bytes();original.uc.mem_write(0x30000,sample_bytes)
for at,value in [(0x4560,0x3000),(0xcb6,0x220),(0xcb8,1),(0x451a,0),(0x1600,123)]:original.uc.mem_write(fixture.STACK+at,struct.pack('<H',value))
effect_cases=[]
for e in meta['effects']:
 assert e['effective_time_constant']==min(e['time_constant'],234)
 assert e['sample_rate']==1000000//(256-e['effective_time_constant'])
 original.ports=[];original.arguments=[];original.call(0x3c2,[e['index']]);args=original.arguments[0]
 assert args==[e['source_offset']+1,0x3000,e['time_constant'],e['samples']]
 dsp=[v for p,v in original.ports if p==0x22c]
 assert dsp==[0xd0,0x40,e['time_constant'],0x14,(e['samples']-1)&255,(e['samples']-1)>>8]
 with wave.open(str(A/e['file']),'rb') as w:
  assert w.getnchannels()==w.getsampwidth()==1 and w.getframerate()==e['sample_rate']
  assert w.readframes(w.getnframes())==sample_bytes[e['source_offset']+1:e['source_end']]
 assert sha(A/e['file'])==e['wav_sha256']
 effect_cases.append({'effect':e['index'],'original_sample_arguments':args,'dsp_bytes':dsp,'pcm_match':True})
runs=[];seen=set();writes=0;native_requests=[];decoded_files=set();native_sound_ticks=0;catalog=Catalog()
for runName in sys.argv[1:]:
 run=Path(runName);events=[json.loads(l) for l in (run/'trace.jsonl').read_text().splitlines()];m=json.loads((run/'manifest.json').read_text())
 assert m['exit_code']==0 and m['original_files_unchanged'] and m['audio_observation'] and not m['guest_program_patched']
 for name,key in [('probe-source.h','probe_sha256'),('runner-source.py','runner_sha256'),('dosbox.conf','config_sha256'),('emulator-build.json','build_manifest_sha256')]:assert sha(run/name)==m[key]
 assert all(sha(Path(m['source'])/n)==h for n,h in m['source_sha256'].items())
 starts=[(i,e) for i,e in enumerate(events) if e['kind']=='music_start'];segments=[]
 for k,(i,start) in enumerate(starts):
  track=meta['tracks'][start['score']];assert start['length']==track['decoded_length']
  matching=list(run.glob(f"trace.jsonl.attempt-*.music-{start['score']}.bin"));assert matching
  for f in matching:assert sha(f)==track['decoded_sha256'];decoded_files.add(str(f))
  end=starts[k+1][0] if k+1<len(starts) else len(events)
  actual=[e for e in events[i+1:end] if e['kind']=='opl' and e['score']==start['score']]
  b=(A/track['events_file']).read_bytes();assert hashlib.sha256(b).hexdigest()==track['events_sha256']
  oracle=[struct.unpack_from('<IBB',b,p) for p in range(0,len(b),6)]
  # The first 63 writes initialize the chip before loading any score. A new
  # score inherits the preceding stream's remaining delay byte in native RAM.
  assert oracle[62]==(0,0xb7,0x0d);oracle=oracle[63:]
  assert len(actual)<=len(oracle)
  for n,e in enumerate(actual):
   value=(e['score_irq']-start['delay']-1,e['register'],e['value'])
   assert value==oracle[n],(run.name,start['score'],n,value,oracle[n])
  if actual:seen.add(start['score'])
  writes+=len(actual);segments.append({'score':start['score'],'writes_match':len(actual),'initial_delay_irqs':start['delay']})
 pending_sounds=None;road_index=None
 for e in events:
  if e['kind']=='initial':road_index=0 if e['mode']==3 else e['selected']+1
  elif e['kind']=='tick_before':
   observed=[];tick(catalog.bytes[road_index],TickState(**e['state']),TickConfig(*e['config']),
    TickInput(e['throttle'],e['direction'],e['jump'],e['timer']),observer=lambda x:observed.append(x))
   pending_sounds=[x[1] for x in observed if x[0]=='sound']
  elif e['kind']=='sound_request' and pending_sounds is not None:
   assert pending_sounds and pending_sounds.pop(0)==e['arg0'];native_sound_ticks+=1
  elif e['kind'] in ('tick_after','finish_start'):
   assert pending_sounds==[];pending_sounds=None
  if e['kind']=='sample_arguments':
   if e['offset']==0 and e['length']==meta['intro']['samples']:
    assert e['constant']==meta['intro']['time_constant'];index='intro'
   else:index=next(x['index'] for x in meta['effects'] if x['time_constant']==e['constant'] and x['samples']==e['length'])
   native_requests.append({'run':run.name,'effect':index,'ms':e['ms']})
 runs.append({'run':run.name,'trace_sha256':sha(run/'trace.jsonl'),'manifest_sha256':sha(run/'manifest.json'),'segments':segments})
assert seen==set(range(10)),('Native score coverage incomplete',seen)
report={'verified':True,'original_dsp_effects':effect_cases,'native_music_tracks':sorted(seen),'native_opl_writes_match':writes,
 'native_decoded_assets_checked':len(decoded_files),'native_tick_sound_requests_match':native_sound_ticks,
 'native_sample_requests':native_requests,'runs':runs,'audio_manifest_sha256':sha(A/'manifest.json'),
 'limits':['Native score comparisons cover observed continuous prefixes; complete score loops execute the original isolated sequencer.',
  'Music uses pre-rendered DBOPL OPL2, not physical Yamaha chip/DAC output; looped PCM repeats noise/envelope state.',
  'Browser/OS output latency and perceptual loudness require separate measurement.']}
(OUT/'audio-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('runs','original_dsp_effects')},indent=2))
