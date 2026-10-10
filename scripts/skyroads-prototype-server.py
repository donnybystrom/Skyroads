#!/usr/bin/env python3
"""Local UI/API server for the recovered SkyRoads physics core."""
import argparse
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import threading
import uuid
from skyroads_collision import TABLES
from skyroads_session import Catalog,Session,replay,ANALYSIS,ROOT
from skyroads_timer import TICK_HZ,TICK_SECONDS
from skyroads_cycle import identity as cycle_identity,replay as cycle_replay


class App:
    def __init__(self):
        self.catalog=Catalog();self.sessions={};self.lock=threading.RLock()


class Handler(BaseHTTPRequestHandler):
    def log_message(self,fmt,*args):
        if args and str(args[1] if len(args)>1 else '').startswith(('4','5')):super().log_message(fmt,*args)

    def send_json(self,value,status=200):
        body=json.dumps(value,separators=(',',':')).encode()
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(body)

    def do_GET(self):
        path=self.path.split('?')[0]
        app=self.server.app
        if path=='/api/catalog':
            self.send_json({'physics_hz':TICK_HZ,'tick_seconds':TICK_SECONDS,'tables':TABLES,
                            'model_sha256':cycle_identity(),
                            'roads':[{'index':i,'rows':r['rows_as_seven_uint16_le'],'metadata':r['metadata_words'],'sha256':r['decoded_sha256']}
                                     for i,r in app.catalog.roads.items()]});return
        parts=path.strip('/').split('/')
        if len(parts)>=3 and parts[:2]==['api','sessions']:
            with app.lock:
                session=app.sessions.get(parts[2])
                if session is None:self.send_json({'error':'Unknown session'},404);return
                if parts[3:]==['recording']:self.send_json(session.recording());return
                if len(parts)==3:self.send_json(session.snapshot());return
        files={'/':ROOT/'scripts/skyroads-physics.html','/physics-viewer.html':ROOT/'scripts/skyroads-physics.html',
               '/geometry.js':ROOT/'scripts/skyroads-geometry.js','/road-viewer.html':ANALYSIS/'road-viewer.html'}
        files.update({'/physics.js':ROOT/'scripts/skyroads-physics.js','/cycle.js':ROOT/'scripts/skyroads-cycle.js','/ui.js':ROOT/'scripts/skyroads-ui.js'})
        files['/presentation.js']=ROOT/'scripts/skyroads-presentation.js'
        files['/response-ui.js']=ROOT/'scripts/skyroads-response-ui.js'
        files['/mobile.js']=ROOT/'scripts/skyroads-mobile.js'
        files['/menu-viewer.html']=ROOT/'scripts/skyroads-menu-viewer.html'
        files['/menu-viewer.js']=ROOT/'scripts/skyroads-menu-viewer.js'
        files['/menus.js']=ROOT/'scripts/skyroads-menus.js'
        files['/renderer.js']=ROOT/'scripts/skyroads-renderer.js'
        files['/hud.js']=ROOT/'scripts/skyroads-hud.js'
        files['/renderer-ui.js']=ROOT/'scripts/skyroads-renderer-ui.js'
        files['/audio.js']=ROOT/'scripts/skyroads-audio.js'
        files['/audio-ui.js']=ROOT/'scripts/skyroads-audio-ui.js'
        if path.startswith('/audio/'):
            name=path[len('/audio/'):]
            if name==Path(name).name and Path(name).suffix in ('.json','.wav','.flac'):
                candidate=ANALYSIS/'audio'/name
                if candidate.is_file():files[path]=candidate
        if path.startswith(('/graphics/','/menus/')):
            folder=path.split('/')[1];name=path[len(folder)+2:]
            if name==Path(name).name and Path(name).suffix in ('.json','.bin','.png'):
                candidate=ANALYSIS/folder/name
                if candidate.is_file():files[path]=candidate
        file=files.get(path)
        if file is None:self.send_json({'error':'Not found'},404);return
        body=file.read_bytes();self.send_response(200)
        mime={'.js':'text/javascript; charset=utf-8','.html':'text/html; charset=utf-8',
              '.json':'application/json; charset=utf-8','.png':'image/png','.bin':'application/octet-stream',
              '.wav':'audio/wav','.flac':'audio/flac'}
        self.send_header('Content-Type',mime.get(file.suffix,'application/octet-stream'))
        self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-cache')
        self.end_headers();self.wfile.write(body)

    def do_POST(self):
        try:
            origin=self.headers.get('Origin')
            if origin and origin!=f'http://{self.headers.get("Host")}':raise ValueError('Cross-origin request rejected')
            length=int(self.headers.get('Content-Length','0'))
            limit=32*1024*1024 if self.path.startswith('/api/cycles/') else 65536
            if not 0<=length<=limit:raise ValueError('Request too large')
            request=json.loads(self.rfile.read(length) or b'{}')
            if not isinstance(request,dict):raise ValueError('Object body required')
            app=self.server.app
            with app.lock:
                parts=self.path.strip('/').split('/')
                if parts in (['api','cycles','replay'],['api','cycles','save']):
                    recording=request.get('recording',{})
                    if not isinstance(recording,dict):raise ValueError('Recording object required')
                    if not isinstance(recording.get('samples'),list) or len(recording['samples'])>20000:raise ValueError('Invalid recording length')
                    index=recording.get('road_index');assist=recording.get('assist')
                    if type(index)!=int or index not in app.catalog.roads:raise ValueError('Invalid road')
                    if type(assist)!=bool:raise ValueError('Invalid assist option')
                    completed=recording.get('initial_completed')
                    if not isinstance(completed,list) or len(completed)!=30 or any(type(n)!=int or not 0<=n<=65535 for n in completed):raise ValueError('Invalid completion counters')
                    result=cycle_replay(app.catalog,recording)
                    if parts[-1]=='save':
                        folder=ANALYSIS/'recordings';folder.mkdir(exist_ok=True)
                        name=f"cycle-{recording['road_index']:02d}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}.json"
                        file=folder/name;file.write_text(json.dumps(recording,indent=2)+'\n')
                        self.send_json({'verified':True,'saved_path':str(file),'ticks':result['ticks']});return
                    self.send_json(result);return
                if parts==['api','sessions']:
                    index=request.get('road_index',0);assist=request.get('assist',True)
                    if type(index)!=int or index not in app.catalog.roads:raise ValueError('Invalid road')
                    if type(assist)!=bool:raise ValueError('Invalid assist option')
                    if len(app.sessions)>=64:raise ValueError('Session limit reached; restart server')
                    key=uuid.uuid4().hex;session=Session(app.catalog,index,assist);app.sessions[key]=session
                    self.send_json({'session_id':key,**session.snapshot()});return
                if len(parts)!=4 or parts[:2]!=['api','sessions']:self.send_json({'error':'Not found'},404);return
                session=app.sessions.get(parts[2])
                if session is None:self.send_json({'error':'Unknown session'},404);return
                action=parts[3]
                if action=='step':
                    if request.get('expected_tick')!=len(session.samples):
                        self.send_json({'error':'Stale tick index',**session.snapshot()},409);return
                    controls=request.get('inputs',[])
                    if not isinstance(controls,list) or not 1<=len(controls)<=16:raise ValueError('Expected1..16 controls')
                    # Validate the whole batch before applying any part of it.
                    for item in controls:
                        if not isinstance(item,dict) or set(item)!=set(('throttle','direction','jump')):raise ValueError('Invalid controls')
                        for name,allowed in [('throttle',(-1,0,1)),('direction',(-1,0,1)),('jump',(0,1))]:
                            if type(item[name])!=int or item[name] not in allowed:raise ValueError('Invalid '+name)
                    samples=[]
                    for item in controls:
                        sample=session.step(**item)
                        if sample is None:break
                        samples.append(sample)
                    self.send_json({**session.snapshot(),'samples':samples});return
                if action=='replay':
                    self.send_json(replay(app.catalog,session.recording()));return
                if action=='save':
                    folder=ANALYSIS/'recordings';folder.mkdir(exist_ok=True)
                    name=f"road-{session.index:02d}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{parts[2][:8]}.json"
                    file=folder/name;file.write_text(json.dumps(session.recording(),indent=2)+'\n')
                    self.send_json({'saved_path':str(file),'ticks':len(session.samples)});return
                self.send_json({'error':'Not found'},404)
        except (ValueError,KeyError,TypeError,AssertionError,RuntimeError) as exc:
            self.send_json({'error':str(exc)},400)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=8766)
    args=parser.parse_args();server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.app=App();server.daemon_threads=True
    print(f'SkyRoads prototype: http://127.0.0.1:{args.port}/physics-viewer.html',flush=True)
    server.serve_forever()


if __name__=='__main__':main()
