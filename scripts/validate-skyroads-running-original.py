#!/usr/bin/env python3
"""Compare continuous full-DOSBox traces to the existing Python/JS models.

The guest executable, BIOS/DOS calls, IRQs, rendering and files all execute.
Only the three documented unspecified initial stack words are calibrated in
one model. A second model keeps the clone's canonical/retry seeds and checks
all other state, without resetting it to observed state between ticks.
"""
import argparse,hashlib,json
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from skyroads_cycle import Attempt,Game,UNDEFINED,decode_keyboard,identity
from skyroads_tick import TickConfig,TickInput,tick
from skyroads_session import Catalog
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads'
p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path)
p.add_argument('--output-dir',type=Path,help='Keep a new comparison separate from the archived reference reports')
args=p.parse_args()
if args.output_dir:OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)
catalog=Catalog();counts=Counter();reports=[];corpus=[]
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def same(expected,actual,label,ignore=()):
 diff={k:{'model':v,'original':actual.get(k)} for k,v in expected.items() if k not in ignore and v!=actual.get(k)}
 if diff:raise AssertionError(json.dumps({'boundary':label,'first_difference':diff},indent=2))
def check_first_retry(ops,gaps):
 """Drive the actual Game API until its first premature restart is observed.

 This records a discrepancy, not a passing whole-game equivalence test. The
 existing Game consumes the same timer deltas and held-key masks as the guest.
 """
 first=next(op for op in ops if op['kind']=='initial')
 if first['road_index']==0 or not gaps:return None
 game=Game(catalog,first['road_index']);ticks=0;sample=None
 for op in ops:
  if op['kind']=='tick':
   old=game.attempt;elapsed=(op['input']['timer']-old.timer)&65535
   sample=game.advance(op['mask'],elapsed)
   same(asdict(old.state),op['after'],'actual-Game/before-retry',UNDEFINED);ticks+=1
  elif op['kind']=='pause_poll':sample=game.advance(op['mask'],op['elapsed'])
  elif op['kind']=='return':
   assert op['result'] not in (0,7) and game.attempt_number==2
   assert ['return',op['result']] in sample['events'] and ['restart',2] in sample['events']
   return {'whole_game_equal':False,'compared_physics_ticks_before_difference':ticks,
           'original_return_reason':op['result'],'clone_attempt_number_at_original_return':game.attempt_number,
           'clone_events':sample['events'],'original_ms_until_next_initial':gaps[0]['native_ms'],
           'difference':'Game has already initialized attempt 2 at the boundary where the original only returns from attempt 1; original wrapper transitions still follow.'}
 raise AssertionError('Missing first retry return')
for run in args.runs:
 events=[json.loads(l) for l in (run/'trace.jsonl').read_text().splitlines()];manifest=json.loads((run/'manifest.json').read_text())
 assert manifest['exit_code']==0 and manifest['original_files_unchanged'] and not manifest['guest_program_patched']
 assert sha(run/'dosbox.conf')==manifest['config_sha256']
 assert sha(run/'probe-source.h')==manifest['probe_sha256']
 if 'build_manifest_sha256' in manifest:assert sha(run/'emulator-build.json')==manifest['build_manifest_sha256']
 if (run/'runner-source.py').exists():assert sha(run/'runner-source.py')==manifest['runner_sha256']
 assert all(sha(run/'drive-c'/name)==value for name,value in manifest['output_sha256'].items())
 assert all(sha(Path(manifest['source'])/name)==value for name,value in manifest['source_sha256'].items())
 assert events[-1]['kind']=='stop' and events[-1]['sessions']>=manifest.get('requested_sessions',1),'Incomplete original run'
 model=canonical=None;pending=None;polled=0;attempt=None;previous_return=None;profile_before=None;finish=False;notice=None;fade=None
 totals=Counter();attempts=[];gaps=[];fade_intervals=[];notice_intervals=[];ops=[]
 for e in events:
  kind=e['kind'];label=f'{run.name}/{e.get("attempt",0)}/{e.get("tick",0)}/{kind}'
  if kind=='initial':
   number=e['attempt'];road=(run/f'trace.jsonl.attempt-{number}.road.bin').read_bytes()
   indices=[i for i,b in catalog.bytes.items() if b==road]
   index=0 if e['mode']==3 else e['selected']+1
   assert index in indices;cfg=TickConfig(*e['config']);assert cfg==catalog.config(index)
   demo=(run/f'trace.jsonl.attempt-{number}.demo.bin').read_bytes()
   if e['mode']==3:assert sha(run/f'trace.jsonl.attempt-{number}.demo.bin')==manifest['source_sha256']['DEMO.REC']
   seeds={k:e['state'][k] for k in UNDEFINED};old=canonical
   model=Attempt(road,cfg,seeds);canonical=Attempt(road,cfg,{k:getattr(old.state,k) for k in UNDEFINED} if old and previous_return and previous_return['ax'] not in (0,7) else None)
   same(asdict(model.state),e['state'],label);same(asdict(canonical.state),e['state'],label+'/canonical',UNDEFINED)
   attempt={'attempt':number,'road_index':index,'mode':e['mode'],'start_ms':e['ms'],'initial_stack_seeds':seeds,'ticks':0,'finish_frames':0}
   attempts.append(attempt);finish=False;pending=None;ops.append({'kind':'initial','config':asdict(cfg),'road_index':index,'seeds':seeds,'state':e['state']})
   if previous_return and previous_return['ax'] not in (0,7):gaps.append({'after_attempt':previous_return['attempt'],'before_attempt':number,'native_ms':round(e['ms']-previous_return['ms'],6),'clone_restart_delay_ticks':0})
   totals['initializers']+=1
  elif kind=='input_poll':polled=e['mask'];totals['polls']+=1
  elif kind=='tick_before':
   same(asdict(model.state),e['state'],label+'/before');same(asdict(canonical.state),e['state'],label+'/canonical-before',UNDEFINED)
   if e['mode']==3:
    def decode_demo(state):
     address=state.forward//0x666;assert 0<=address<len(demo);b=demo[address]
     return {'throttle':(b&3)-1,'direction':((b>>2)&3)-1,'jump':(b>>4)&1}
    controls=decode_demo(model.state);assert controls==decode_demo(canonical.state)
   else:controls=decode_keyboard(polled)
   assert controls=={k:e[k] for k in ('throttle','direction','jump')},label+'/independent-input'
   controls={**controls,'timer':e['timer']}
   pending=tick(road,model.state,cfg,TickInput(**controls));cp=tick(road,canonical.state,cfg,TickInput(**controls));pending_canonical=cp
   pending_op={'kind':'tick','input':controls,'before':e['state'],'mask':polled,'mode':e['mode']}
   totals['input_samples']+=1
  elif kind=='tick_after':
   assert pending and not pending.completion_requested
   same(asdict(pending.state),e['state'],label);same(asdict(pending_canonical.state),e['state'],label+'/canonical',UNDEFINED)
   model.state=pending.state;canonical.state=pending_canonical.state
   ops.append({**pending_op,'after':e['state'],'completion':False});pending=None
   totals['physics_ticks']+=1;attempt['ticks']+=1
  elif kind=='outer':
   same(asdict(model.state),e['state'],label);same(asdict(canonical.state),e['state'],label+'/canonical',UNDEFINED)
   for m in (model,canonical):m.timer=e['timer'];m.prepare(e['mask'],[])
   ops.append({'kind':'gate','timer':e['timer'],'mask':e['mask'],'before':e['state']});totals['outer_boundaries']+=1
  elif kind in ('pause_release','pause_press','pause_clear'):
   same(asdict(model.state),e['state'],label)
   if model.phase.startswith('pause_'):
    elapsed=(e['timer']-model.timer)&65535
    for m in (model,canonical):m.advance(e['mask'],elapsed)
    ops.append({'kind':'pause_poll','mask':e['mask'],'elapsed':elapsed,'state':e['state']})
    totals['pause_polls']+=1
  elif kind=='pause_resume':
   if model.phase.startswith('pause_'):
    elapsed=(e['timer']-model.timer)&65535
    for m in (model,canonical):m.advance(e['mask'],elapsed)
    ops.append({'kind':'pause_poll','mask':e['mask'],'elapsed':elapsed,'state':e['state']});totals['pause_polls']+=1
   assert model.phase=='playing' and model.timer==e['saved_timer'],label
   same(asdict(model.state),e['state'],label);totals['pause_resumes']+=1
   ops.append({'kind':'resume_check','timer':e['saved_timer'],'state':e['state']})
  elif kind=='finish_start':
   assert pending.completion_requested and pending_canonical.completion_requested
   same(asdict(pending.state),e['state'],label);same(asdict(pending_canonical.state),e['state'],label+'/canonical',UNDEFINED)
   ops.append({**pending_op,'after':e['state'],'completion':True});pending=None
   for m in (model,canonical):m.timer=m.state.tick_counter;m.advance(0,(e['timer']-m.timer)&65535)
   assert model.phase=='finishing';ops.append({'kind':'finish_start','state':asdict(model.state)})
   finish=True;totals['completion_requests']+=1
  elif kind=='finish_after':
   assert finish
   elapsed=(e['timer']-model.timer)&65535
   if elapsed:
    for m in (model,canonical):m.advance(e['mask'],elapsed)
    attempt['finish_frames']+=1;totals['finish_frames']+=1
   same(asdict(model.state),e['state'],label);same(asdict(canonical.state),e['state'],label+'/canonical',UNDEFINED)
   ops.append({'kind':'finish_after','elapsed':elapsed,'mask':e['mask'],'state':e['state'],'timer':e['timer']})
  elif kind=='attempt_return':
   for m in (model,canonical):
    if m.phase!='returned':m.timer=e['timer'];m.gate(e['mask'],[])
    assert m.result==e['ax'],label+'/reason'
   same(asdict(model.state),e['state'],label);same(asdict(canonical.state),e['state'],label+'/canonical',UNDEFINED)
   previous_return=e;attempt.update(result=e['ax'],end_ms=e['ms'],final=e['state'])
   ops.append({'kind':'return','mask':e['mask'],'timer':e['timer'],'result':e['ax'],'state':e['state']});totals['attempt_returns']+=1
  elif kind=='session_return':
   assert previous_return and previous_return['ax']==e['ax'];profile_before=e
   totals['session_returns']+=1
  elif kind in ('retry_branch','selection_branch') and profile_before:
   result=previous_return['ax'];expected=profile_before['completed'][:];selected=profile_before['selected']
   if result==0:expected[selected]=(expected[selected]+1)&65535;selected+=1
   assert e['completed']==expected and e['selected']==selected
   assert (kind=='retry_branch')==(result not in (0,7))
   totals[kind]+=1;profile_before=None
  elif kind=='fade_start':fade=e
  elif kind=='fade_return' and fade:
   fade_intervals.append({'attempt':e['attempt'],'direction':fade['arg1'],'duration_argument':fade['arg2'],'native_ms':round(e['ms']-fade['ms'],6)});fade=None
  elif kind=='notice_start' and previous_return and previous_return['ax']==0:notice=e
  elif kind=='notice_return' and notice:
   assert e['timer']>=notice.get('arg0',27);notice_intervals.append({'target_ticks':notice.get('arg0',27),'return_timer':e['timer'],'native_ms':round(e['ms']-notice['ms'],6)});notice=None
 assert pending is None
 # Profile writes occur in the copied C: drive, never in the source folder.
 changed=[n for n,h in manifest['source_sha256'].items() if manifest['output_sha256'].get(n)!=h]
 source_cfg=(Path(manifest['source'])/'SKYROADS.CFG').read_bytes();output_cfg=(run/'drive-c/SKYROADS.CFG').read_bytes()
 assert len(source_cfg)==len(output_cfg)
 cfg_changes=[{'offset':i,'before':a,'after':b} for i,(a,b) in enumerate(zip(source_cfg,output_cfg)) if a!=b]
 report={'run':run.name,'counts':dict(totals),'attempts':attempts,'retry_gaps':gaps,'actual_game_first_retry_comparison':check_first_retry(ops,gaps),'fade_intervals':fade_intervals,'notice_intervals':notice_intervals,'changed_copy_files':changed,'cfg_byte_changes':cfg_changes,'trace_sha256':sha(run/'trace.jsonl'),'probe_sha256':manifest['probe_sha256'],'emulator_sha256':manifest['emulator_sha256'],'config_sha256':manifest['config_sha256'],'original_files_unchanged':True}
 (run/'comparison.json').write_text(json.dumps(report,indent=2)+'\n');reports.append(report);counts.update(totals)
 corpus.append({'run':run.name,'ops':ops})
(OUT/'running-original-corpus.json').write_text(json.dumps(corpus,separators=(',',':'))+'\n')
report={'comparison_completed':True,'compared_boundaries_match':True,'counts':dict(counts),'runs':reports,
 'model_sha256':identity(),'validator_sha256':sha(Path(__file__)),'corpus_sha256':sha(OUT/'running-original-corpus.json'),
 'known_gameplay_mismatches':['Clone Game retries immediately. Running original executes fade-out and fade-in around retries; native delays and palette fade arguments are recorded per run.','Clone success notice begins before the original wrapper palette/message transitions are reproduced.'],
 'limits':['Finite recorded sessions, not exhaustive full-game equivalence.','Seeded model compares all state; canonical clone compares all state except three explicitly unspecified stack words, while carrying state continuously.','Timer samples are observed emulated PIT values; physical host keyboard-to-photon latency is not measured.','Full original renders and executes audio routines; host audio output muted.','Browser/native render projection, menus and disk persistence are not equivalent yet.']}
(OUT/'running-original-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'compared_boundaries_match':True,'counts':dict(counts),'known_gameplay_mismatches':report['known_gameplay_mismatches']},indent=2))
