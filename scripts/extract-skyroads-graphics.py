#!/usr/bin/env python3
"""Decode original CMAP/PICT assets and eight precomputed VGA span banks.

Container and span reconstruction follow 3f91,4084,4052,3a96,3153/3190.
No original files are modified. Indexed bytes remain the rendering authority.
"""
import hashlib,json,struct
from pathlib import Path
from PIL import Image
from skyroads_lzs import decode
ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10'
OUT=ROOT/'analysis/skyroads/graphics';OUT.mkdir(exist_ok=True)
sha=lambda b:hashlib.sha256(b).hexdigest()
def graphic(name,base):
 b=(SOURCE/name).read_bytes();assert b[:4]==b'CMAP'
 n=b[4];palette=list(b[5:5+n*3]);mapping=list(b[5+n*3:5+n*5]);p=5+n*5;images=[]
 while p<len(b):
  assert b[p:p+4]==b'PICT',(name,p)
  offset,height,width=struct.unpack_from('<3H',b,p+4)
  decoded=decode(b[p+10:],width*height)
  pixels=bytes((x+base)&255 if x else 0 for x in decoded.data)
  file=f'{Path(name).stem.lower()}-{len(images)}.bin';(OUT/file).write_bytes(pixels)
  colors=[0]*768
  for i,c in enumerate(palette):colors[base*3+i]=(c<<2)|(c>>4)
  image=Image.frombytes('P',(width,height),pixels);image.putpalette(colors);image.save(OUT/file.replace('.bin','.png'))
  images.append({'file':file,'offset':offset,'width':width,'height':height,'sha256':sha(pixels),
                 'encoded_start':p+10,'encoded_length':decoded.consumed_bytes,'decoded_length':len(pixels)})
  p+=10+decoded.consumed_bytes
 assert p==len(b)
 return {'source':name,'source_sha256':sha(b),'palette_base':base,'palette_rgb6':palette,'ega_mapping':mapping,'images':images}
assets={'cars':graphic('CARS.LZS',72),'dashboard':graphic('DASHBRD.LZS',92),
        'worlds':[graphic(f'WORLD{i}.LZS',142) for i in range(10)]}
data=(SOURCE/'TREKDAT.LZS').read_bytes();p=0;banks=[]
while p<len(data):
 total,length=struct.unpack_from('<HH',data,p);r=decode(data[p+4:],length);s=r.data;bank=bytearray(s[:0x270]);q=0x270
 for _ in range(0x410):
  bank.extend(s[q:q+3]);q+=3
  while True:
   start=s[q];q+=1;bank.append(start)
   if start==255:break
   bank.extend((s[q],0));q+=1
 assert q==len(s) and len(bank)<=total,(q,len(s),len(bank),total)
 # All 312 bank table pointers refer to the reconstructed span data.
 assert all(0x270<=v<len(bank) for v in struct.unpack_from('<312H',bank))
 file=f'trek-{len(banks)}.bin';(OUT/file).write_bytes(bank)
 banks.append({'file':file,'sha256':sha(bank),'size':len(bank),'source_offset':p,'decoded_length':length,'allocation':total})
 p+=4+r.consumed_bytes
assert p==len(data) and len(banks)==8
module=(ROOT/'analysis/skyroads/runtime-load-image.bin').read_bytes();ds=module[0x6760:]
assets.update({'trek_banks':banks,'trek_source_sha256':sha(data),'module_sha256':sha(module),
 'color_pairs':[list(ds[0x352+4*i:0x354+4*i]) for i in range(74)],
 'ship_lane_offsets':list(struct.unpack_from('<7h',ds,0x3e)),
 'ship_animation':list(struct.unpack_from('<4H',ds,0x11a)),
 'ship_clip':list(struct.unpack_from('<190H',ds,0x47a)),
 'shadow_masks':list(ds[0x68e:0x68e+5*261]),
 'roads_source_sha256':sha((SOURCE/'ROADS.LZS').read_bytes()),
 'road_palettes':[r['metadata_216_bytes'] for r in json.loads((ROOT/'analysis/skyroads/roads/manifest.json').read_text())['roads']],
 'format':'skyroads-vga-assets-v1','extractor_sha256':sha(Path(__file__).read_bytes())})
# Transpose original column-major 29x24 ship frames for a reviewable atlas.
cars=(OUT/assets['cars']['images'][0]['file']).read_bytes();atlas=Image.new('P',(29*11,24*7));colors=[0]*768
for i,c in enumerate(assets['cars']['palette_rgb6']):colors[72*3+i]=(c<<2)|(c>>4)
atlas.putpalette(colors)
for f in range(77):
 for x in range(29):
  for y in range(24):atlas.putpixel(((f%11)*29+x,(f//11)*24+y),cars[f*720+x*24+y])
atlas.save(OUT/'ship-atlas.png',transparency=0)
(OUT/'manifest.json').write_text(json.dumps(assets,indent=2)+'\n')
print(json.dumps({'graphics_containers':12,'trek_banks':len(banks),'ship_frames':77,'source_files_unchanged':True,'output':str(OUT)},indent=2))
