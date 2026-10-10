#!/usr/bin/env python3
"""Real HTTP replay/tamper/identity/schema tests; legacy recordings retained."""
from collections import Counter
import copy
import importlib.util
import json
from pathlib import Path
import threading
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
from skyroads_session import Catalog,replay as legacy_replay
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads'
spec=importlib.util.spec_from_file_location('server',ROOT/'scripts/skyroads-prototype-server.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
server=ThreadingHTTPServer(('127.0.0.1',0),m.Handler);server.app=m.App()
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base=f'http://127.0.0.1:{server.server_port}'
counts=Counter()
def post(recording,action='replay',origin=None):
    req=Request(base+'/api/cycles/'+action,data=json.dumps({'recording':recording}).encode(),headers={'Content-Type':'application/json',**({'Origin':origin} if origin else {})})
    try:
        with urlopen(req) as r:return r.status,json.load(r)
    except HTTPError as e:return e.code,json.load(e)
try:
    rec=json.loads((OUT/'recordings/cycle-01-20261009-204551-f792baea.json').read_text())
    code,result=post(rec);assert code==200 and result['verified'];counts['http_complete_replay']+=1
    malformed=[None,[],{}, {**rec,'initial_completed':[True]*30}, {**rec,'road_index':True}, {**rec,'assist':1}]
    wrong=copy.deepcopy(rec);wrong['model_sha256']['skyroads_cycle.py']='0'*64;malformed.append(wrong)
    wrong=copy.deepcopy(rec);wrong['final']['state']['forward']+=1;malformed.append(wrong)
    wrong=copy.deepcopy(rec);wrong['samples'][0]['state']={};malformed.append(wrong)
    wrong=copy.deepcopy(rec);wrong['samples'][0]['input']['mask']='1';malformed.append(wrong)
    wrong=copy.deepcopy(rec);wrong['samples'][0]['input']['elapsed']=0;malformed.append(wrong)
    before=set((OUT/'recordings').iterdir())
    for body in malformed:
        code,result=post(body,'save');assert code==400 and 'error' in result;counts['rejected_saves']+=1
    assert set((OUT/'recordings').iterdir())==before
    assert post(rec,origin='http://unrelated.invalid')[0]==400;counts['cross_origin_rejected']+=1
    for file in (OUT/'recordings').glob('road-*.json'):
        assert legacy_replay(Catalog(),json.loads(file.read_text()))['verified'];counts['legacy_replays']+=1
    report={'verified':True,'counts':dict(counts),'rejected_saves_write_no_files':True}
    (OUT/'cycle-api-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
finally:server.shutdown();server.server_close()
