#!/usr/bin/env python3
"""Exercise real HTTP sessions and compare recordings with original x86 ticks."""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from skyroads_session import Catalog, replay, ROOT, ANALYSIS, model_identity
from skyroads_tick import TickState, TickConfig, TickInput


def module(name, filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recording',type=Path,action='append',default=[])
    args=parser.parse_args();started=time.monotonic()
    catalog=Catalog();original=module('tick_oracle','validate-skyroads-tick.py').OriginalTick()
    server_module=module('prototype_server','skyroads-prototype-server.py')
    server=server_module.ThreadingHTTPServer(('127.0.0.1',0),server_module.Handler)
    server.app=server_module.App();server.daemon_threads=True
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    base=f'http://127.0.0.1:{server.server_address[1]}'
    checks=[];runs=[];total=0
    def request(path,body=None,status=200,headers=None):
        payload=None if body is None else json.dumps(body).encode()
        req=Request(base+path,data=payload,headers={'Content-Type':'application/json',**(headers or {})})
        try:
            response=urlopen(req,timeout=30)
        except HTTPError as exc:response=exc
        with response:
            assert response.status==status,(path,response.status,response.read())
            return json.load(response)
    def check_recording(recording,label):
        nonlocal total
        result=replay(catalog,recording);assert result['verified']
        cfg=TickConfig(**recording['config']);state=TickState(**recording['initial_state'])
        digest=hashlib.sha256()
        for n,sample in enumerate(recording['samples']):
            assert sample['tick']==n
            observed=original.execute(catalog.bytes[recording['road_index']],state,cfg,TickInput(**sample['input']))
            assert asdict(observed.state)==sample['state'],f'{label}: state mismatch at{n}'
            assert observed.completion_requested==sample['completion_requested']
            events=[list(e) for e in original.events if e[0] in ('resolve','sound','finish')]
            assert events==sample['events'],f'{label}: event mismatch at{n}'
            digest.update(json.dumps(sample,sort_keys=True).encode());state=observed.state;total+=1
        runs.append({'label':label,'road_index':recording['road_index'],'ticks':len(recording['samples']),
                     'assist':cfg.assist_enabled,'exit_state':state.exit_state,'trace_sha256':digest.hexdigest()})
    def step(key,inputs):
        current=request('/api/sessions/'+key)
        return request('/api/sessions/'+key+'/step',{'expected_tick':current['ticks'],'inputs':inputs})
    try:
        cat=request('/api/catalog');assert len(cat['roads'])==31
        for road in cat['roads']:
            index=road['index'];created=request('/api/sessions',{'road_index':index,'assist':index%2==0})
            key=created['session_id'];controls=[]
            for n in range(100):
                controls.append({'throttle':1 if n<85 else -1,'direction':1 if 8<=n<10 else -1 if 15<=n<17 else 0,'jump':int(n in (25,60))})
            for begin in range(0,len(controls),8):
                result=step(key,controls[begin:begin+8])
                if result['stopped']:break
            recording=request('/api/sessions/'+key+'/recording')
            check_recording(recording,f'http-road-{index:02d}')
            replay_result=request('/api/sessions/'+key+'/replay',{})
            assert replay_result['frames'][1:]==[s['state'] for s in recording['samples']]
            if result['stopped']:
                assert step(key,[controls[0]])['samples']==[]
            print(f'HTTP road{index:02d}: {len(recording["samples"])} x86 ticks match',flush=True)
        checks.extend(['31 catalog roads','31 HTTP trajectories and exact-state/event x86 comparisons','31 server replays','terminal sessions stop'])
        # Rendering cadence or HTTP batch size must not change tick results.
        pair=[request('/api/sessions',{'road_index':0,'assist':True})['session_id'] for _ in range(2)]
        controls=[{'throttle':1,'direction':0,'jump':int(n==25)} for n in range(40)]
        for item in controls:step(pair[0],[item])
        for n in range(0,40,8):step(pair[1],controls[n:n+8])
        recordings=[request('/api/sessions/'+key+'/recording') for key in pair]
        assert recordings[0]==recordings[1];checks.append('single tick vs 8-tick batch invariance')
        key=pair[0];before=request('/api/sessions/'+key+'/recording')
        bad=[controls[0],{'throttle':2,'direction':0,'jump':0}]
        request('/api/sessions/'+key+'/step',{'expected_tick':40,'inputs':bad},400)
        request('/api/sessions/'+key+'/step',{'expected_tick':39,'inputs':[controls[0]]},409)
        request('/api/sessions/'+key+'/step',{'expected_tick':40,'inputs':[controls[0]]},400,{'Origin':'http://example.invalid'})
        assert before==request('/api/sessions/'+key+'/recording')
        checks.extend(['malformed batch is atomic','stale tick rejected without mutation','cross-origin write rejected'])
        saved=request('/api/sessions/'+key+'/save',{})
        file=Path(saved['saved_path']);assert json.loads(file.read_text())==before
        cli=subprocess.run([sys.executable,str(ROOT/'scripts/replay-skyroads-session.py'),str(file)],capture_output=True,text=True,check=True)
        assert json.loads(cli.stdout)['verified'];checks.append('HTTP save -> file -> independent CLI replay')
        check_recording(before,'saved-http-run')
        for file in args.recording:
            check_recording(json.loads(file.read_text()),str(file.resolve()))
            cli=subprocess.run([sys.executable,str(ROOT/'scripts/replay-skyroads-session.py'),str(file)],capture_output=True,text=True,check=True)
            assert json.loads(cli.stdout)['verified']
        report={'verified':True,'elapsed_seconds':time.monotonic()-started,'x86_ticks':total,'runs':runs,'checks':checks,
                'model_sha256':model_identity(),'api_saved_recording':str(file) if not args.recording else saved['saved_path'],
                'browser_recordings':[str(p.resolve()) for p in args.recording],
                'boundary':'post-input-poll deterministic physics; fixed timer per tick; muted audio helpers; analytical rendering'}
        (ANALYSIS/'prototype-validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'verified':True,'x86_ticks':total,'runs':len(runs),'checks':checks},indent=2))
    finally:
        server.shutdown();server.server_close();worker.join(timeout=3)


if __name__=='__main__':main()
