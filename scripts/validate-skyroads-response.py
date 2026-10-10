#!/usr/bin/env python3
"""Measure software response boundaries; never claims physical key-to-photon latency."""
import hashlib,json,re,statistics
from pathlib import Path
from skyroads_cycle import decode_keyboard,replay
from skyroads_session import Catalog
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads'
run=OUT/'original-runs/response-irq-realtime-20000'
events=[json.loads(l) for l in (run/'trace.jsonl').read_text().splitlines()]
manifest=json.loads((run/'manifest.json').read_text())
assert manifest['turbo'] is False and manifest['original_files_unchanged'] and manifest['exit_code']==0
assert hashlib.sha256((run/'probe-source.h').read_bytes()).hexdigest()==manifest['probe_sha256']
start=next(e for e in events if e['kind']=='initial');end=next(e for e in events if e['kind']=='attempt_return')
trace=[e for e in events if start['ms']<=e.get('ms',-1)<=end['ms']]
enum=(ROOT/'tools/dosbox-x/include/keyboard.h').read_text().split('enum KBD_KEYS {')[1].split('};')[0]
enum=re.sub(r'/\*.*?\*/','',enum,flags=re.S)
names=re.findall(r'\bKBD_\w+\b',enum);mapping={names.index('KBD_'+k):i for i,k in enumerate(['up','down','left','right','home','pageup','end','pagedown','esc','space','p'])}
held=0;irq_count=0;poll_count=0
for e in trace:
 if e['kind']=='keyboard_irq':held=e['mask'];irq_count+=1
 elif e['kind']=='input_poll':assert e['mask']==held;poll_count+=1
 elif e['kind']=='input_decoded':assert decode_keyboard(held)=={k:e[k] for k in ('throttle','direction','jump')}
responses=[]
for i,e in enumerate(trace):
 if e['kind']!='hardware_key' or e['key'] not in mapping:continue
 bit=mapping[e['key']];later=trace[i+1:]
 opposite=next((x['ms'] for x in later if x['kind']=='hardware_key' and x['key']==e['key'] and x['down']!=e['down']),float('inf'))
 irq=next((x for x in later if x['kind']=='keyboard_irq' and bool(x['mask']&(1<<bit))==e['down'] and x['ms']<opposite),None)
 assert irq,'Scheduled controller event never reached original keyboard ISR'
 row={'key':names[e['key']],'down':e['down'],'ms_since_initial':round(e['ms']-start['ms'],6),
      'controller_to_irq_ms':round(irq['ms']-e['ms'],6)}
 poll=next((x for x in later if x['kind']=='input_decoded' and x['ms']>=irq['ms'] and x['ms']<opposite and bool(x['mask']&(1<<bit))==e['down']),None)
 if poll and bit<10:
  step=next((x for x in later if x['kind']=='tick_after' and x['ms']>=poll['ms']),None)
  scene=next((x for x in later if step and x['kind']=='scene_ready' and x['ms']>=step['ms']),None)
  row.update(controller_to_poll_ms=round(poll['ms']-e['ms'],6),poll_tick=poll['tick'])
  if step:row['controller_to_step_ms']=round(step['ms']-e['ms'],6)
  if scene:row.update(controller_to_scene_ms=round(scene['ms']-e['ms'],6),host_controller_to_scene_ms=round(scene['host_ms']-e['host_ms'],6))
 else:row['path']='pause busy-poll or superseded before next normal poll'
 responses.append(row)
recording=OUT/'recordings/cycle-01-20261010-145206-a95877b7.json';rec=json.loads(recording.read_text());verified=replay(Catalog(),rec)
browser=rec['response_observation']['events'];assert len(browser)>=12
for e in browser:
 assert e['applied_ms']>=e['received_ms'] and e['canvas_ms']>=e['applied_ms']
 if e['applied']=='timer':assert rec['browser_timing']['input_events'][browser.index(e)]['frame']==e['queued_frame']
values=[e['receipt_to_canvas_ms'] for e in browser if e['applied']=='timer']
assert any(e['applied']=='pause_poll' and e['index']==9 for e in browser)
report={'verified':True,'native_run':run.name,'native_physics_steps':poll_count,'native_keyboard_irq_returns':irq_count,
 'native_gameplay_clock_ratio':(end['host_ms']-start['host_ms'])/(end['ms']-start['ms']),
 'native_responses':responses,'browser_recording':str(recording.relative_to(ROOT)),
 'browser_timer_events':len(values),'browser_receipt_to_canvas_ms':{'min':min(values),'median':statistics.median(values),'max':max(values)},
 'browser_pause_events':sum(e['applied']=='pause_poll' for e in browser),
 'limits':['Native controller-injection and browser key-event receipt are different starting points; these numbers are not a latency ranking.',
 'Native endpoint: RenderShipAndRoadScene return after VGA drawing; browser endpoint: canvas draw return. Neither measures compositor, scanout or photons.',
 'PIT phase at attempt start is free-running in the original. Browser starts a new host clock. Absolute first-step phase is not proven equivalent.',
 'Native run uses SDL dummy video and muted audio. Browser sample is finite and includes host/tool overhead. No hardware display test.',
 'Under host stalls the browser queues historical keys per quantum; original catch-up can reuse the newest poll for multiple ticks. That edge remains to test.'],
 'source_sha256':manifest['source_sha256'],'trace_sha256':hashlib.sha256((run/'trace.jsonl').read_bytes()).hexdigest()}
(OUT/'response-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
