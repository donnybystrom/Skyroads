#!/usr/bin/env python3
"""Run the unchanged packed DOS game in a copied, isolated DOSBox directory."""
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10'
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--name',default='demo-reference');p.add_argument('--cycles',type=int,default=20000)
p.add_argument('--sessions',type=int,default=1);p.add_argument('--max-ms',type=int,default=180000)
p.add_argument('--keyboard',action='store_true');p.add_argument('--visible',action='store_true');p.add_argument('--realtime',action='store_true')
p.add_argument('--graphics',action='store_true',help='Capture read-only original renderer inputs and indexed framebuffers')
p.add_argument('--audio',action='store_true',help='Observe original music register writes and sound requests without changing guest state')
p.add_argument('--hud',action='store_true',help='Capture original VGA instrument updates, caches and source masks')
p.add_argument('--response',action='store_true',help='Observe input decode and scene completion with emulated and host monotonic times')
p.add_argument('--menus',action='store_true',help='Visit main/settings/help/30 road selections through real keyboard input')
p.add_argument('--gallery',action='store_true',help='Visit all thirty menu roads through real keyboard input (use --sessions 30 --max-ms 300000)')
a=p.parse_args()
if not a.name.replace('-','').replace('_','').isalnum():p.error('Invalid run name')
if a.cycles<=0 or a.sessions<=0 or a.max_ms<=0:p.error('Cycles, sessions and maximum time must be positive')
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
binary=ROOT/'tools/dosbox-x/src/dosbox-x'
build_path=ROOT/'runtime/dosbox-x-build.json'
if not build_path.exists():p.error('Build observer first: bash scripts/build-skyroads-dosbox.sh')
build=json.loads(build_path.read_text())
if build['emulator_sha256']!=sha(binary) or build['probe_sha256']!=sha(ROOT/'scripts/dosbox-skyroads-probe.h'):
 p.error('Observer build differs from source; rebuild with bash scripts/build-skyroads-dosbox.sh')
run=ROOT/'analysis/skyroads/original-runs'/a.name
run.mkdir(parents=True,exist_ok=True); drive=run/'drive-c';captures=run/'captures'
if (run/'trace.jsonl').exists():p.error('Run already exists; use a fresh name to preserve evidence')
shutil.copytree(SOURCE,drive,dirs_exist_ok=True);captures.mkdir(exist_ok=True)
config=f'''[sdl]
fullscreen=false
output=surface
showmenu=false
waitonerror=false
windowresolution=960x720
[dosbox]
machine=vgaonly
memsize=16
captures={captures}
[render]
frameskip=0
aspect=true
doublescan=false
scaler=normal2x
[cpu]
core=normal
cputype=386
cycles=fixed {a.cycles}
turbo={'false' if a.realtime else 'true'}
[mixer]
nosound=true
[sblaster]
sbtype=sb16
[midi]
mpu401=none
[dos]
xms=false
ems=false
umb=false
[autoexec]
mount c "{drive}"
c:
skyroads.exe
exit
'''
(run/'dosbox.conf').write_text(config)
env={**os.environ,'SKYROADS_TRACE':str(run/'trace.jsonl'),'SKYROADS_MAX_MS':str(a.max_ms),
     'SKYROADS_MAX_SESSIONS':str(a.sessions),'SDL_AUDIODRIVER':'dummy'}
if not a.visible:env['SDL_VIDEODRIVER']='dummy'
if a.keyboard or a.gallery or a.menus:env['SKYROADS_KEYBOARD']='1'
if a.graphics:env['SKYROADS_GRAPHICS']='1'
if a.audio:env['SKYROADS_AUDIO']='1'
if a.hud:env['SKYROADS_HUD']='1'
if a.gallery:env['SKYROADS_GALLERY']='1'
if a.response:env['SKYROADS_RESPONSE']='1'
if a.menus:env['SKYROADS_MENUS']='1'
meta={'source':str(SOURCE),'source_sha256':{f.name:sha(f) for f in SOURCE.iterdir() if f.is_file() and not f.name.startswith('.')},
      'emulator_commit':subprocess.check_output(['git','-C',str(ROOT/'tools/dosbox-x'),'rev-parse','HEAD'],text=True).strip(),
      'emulator_sha256':sha(binary),'probe_sha256':sha(ROOT/'scripts/dosbox-skyroads-probe.h'),
      'build_manifest_sha256':sha(build_path),'runner_sha256':sha(Path(__file__)),
      'config_sha256':sha(run/'dosbox.conf'),'cycles_per_ms':a.cycles,'turbo':not a.realtime,
      'requested_sessions':a.sessions,'max_emulated_ms':a.max_ms,
      'graphics_observation':a.graphics,
      'audio_observation':a.audio,
      'hud_observation':a.hud,
      'response_observation':a.response,'menu_observation':a.menus,
      'road_gallery':a.gallery,
      'keyboard_controller_scenario':a.keyboard or a.gallery or a.menus,'guest_program_patched':False,'host_audio_muted':True,'visible':a.visible}
(run/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
shutil.copyfile(ROOT/'scripts/dosbox-skyroads-probe.h',run/'probe-source.h')
shutil.copyfile(build_path,run/'emulator-build.json')
shutil.copyfile(Path(__file__),run/'runner-source.py')
start=time.monotonic()
with (run/'dosbox.log').open('w') as log:
 result=subprocess.run([str(binary),'-fastlaunch','-conf',str(run/'dosbox.conf')],cwd=run,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=300)
meta['host_elapsed_seconds']=round(time.monotonic()-start,3);meta['exit_code']=result.returncode
meta['original_files_unchanged']=all(sha(SOURCE/f)==v for f,v in meta['source_sha256'].items())
meta['output_sha256']={f.name:sha(f) for f in drive.iterdir() if f.is_file() and not f.name.startswith('.')}
(run/'manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({k:meta[k] for k in ('exit_code','host_elapsed_seconds','original_files_unchanged')},indent=2))
print(run)
raise SystemExit(result.returncode)
