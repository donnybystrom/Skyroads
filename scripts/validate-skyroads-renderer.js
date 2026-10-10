/* Independent browser renderer comparison with running-original indexed RAM. */
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'analysis/skyroads'),G=path.join(OUT,'graphics');
const meta=JSON.parse(fs.readFileSync(path.join(G,'manifest.json'))),read=f=>new Uint8Array(fs.readFileSync(path.join(G,f)));
const assets={...meta,carsMeta:meta.cars,dashboardMeta:meta.dashboard,cars:read(meta.cars.images[0].file),
 dashboard:read(meta.dashboard.images[0].file),worldPixels:meta.worlds.map(w=>read(w.images[0].file)),banks:meta.trek_banks.map(b=>read(b.file))};
const geometry=require('./skyroads-geometry.js').createGeometry(JSON.parse(fs.readFileSync(path.join(OUT,'collision-validation.json'))).tables);
const renderer=require('./skyroads-renderer.js').createSkyRoadsRenderer(assets,geometry);
const roads=JSON.parse(fs.readFileSync(path.join(OUT,'roads/manifest.json'))).roads;
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
for(const item of [meta.cars,meta.dashboard,...meta.worlds]){
 assert.strictEqual(sha(path.join(ROOT,'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10',item.source)),item.source_sha256);
 for(const block of item.images)assert.strictEqual(sha(path.join(G,block.file)),block.sha256);
}
for(const bank of meta.trek_banks)assert.strictEqual(sha(path.join(G,bank.file)),bank.sha256);
assert.strictEqual(sha(path.join(OUT,'runtime-load-image.bin')),meta.module_sha256);
assert.strictEqual(sha(path.join(ROOT,'scripts/extract-skyroads-graphics.py')),meta.extractor_sha256);
let count=0,pixels=0;const phases=new Set(),structures=new Set(),runs=[],digest=crypto.createHash('sha256');
function sameBytes(actual,expected,label,length=actual.length){
 const bad=[];let count=0;for(let i=0;i<length;i++)if(actual[i]!==expected[i]){count++;if(bad.length<8)bad.push({offset:i,actual:actual[i],original:expected[i]});}
 assert.strictEqual(count,0,label+' '+JSON.stringify(bad));
}
for(const runName of process.argv.slice(2)){
 const run=path.resolve(runName),events=fs.readFileSync(path.join(run,'trace.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
 const manifest=JSON.parse(fs.readFileSync(path.join(run,'manifest.json')));
 assert(manifest.original_files_unchanged&&manifest.exit_code===0&&!manifest.guest_program_patched&&manifest.graphics_observation);
 for(const [file,key] of [['dosbox.conf','config_sha256'],['probe-source.h','probe_sha256'],['emulator-build.json','build_manifest_sha256'],['runner-source.py','runner_sha256']])
  assert.strictEqual(sha(path.join(run,file)),manifest[key],file+' provenance');
 for(const [file,hash] of Object.entries(manifest.source_sha256))assert.strictEqual(sha(path.join(manifest.source,file)),hash,'Unchanged original '+file);
 for(const [file,hash] of Object.entries(manifest.output_sha256))assert.strictEqual(sha(path.join(run,'drive-c',file)),hash,'Copied drive '+file);
 assert(events.at(-1).kind==='stop'&&events.at(-1).sessions>=manifest.requested_sessions,'Incomplete native run');
 let before,index,params,id;const frames=[];
 for(const e of events){
  if(e.kind==='initial')index=e.mode===3?0:e.selected+1;
  else if(e.kind==='render_before')before=e;
  else if(e.kind==='render_arguments'){params=e.args;id=e.id;}
  else if(e.kind==='render_after'){
   assert(before&&params);const rows=roads[index].rows_as_seven_uint16_le;
   const prefix=path.join(run,`trace.jsonl.graphics-attempt-${e.attempt}.`),nativeBackground=new Uint8Array(fs.readFileSync(prefix+'background.bin'));
   assert.deepStrictEqual(assets.cars,new Uint8Array(fs.readFileSync(prefix+'cars.bin')),'Native car decode');
   sameBytes(renderer.background(index),nativeBackground,'Native background decode',44160);
   sameBytes(renderer.palette(index),new Uint8Array(fs.readFileSync(prefix+'palette.bin')),'Native palette');
   const expected=renderer.parameters(rows,before.state,before.timer);
   // Ice display-height adjustment is passed to 0c98 separately.
   if(before.state.surface2)expected[2]=Math.floor(((before.state.height-128)&65535)/128);
   for(const k of [0,1,2,3,5,6])assert.strictEqual(expected[k],params[k],`${path.basename(run)}/${id}/argument${k}`);
   const start=new Uint8Array(fs.readFileSync(path.join(run,`trace.jsonl.render-${id}.before.bin`)));
   const original=new Uint8Array(fs.readFileSync(path.join(run,`trace.jsonl.render-${id}.after.bin`)));
   const actual=renderer.renderIndexed(rows,params,nativeBackground,start);
   const differences=[];for(let i=0;i<44160;i++)if(actual[i]!==original[i])differences.push(i);
   if(differences.length){fs.writeFileSync(path.join(G,'render-failure-actual.bin'),actual);fs.writeFileSync(path.join(G,'render-failure-original.bin'),original);
    throw Error(JSON.stringify({run:path.basename(run),id,args:params,state:before.state,different_pixels:differences.length,first:differences.slice(0,12).map(i=>({x:i%320,y:Math.floor(i/320),original:original[i],clone:actual[i]}))},null,2));}
   frames.push({id,attempt:e.attempt,road_index:index,tick:before.state.tick_counter,phase:params[1]&7,scene_sha256:crypto.createHash('sha256').update(actual.subarray(0,44160)).digest('hex')});
   digest.update(actual.subarray(0,44160));count++;pixels+=44160;phases.add(params[1]&7);
   for(let r=Math.max(0,(params[1]>>>3)-3);r<(params[1]>>>3)+8;r++)for(const v of rows[r]||[])structures.add((v>>8)&15);
  }
 }
 runs.push({run:path.basename(run),trace_sha256:sha(path.join(run,'trace.jsonl')),manifest_sha256:sha(path.join(run,'manifest.json')),
  probe_sha256:manifest.probe_sha256,emulator_sha256:manifest.emulator_sha256,source_files_unchanged:true,frames});
}
assert(count>0);
const report={indexed_frames_match:true,frames:count,pixels_compared:pixels,forward_phases:[...phases].sort(),structure_kinds:[...structures].sort(),
 result_sha256:digest.digest('hex'),renderer_sha256:sha(path.join(__dirname,'skyroads-renderer.js')),asset_manifest_sha256:sha(path.join(G,'manifest.json')),runs,
 limits:['44160-byte (320x138) original scene buffers; each extracted car, background and 256-color palette matches the corresponding original RAM.','Palette RGB conversion and browser display scaling require separate checks.','Host keyboard/display latency, audio and animated HUD indicators are not covered.']};
fs.writeFileSync(path.join(OUT,'graphics-validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({...report,runs:runs.map(r=>({run:r.run,frames:r.frames.length}))},null,2));
