/* Boundary/warning rasterization compared with unchanged original x86 code. */
const fs=require('fs'),path=require('path'),crypto=require('crypto'),assert=require('assert/strict');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'analysis/skyroads'),dir=path.join(OUT,'hud-corpus');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex'),read=file=>new Uint8Array(fs.readFileSync(path.join(dir,file)));
const bytes=fs.readFileSync(path.join(OUT,'graphics/hud-manifest.json')),meta=JSON.parse(bytes),corpus=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));
assert.equal(sha(bytes),corpus.hud_manifest_sha256);
assert.equal(sha(fs.readFileSync(path.join(ROOT,'scripts/capture-skyroads-hud-corpus.py'))),corpus.capture_sha256);
const {createSkyRoadsHud,createSkyRoadsHudTimeline}=require('./skyroads-hud.js');
const hud=createSkyRoadsHud(meta),keys=['speed','oxygen','fuel','progress','assist','blink'],groups=[];
const digest=crypto.createHash('sha256');let count=0;
for(const g of corpus.groups){
 const timeline=createSkyRoadsHudTimeline(hud,read('background.bin'),g.gravity,g.rows);
 const snapshots=g.steps.map(s=>({attempt_number:1,game_phase:'attempt',phase:'playing',state:s.state,timer:s.timer}));
 timeline.sync(snapshots);
 const frame=read('background.bin');assert.equal(sha(frame),corpus.background_sha256);let cache=hud.initialize(frame,g.gravity);
 const initial=read(g.initial);assert.equal(sha(initial),g.initial_sha256);assert.deepEqual(frame,initial,g.name+' initial digits');
 for(const [i,step] of g.steps.entries()){
  cache=hud.update(frame,cache,step.state,step.timer,g.rows);
  const expected=read(step.file);assert.equal(sha(expected),step.sha256);
  const bad=[];for(let n=0;n<64000&&bad.length<8;n++)if(frame[n]!==expected[n])bad.push({x:n%320,y:Math.floor(n/320),actual:frame[n],original:expected[n]});
  assert.equal(bad.length,0,`${g.name}/${i}: ${JSON.stringify(bad)}`);
  assert.deepEqual(keys.map(k=>cache[k]),step.cache,`${g.name}/${i} counters`);digest.update(frame);count++;
  assert.deepEqual(timeline.get(i).image.pixels,expected.slice(44160),`${g.name}/${i} timeline pixels`);
 }
 const held=timeline.get(snapshots.length-1).image;
 snapshots.push({...snapshots.at(-1),phase:'pause_press',timer:400,state:{...g.steps[0].state}});
 snapshots.push({...snapshots.at(-1),phase:'finishing',timer:71});timeline.sync(snapshots);
 assert.equal(timeline.get(snapshots.length-1).image,held,'Finish HUD stays frozen');
 assert.equal(timeline.get(snapshots.length-2).image,held,'P-pause HUD stays frozen');
 snapshots.push({...snapshots[0],attempt_number:2});timeline.sync(snapshots);
 assert.deepEqual(timeline.get(snapshots.length-1).image.pixels,read(g.steps[0].file).slice(44160),'Retry initializes original HUD');
 groups.push({name:g.name,updates:g.steps.length});
}
const report={verified:true,updates:count,pixels_compared:count*64000,timeline_frames_match:count,
 pause_finish_freeze_groups:groups.length,retry_reset_groups:groups.length,groups,result_sha256:digest.digest('hex'),
 renderer_sha256:sha(fs.readFileSync(path.join(ROOT,'scripts/skyroads-hud.js'))),corpus_manifest_sha256:sha(fs.readFileSync(path.join(dir,'manifest.json'))),limits:corpus.limits};
fs.writeFileSync(path.join(OUT,'hud-corpus-validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
