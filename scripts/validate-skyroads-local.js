/* Compare every local integer state and intermediate trace with x86 corpus. */
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'analysis/skyroads');
const manifest=JSON.parse(fs.readFileSync(path.join(OUT,'roads/manifest.json')));
const tables=JSON.parse(fs.readFileSync(path.join(OUT,'collision-validation.json'))).tables;
const physics=require('./skyroads-physics.js').createPhysics(tables);
const {createCycle,SkyRoadsInputQueue}=require('./skyroads-cycle.js'),cycle=createCycle(physics);
const rowsOf=hex=>{const b=Buffer.from(hex,'hex'),rows=[];for(let n=0;n<b.length;n+=14){const row=[];for(let i=0;i<7;i++)row.push(b.readUInt16LE(n+i*2));rows.push(row);}return rows;};
const catalog={roads:manifest.roads.map(r=>({rows:r.rows_as_seven_uint16_le,metadata:r.metadata_words,sha256:r.decoded_sha256})),model_sha256:{}};
let ticks=0,frames=0,events=0,queueCases=0;const digest=crypto.createHash('sha256');
for(const line of fs.readFileSync(path.join(OUT,'tick-corpus.jsonl'),'utf8').trim().split('\n')){
  const c=JSON.parse(line),trace=[];const result=physics.tick(rowsOf(c.road_hex),c.state,c.config,c.input,e=>trace.push(e));
  assert.deepStrictEqual(result,c.result,'Tick state '+ticks);assert.deepStrictEqual(trace,c.events,'Tick trace '+ticks);ticks++;events+=trace.length;
  digest.update(JSON.stringify([result,trace]));
}
const cycles=JSON.parse(fs.readFileSync(path.join(OUT,'cycle-corpus.json')));
if(fs.existsSync(path.join(OUT,'pause-poll-corpus.json')))cycles.push(...JSON.parse(fs.readFileSync(path.join(OUT,'pause-poll-corpus.json'))));
for(const c of cycles){
  const rows=c.road_index===null?rowsOf(c.road_hex):catalog.roads[c.road_index].rows;
  const attempt=new cycle.Attempt(rows,c.config,c.seeds);
  assert.deepStrictEqual(attempt.snapshot(),c.initial);
  for(const f of c.frames){
    if(f.inject_before)Object.assign(attempt,JSON.parse(JSON.stringify(f.inject_before)));
    const trace=attempt.advance(f.input.mask,f.input.elapsed);
    assert.deepStrictEqual(attempt.snapshot(),f.snapshot,'Cycle state '+c.group+' '+frames);
    assert.deepStrictEqual(trace,f.events,'Cycle trace '+c.group+' '+frames);frames++;events+=trace.length;
  }
}
// Event positions on both sides of a boundary, simultaneous keys, quick tap,
// delayed rendering, stale event delivery and keyboard bits reset on retry.
const dt=1000/(1193182/6628/5);
for(const offset of [-.001,0,.001]){
  const q=new SkyRoadsInputQueue(dt);q.reset(100);
  const e=q.enqueue(0,true,100+dt+offset);
  assert.strictEqual(e.frame,offset<=0?0:1);assert.strictEqual(q.consume(0).mask,offset<=0?1:0);
  assert.strictEqual(q.consume(1).mask,1);queueCases++;
}
for(let stall=1;stall<=12;stall++){
  const q=new SkyRoadsInputQueue(dt);q.reset(0);q.enqueue(0,true,dt*.4);q.enqueue(0,false,dt*2.3);q.enqueue(2,true,dt*3.3);q.enqueue(3,true,dt*3.3);
  for(let f=0;f<12;f++){const value=q.consume(f);assert.strictEqual(value.mask,f<2?1:f===2?0:12);if(f>=3)assert.strictEqual(cycle.decode(value.mask).direction,0);}queueCases++;
}
{
  const q=new SkyRoadsInputQueue(dt);q.reset(0);q.enqueue(9,true,dt*.2);q.enqueue(9,false,dt*.8);assert.strictEqual(q.consume(0).mask,0);
  const late=q.enqueue(0,true,dt*.7);assert.strictEqual(late.late_frames,1);assert.strictEqual(q.consume(1).mask,1);q.clearHeld();assert.strictEqual(q.consume(2).mask,0);queueCases+=3;
}
// Persisted Game lifecycle corpora are produced by original caller checks.
const gameCorpus=path.join(OUT,'lifecycle-corpus.json');let lifecycle=0;
if(fs.existsSync(gameCorpus))for(const c of JSON.parse(fs.readFileSync(gameCorpus))){
  const active=c.road_hex?{...catalog,roads:catalog.roads.map((r,i)=>i===c.index?{...r,rows:rowsOf(c.road_hex),metadata:c.metadata}:r)}:catalog;
  const game=new cycle.Game(active,c.index,c.assist,c.completed);
  for(const f of c.frames){if(f.inject_before){const b=f.inject_before;game.phase=b.game_phase;game.notice_ticks=b.notice_ticks;game.completed=b.completed.slice();Object.assign(game.attempt,JSON.parse(JSON.stringify(b)));}
    const actual=game.advance(f.input.mask,f.input.elapsed,f.input.notice_key);const expected={...f};delete expected.inject_before;assert.deepStrictEqual(actual,expected);lifecycle++;
  }
}
const report={verified:true,tick_cases:ticks,cycle_frames:frames,lifecycle_frames:lifecycle,compared_events:events,input_queue_cases:queueCases,
  result_sha256:digest.digest('hex'),code_sha256:Object.fromEntries(['skyroads-physics.js','skyroads-cycle.js','skyroads-geometry.js'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname,n))).digest('hex')])),
  limitations:['Logical input boundaries validated; physical OS/display latency requires measured runtime evidence.']};
let presentation=0;
const selectPresentation=require('./skyroads-presentation.js').selectSkyRoadsPresentation;
const presentationFile=path.join(OUT,'presentation-corpus.json');
if(fs.existsSync(presentationFile))for(const c of JSON.parse(fs.readFileSync(presentationFile))){
  let display={...c.initial.state,...c.initial_display};
  for(const f of c.frames){display=selectPresentation({game_phase:'attempt',attempt_number:1,...f.before},{game_phase:'attempt',attempt_number:1,...f.after},display);
    assert.deepStrictEqual(Object.fromEntries(Object.keys(f.display).map(k=>[k,display[k]])),f.display);presentation++;}
}
report.presentation_boundaries=presentation;
fs.writeFileSync(path.join(OUT,'local-validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
