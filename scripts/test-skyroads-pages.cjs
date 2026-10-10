const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..'),dist=path.resolve(process.argv[2]||path.join(root,'dist'));
const catalog=JSON.parse(fs.readFileSync(path.join(dist,'api/catalog.json')));
const physics=require('./skyroads-physics.js').createPhysics,cycle=require('./skyroads-cycle.js').createCycle;
const verify=require('./skyroads-static-api.js').createSkyRoadsStaticReplay(catalog,physics,cycle);
let recordings=0,samples=0,negativeCases=0;
for(const name of fs.readdirSync(path.join(root,'analysis/skyroads/recordings'))){
 const rec=JSON.parse(fs.readFileSync(path.join(root,'analysis/skyroads/recordings',name)));
 if(rec.format!=='skyroads-cycle-v2'||JSON.stringify(rec.model_sha256)!==JSON.stringify(catalog.model_sha256))continue;
 const result=verify(rec);assert(result.verified);samples+=result.ticks;recordings++;
}
assert(recordings>=3);
const game=new (cycle(physics(catalog.tables)).Game)(catalog,1,true,Array(30).fill(0));game.advance(1,1,false);
const correct=game.recording();verify(correct);
for(const mutate of [r=>r.final.state.speed++,r=>r.road_sha256='wrong',r=>r.model_sha256={},r=>r.samples[0].input.mask=4096,r=>r.samples[0].snapshot.state.speed++,r=>r.initial_completed=[]]){
 const rec=JSON.parse(JSON.stringify(correct));mutate(rec);assert.throws(()=>verify(rec));negativeCases++;
}
const {createSkyRoadsInputSources}=require('./skyroads-mobile.js');const events=[];
const input=createSkyRoadsInputSources((index,down,time)=>events.push({index,down,time}));
input.press('keyboard',0,0);input.press('finger1',0,1);input.press('finger2',2,2);input.press('finger3',9,3);
assert.strictEqual(input.mask(),1|4|512);input.release('finger1',4);assert.strictEqual(input.mask(),1|4|512);
input.release('keyboard',5);assert.strictEqual(input.mask(),4|512);input.release('finger2',6);assert.strictEqual(input.mask(),512);
input.clear(7);assert.strictEqual(input.mask(),0);input.release('finger3',8);assert.strictEqual(events.length,6);
input.press('finger4',3,9);input.press('finger4',2,10);assert.strictEqual(input.mask(),4);input.clear(11);
assert.deepStrictEqual(events.map(e=>[e.index,e.down]),[[0,true],[2,true],[9,true],[0,false],[2,false],[9,false],[3,true],[3,false],[2,true],[2,false]]);
// Static build must ship byte-identical verified core sources and project-relative links.
for(const file of ['geometry','physics','cycle','presentation','ui'])assert.deepStrictEqual(fs.readFileSync(path.join(dist,file+'.js')),fs.readFileSync(path.join(root,'scripts/skyroads-'+file+'.js')));
for(const file of ['index.html','physics-viewer.html','menu-viewer.html'])assert(!/\b(?:src|href)="\//.test(fs.readFileSync(path.join(dist,file),'utf8')));
console.log(JSON.stringify({verified:true,recordings,samples,negativeCases,touchTransitions:events.length,originalCoreBytesUnchanged:true},null,2));
