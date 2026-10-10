#!/usr/bin/env python3
"""Export the playable browser prototype to a static directory for GitHub Pages."""
import argparse,hashlib,json,shutil
from pathlib import Path
from skyroads_collision import TABLES
from skyroads_session import Catalog,ROOT
from skyroads_cycle import identity
from skyroads_timer import TICK_HZ,TICK_SECONDS
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'dist');a=p.parse_args()
out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);source=ROOT/'scripts';analysis=ROOT/'analysis/skyroads'
catalog=Catalog()
data={'physics_hz':TICK_HZ,'tick_seconds':TICK_SECONDS,'tables':TABLES,'model_sha256':identity(),
 'roads':[{'index':i,'rows':r['rows_as_seven_uint16_le'],'metadata':r['metadata_words'],'sha256':r['decoded_sha256']} for i,r in catalog.roads.items()]}
(out/'api').mkdir(exist_ok=True);(out/'api/catalog.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
names={'geometry','physics','cycle','presentation','ui','renderer','hud','renderer-ui','audio','audio-ui','response-ui','menus','menu-viewer','static-api','static-ui','mobile'}
for name in sorted(names):shutil.copyfile(source/f'skyroads-{name}.js',out/f'{name}.js')
def html(name):
 text=(source/f'skyroads-{name}.html').read_text()
 text=text.replace('src="/','src="').replace('href="/','href="')
 if name=='physics':text=text.replace('<script src="ui.js">','<script src="static-api.js"></script><script src="ui.js">').replace('</html>','<script src="static-ui.js"></script></html>')
 return text
(out/'index.html').write_text(html('physics'));(out/'physics-viewer.html').write_text(html('physics'))
(out/'menu-viewer.html').write_text(html('menu-viewer'));shutil.copyfile(analysis/'road-viewer.html',out/'road-viewer.html')
for folder,extensions in [('graphics',{'.json','.bin'}),('menus',{'.json','.bin'}),('audio',{'.json','.wav','.flac'})]:
 (out/folder).mkdir(exist_ok=True)
 for file in (analysis/folder).iterdir():
  if file.suffix in extensions:shutil.copyfile(file,out/folder/file.name)
(out/'.nojekyll').write_text('')
files={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.rglob('*')) if f.is_file() and f.name!='build-manifest.json'}
(out/'build-manifest.json').write_text(json.dumps({'format':'skyroads-pages-v1','files':files,'core_identity':identity()},indent=2)+'\n')
print(json.dumps({'output':str(out),'files':len(files),'bytes':sum((out/f).stat().st_size for f in files)},indent=2))
