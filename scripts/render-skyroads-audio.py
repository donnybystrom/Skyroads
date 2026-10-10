#!/usr/bin/env python3
"""Pre-render recovered original OPL writes with pinned DOSBox-X DBOPL.

Creates a standalone build from the unmodified DBOPL synthesis core, excluding
DOSBox's mixer/savestate adapters. Copyright/license headers are retained.
"""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'analysis/skyroads/audio'
BUILD=ROOT/'runtime/skyroads-audio';BUILD.mkdir(exist_ok=True)
OPL=ROOT/'tools/dosbox-x/src/hardware'
cpp=(OPL/'dbopl.cpp').read_text().split('uint32_t Handler::WriteAddr')[0]+'\n}\n'
header=(OPL/'dbopl.h').read_text().split('struct Handler :')[0]+'\nvoid InitTables();\n}\n'
header=header.replace('#include "adlib.h"','')
(BUILD/'dbopl.cpp').write_text(cpp);(BUILD/'dbopl.h').write_text(header)
(BUILD/'dosbox.h').write_text('#pragma once\n#include <cstdint>\n#include <cstdio>\nusing Bitu=uintptr_t; using Bits=intptr_t;\n#define DB_FASTCALL\n#define GCC_UNLIKELY(x) (x)\n#define LOG_MSG(...) std::fprintf(stderr,__VA_ARGS__)\n')
(BUILD/'main.cpp').write_text(r'''
#include <algorithm>
#include <cmath>
#include <fstream>
#include <vector>
#include "dbopl.h"
int main(int argc,char**argv){
 if(argc!=4)return 2;
 std::ifstream in(argv[1],std::ios::binary);std::ofstream out(argv[2],std::ios::binary);
 if(!in||!out)return 3;
 constexpr uint32_t rate=48000;constexpr double hz=1193182.0/6628;
 DBOPL::InitTables();DBOPL::Chip chip(false);chip.Setup(rate);uint64_t position=0;
 auto advance=[&](uint64_t target){while(position<target){auto n=std::min<uint64_t>(512,target-position);
  int32_t buffer[512]={};chip.GenerateBlock2(n,buffer);
  for(unsigned i=0;i<n;i++){int16_t value=std::clamp<int32_t>(buffer[i],-32768,32767);out.write(reinterpret_cast<char*>(&value),2);}position+=n;}};
 while(true){uint32_t tick;uint8_t reg,value;in.read(reinterpret_cast<char*>(&tick),4);if(!in)break;
  in.read(reinterpret_cast<char*>(&reg),1);in.read(reinterpret_cast<char*>(&value),1);if(!in)return 4;
  advance(std::llround(tick*rate/hz));chip.WriteReg(reg,value);}
 advance(std::llround(std::stoul(argv[3])*rate/hz));return 0;
}
''')
subprocess.run(['clang++','-O2','-std=c++17','-I'+str(BUILD),str(BUILD/'main.cpp'),str(BUILD/'dbopl.cpp'),'-o',str(BUILD/'render-opl')],check=True)
manifest=json.loads((OUT/'manifest.json').read_text())
for track in manifest['tracks']:
 raw=BUILD/f"track-{track['index']}.raw";name=f"track-{track['index']}.flac"
 subprocess.run([str(BUILD/'render-opl'),str(OUT/track['events_file']),str(raw),str(track['loop_end_irq'])],check=True)
 subprocess.run(['ffmpeg','-v','error','-y','-f','s16le','-ar','48000','-ac','1','-i',str(raw),'-c:a','flac',str(OUT/name)],check=True)
 track.update({'file':name,'sample_rate':48000,'frames':raw.stat().st_size//2,'audio_sha256':hashlib.sha256((OUT/name).read_bytes()).hexdigest(),
  'pcm_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'loop_start_seconds':track['loop_start_irq']/manifest['music_irq_hz'],
  'loop_end_seconds':track['loop_end_irq']/manifest['music_irq_hz']})
 print(f"Rendered track {track['index']}: {track['duration_seconds']:.2f}s, {(OUT/name).stat().st_size} bytes",flush=True)
manifest['synthesizer']={'name':'DOSBox-X DBOPL (OPL2)','commit':'b60936a716c72e0978e940f813bab2cd40d43868','license':'GPL-2.0-or-later',
 'source_sha256':{n:hashlib.sha256((OPL/n).read_bytes()).hexdigest() for n in ['dbopl.cpp','dbopl.h']},
 'renderer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rate':48000}
manifest['limits']+=['Music is pre-rendered OPL2 PCM; browser loops repeat the rendered segment, not the continuing physical chip/noise state.','Hardware DAC/analog response and OS output latency are not claimed identical.']
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
