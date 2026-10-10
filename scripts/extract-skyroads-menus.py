#!/usr/bin/env python3
"""Extract original mixed CMAP/PICT menu containers; retain indexed pixels."""
import hashlib,json,struct
from pathlib import Path
from skyroads_lzs import decode
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10'
OUT=ROOT/'analysis/skyroads/menus';OUT.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
assets={}
for name,bases in {'MAINMENU.LZS':[190],'SETMENU.LZS':[200,250],
                   'HELPMENU.LZS':[200,200,200],'GOMENU.LZS':[0,240],
                   'INTRO.LZS':[0,50,50]+[160]*14}.items():
 b=(SOURCE/name).read_bytes();p=0;palettes=[];images=[];base=None
 while p<len(b):
  tag=b[p:p+4];p+=4
  if tag==b'CMAP':
   n=b[p];base=bases[len(palettes)];p+=1
   palettes.append({'base':base,'rgb6':list(b[p:p+n*3]),'ega_mapping':list(b[p+n*3:p+n*5])});p+=n*5
  else:
   assert tag==b'PICT',(name,p,tag)
   offset,height,width=struct.unpack_from('<3H',b,p);p+=6;r=decode(b[p:],width*height);p+=r.consumed_bytes
   pixels=bytes((v+base)&255 if v else 0 for v in r.data)
   file=f'{Path(name).stem.lower()}-{len(images)}.bin';(OUT/file).write_bytes(pixels)
   images.append({'file':file,'offset':offset,'height':height,'width':width,'palette':len(palettes)-1,'sha256':sha(pixels)})
 assert p==len(b)
 assets[Path(name).stem.lower()]={'source':name,'source_sha256':sha(b),'palettes':palettes,'images':images}
cfg=(SOURCE/'SKYROADS.CFG').read_bytes();assert len(cfg)==66
manifest={'format':'skyroads-menu-assets-v1','assets':assets,'extractor_sha256':sha(Path(__file__).read_bytes()),
 'initial_profile':{'source_sha256':sha(cfg),'input_mode':struct.unpack_from('<H',cfg,2)[0],
                    'music_mode':struct.unpack_from('<H',cfg,4)[0],'completed':list(struct.unpack_from('<30H',cfg,6))}}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'containers':len(assets),'pictures':sum(len(v['images']) for v in assets.values()),'output':str(OUT)}))
