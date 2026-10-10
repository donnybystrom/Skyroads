#!/usr/bin/env python3
"""Execute unchanged original VGA HUD code for boundaries and warning sequences."""
import hashlib,importlib.util,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads/hud-corpus';OUT.mkdir(exist_ok=True)
spec=importlib.util.spec_from_file_location('hud_fixture',ROOT/'scripts/validate-skyroads-collision.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
oracle=fixture.Original(allowed=[(0xf62,0x1631),(0x417e,0x427c),(0x5d80,0x5ded),(0x5e5a,0x5ef6),(0x3c2,0x3d8),(0x472,0x476)],instruction_limit=300000)
G=ROOT/'analysis/skyroads/graphics';graphics=json.loads((G/'manifest.json').read_text());assets=json.loads((G/'hud-manifest.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
def word(at,value):oracle.uc.mem_write(fixture.STACK+at,struct.pack('<H',value&65535))
def long(at,value):oracle.uc.mem_write(fixture.STACK+at,struct.pack('<I',value&0xffffffff))
for key,segment,pointer,table in [('speed',0x3000,0x54a4,0x4572),('oxygen',0x4000,0x5474,0x95f8),('fuel',0x5000,0x960e,0x5480)]:
 a=assets['instruments'][key];oracle.uc.mem_write(segment*16,(G/a['file']).read_bytes());word(pointer,0);word(pointer+2,segment)
 for i,r in enumerate(a['records']):word(table+2*i,r['offset'])
for at,value in [(0x3c,1),(0xaf2a,0x6000),(0x451a,1),(0xcb6,1),(0x41c0,55)]:word(at,value)
background=bytearray(64000);world=(G/graphics['worlds'][0]['images'][0]['file']).read_bytes();background[:len(world)]=world
dashboard=(G/graphics['dashboard']['images'][0]['file']).read_bytes();offset=graphics['dashboard']['images'][0]['offset']
for i,pixel in enumerate(dashboard):
 if pixel:background[offset+i]=pixel
(OUT/'background.bin').write_bytes(background)
default={'forward':3*65536,'speed':0,'speed_delta':0,'fuel':30000,'oxygen':30000,'assist_flag':0,'exit_state':0}
groups=[]
def group(name,steps,gravity=10):
 for at,value in [(0x41be,0),(0x456c,0),(0x960c,0),(0x455c,0),(0xaf20,65535),(0xaf1e,0)]:word(at,value)
 oracle.uc.mem_write(0xa0000,bytes(background));oracle.call(0x1114,[96,156,(gravity-3)*100,4])
 initial=bytes(oracle.uc.mem_read(0xa0000,64000));initial_file=f'{name}-initial.bin';(OUT/initial_file).write_bytes(initial)
 records=[]
 for i,(state,timer) in enumerate(steps):
  s={**default,**state}
  for at,key in [(0x9618,'forward'),(0x54ac,'speed'),(0xaf2e,'speed_delta')]:long(at,s[key])
  for at,key in [(0x5494,'fuel'),(0xb13c,'oxygen'),(0x455a,'assist_flag'),(0x456e,'exit_state')]:word(at,s[key])
  word(0x1600,timer);oracle.call(0x12f8,[])
  result=bytes(oracle.uc.mem_read(0xa0000,64000));file=f'{name}-{i}.bin';(OUT/file).write_bytes(result)
  cache=[struct.unpack('<H',oracle.uc.mem_read(fixture.STACK+o,2))[0] for o in [0x41be,0x456c,0x960c,0x455c,0xaf20,0xaf1e]]
  sound_tick=struct.unpack('<H',oracle.uc.mem_read(fixture.STACK+0xaf38,2))[0]
  records.append({'state':s,'timer':timer,'file':file,'sha256':sha(result),'cache':cache,'sound_tick':sound_tick})
 groups.append({'name':name,'gravity':gravity,'rows':55,'initial':initial_file,'initial_sha256':sha(initial),'steps':records})
speeds=sorted({0,10922,0x7fffffff,0x80000000,0xffffffff}|{321*k+d for k in range(1,35) for d in [-1,0,1]})
group('speed',[(dict(speed=v),0) for v in speeds+list(reversed(speeds))])
group('speed-loss',[(dict(speed=10922,speed_delta=v),0) for v in [0,1,320,321,10921,10922,10923,11243,11244,0xffffffff]])
values=sorted({0,1,30000,65535}|{3000*k+d for k in range(1,11) for d in [-1,0,1]})
group('resources',[(dict(fuel=v,oxygen=v),0) for v in values+list(reversed(values))])
group('warning-fuel',[(dict(fuel=0,exit_state=4),t) for t in range(37)])
group('warning-oxygen',[(dict(oxygen=0,exit_state=5),t) for t in range(37)])
group('assist',[(dict(assist_flag=v),0) for v in [0,1,1,0,1,0]])
denominator=((55-3)*65536)//30
progress=sorted({3*65536,55*65536}|{3*65536+denominator*k+d for k in range(1,31) for d in [-1,0,1]})
group('progress',[(dict(forward=v),0) for v in progress])
for gravity in [3,4,10,16,20]:group(f'gravity-{gravity}',[(dict(),0)],gravity)
report={'format':'skyroads-hud-original-corpus-v1','background_sha256':sha(bytes(background)),'groups':groups,
 'hud_manifest_sha256':sha((G/'hud-manifest.json').read_bytes()),'capture_sha256':sha(Path(__file__).read_bytes()),
 'original_module_sha256':assets['module_sha256'],'instructions':oracle.instructions,
 'limits':['Isolated original HUD/bitmap/division code executes; digital sound mode is muted and no hardware timer advances during a call. Native full-game coverage is separate.']}
(OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'groups':len(groups),'updates':sum(len(g['steps']) for g in groups),'instructions':oracle.instructions},indent=2))
