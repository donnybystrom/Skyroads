#!/usr/bin/env python3
"""Extract original instrument masks and embedded digit/assist glyphs."""
import hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10'
OUT=ROOT/'analysis/skyroads/graphics'
sha=lambda b:hashlib.sha256(b).hexdigest()
module=(ROOT/'analysis/skyroads/runtime-load-image.bin').read_bytes();ds=module[0x6760:]
meta={'format':'skyroads-hud-assets-v1','module_sha256':sha(module),
      'extractor_sha256':sha(Path(__file__).read_bytes()),'instruments':{}}
for key,name,count in [('oxygen','OXY_DISP.DAT',10),('fuel','FUL_DISP.DAT',10),('speed','SPEED.DAT',34)]:
 b=(SOURCE/name).read_bytes();pointers=struct.unpack_from('<'+'H'*count,b);data=b[count*2:];records=[]
 for i,offset in enumerate(pointers):
  at,width,height=struct.unpack_from('<HBB',data,offset);pixels=list(data[offset+4:offset+4+width*height])
  assert len(pixels)==width*height and set(pixels)<={0,1,2} and width and height
  assert at%320+width<=320 and at//320+height<=200
  assert offset+4+width*height==(pointers[i+1] if i+1<count else len(data))
  records.append({'offset':offset,'destination':at,'width':width,'height':height,'pixels':pixels})
 file=f'hud-{key}.bin';(OUT/file).write_bytes(data)
 meta['instruments'][key]={'source':name,'source_sha256':sha(b),'file':file,'sha256':sha(data),'records':records}
symbols=ds[0x16c:0x338];(OUT/'hud-symbols.bin').write_bytes(symbols)
meta['symbols']={'file':'hud-symbols.bin','sha256':sha(symbols),
 'digits':[list(ds[0x16c+i*20:0x16c+(i+1)*20]) for i in range(10)],
 'assist':[list(ds[0x234+i*130:0x234+(i+1)*130]) for i in range(2)]}
assert all(set(x)<={0,1,2} for x in meta['symbols']['digits'])
assert all(set(x)<={0,5,6} for x in meta['symbols']['assist'])
(OUT/'hud-manifest.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps({'instrument_masks':54,'digits':10,'assist_symbols':2,'manifest':str(OUT/'hud-manifest.json')},indent=2))
