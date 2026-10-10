/* Continuous JS clone comparison against full packed-game DOSBox observations. */
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'analysis/skyroads');
const REPORT=process.argv[2]?path.resolve(process.argv[2]):OUT;
const tables=JSON.parse(fs.readFileSync(path.join(OUT,'collision-validation.json'))).tables;
const physics=require('./skyroads-physics.js').createPhysics(tables),cycle=require('./skyroads-cycle.js').createCycle(physics);
const manifest=JSON.parse(fs.readFileSync(path.join(OUT,'roads/manifest.json'))),undefinedLocals=new Set(['jump_height','edge_distance','previous_target_height']);
const count={initializers:0,physics_ticks:0,completion_requests:0,finish_frames:0,pause_polls:0,pause_resumes:0,attempt_returns:0};
const digest=crypto.createHash('sha256');
function check(m,state,label,canonical=false){const values=s=>Object.fromEntries(Object.entries(s).filter(([k])=>!canonical||!undefinedLocals.has(k)));
 assert.deepStrictEqual(values(m.state),values(state),label);digest.update(JSON.stringify(m.state));}
for(const run of JSON.parse(fs.readFileSync(path.join(REPORT,'running-original-corpus.json')))){
 let model,canonical,rows,config,demo,attempt=0,result=null;
 for(const op of run.ops){const label=run.run+'/'+attempt+'/'+op.kind;
  switch(op.kind){
   case 'initial':{
    attempt++;rows=manifest.roads[op.road_index].rows_as_seven_uint16_le;config=op.config;
    // All nine observed attempts used this exact original DEMO.REC. Raw DOSBox
    // captures stay local; a clean checkout can use the verified source file.
    const capturedDemo=path.join(OUT,'original-runs',run.run,`trace.jsonl.attempt-${attempt}.demo.bin`);
    demo=fs.readFileSync(fs.existsSync(capturedDemo)?capturedDemo:path.join(ROOT,'Skyroads-binary/SkyRoads_DOS_EN_Registered-v10/DEMO.REC'));
    assert.strictEqual(crypto.createHash('sha256').update(demo).digest('hex'),'2bb53c6cd62f2cd2a8657cd05bf9e33054570c1e3e98dd89e18587156867016e','original demo identity');
    const seeds=canonical&&result!==null&&![0,7].includes(result)?Object.fromEntries([...undefinedLocals].map(k=>[k,canonical.state[k]])):{};
    model=new cycle.Attempt(rows,config,op.seeds);canonical=new cycle.Attempt(rows,config,seeds);
    check(model,op.state,label);check(canonical,op.state,label,true);count.initializers++;break;
   }
   case 'tick':{
    check(model,op.before,label+'/before');check(canonical,op.before,label+'/canonical-before',true);
    for(const [m,isCanonical] of [[model,false],[canonical,true]]){
     let controls;
     if(op.mode===3){const b=demo[Math.floor(m.state.forward/1638)];assert(b!==undefined);controls={throttle:(b&3)-1,direction:((b>>2)&3)-1,jump:(b>>4)&1};}
     else controls=cycle.decode(op.mask);
     controls.timer=op.input.timer;assert.deepStrictEqual(controls,op.input,label+'/input');
     const r=physics.tick(rows,m.state,config,controls);assert.strictEqual(r.completion_requested,op.completion);m.state=r.state;
     check(m,op.after,label+'/after',isCanonical);
     if(op.completion){m.timer=m.state.tick_counter;m.advance(0,(op.input.timer-m.timer)&65535);}
    }
    if(op.completion)count.completion_requests++;else count.physics_ticks++;break;
   }
   case 'gate':for(const [m,c] of [[model,false],[canonical,true]]){check(m,op.before,label,c);m.timer=op.timer;m.prepare(op.mask,[]);}break;
   case 'pause_poll':for(const [m,c] of [[model,false],[canonical,true]]){m.advance(op.mask,op.elapsed);check(m,op.state,label,c);}count.pause_polls++;break;
   case 'resume_check':assert.strictEqual(model.phase,'playing');assert.strictEqual(model.timer,op.timer);check(model,op.state,label);count.pause_resumes++;break;
   case 'finish_start':check(model,op.state,label);assert.strictEqual(model.phase,'finishing');break;
   case 'finish_after':for(const [m,c] of [[model,false],[canonical,true]]){if(op.elapsed)m.advance(op.mask,op.elapsed);check(m,op.state,label,c);assert.strictEqual(m.timer,op.timer);}if(op.elapsed)count.finish_frames++;break;
   case 'return':for(const [m,c] of [[model,false],[canonical,true]]){if(m.phase!=='returned'){m.timer=op.timer;m.gate(op.mask,[]);}assert.strictEqual(m.result,op.result);check(m,op.state,label,c);}result=op.result;count.attempt_returns++;break;
   default:throw Error('Unknown corpus operation '+op.kind);
  }
 }
}
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const report={compared_boundaries_match:true,counts:count,result_sha256:digest.digest('hex'),corpus_sha256:sha(path.join(REPORT,'running-original-corpus.json')),
 model_sha256:Object.fromEntries(['skyroads-geometry.js','skyroads-physics.js','skyroads-cycle.js'].map(f=>[f,sha(path.join(__dirname,f))])),
 limits:['Full original game executes, but this comparison checks tick/attempt boundaries. Game wrapper fade delays are recorded mismatches, not modeled by this test.','Physical OS/display latency and full graphical equivalence remain unmeasured.']};
fs.writeFileSync(path.join(REPORT,'running-original-js-validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
