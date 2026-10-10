/* Compare independently reconstructed menus with unchanged whole-game VGA RAM. */
const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'analysis/skyroads'),DIR=path.join(OUT,'menus');
const run=path.join(OUT,'original-runs',process.argv[2]||'menus-reference');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const meta=JSON.parse(fs.readFileSync(path.join(DIR,'manifest.json'))),manifest=JSON.parse(fs.readFileSync(path.join(run,'manifest.json')));
assert(manifest.original_files_unchanged&&!manifest.guest_program_patched&&manifest.exit_code===0);
for(const a of Object.values(meta.assets)){
 assert.strictEqual(sha(fs.readFileSync(path.join(manifest.source,a.source))),a.source_sha256);
 for(const im of a.images){im.pixels=fs.readFileSync(path.join(DIR,im.file));assert.strictEqual(sha(im.pixels),im.sha256);}
}
const menus=require('./skyroads-menus.js').createSkyRoadsMenus(meta.assets),events=fs.readFileSync(path.join(run,'trace.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
const records=[];let total=0;
const cfg=fs.readFileSync(path.join(manifest.source,'SKYROADS.CFG')),completed=Array.from({length:30},(_,i)=>cfg.readUInt16LE(6+i*2));
for(const e of events.filter(e=>e.kind==='menu_capture')){
 const model=menus.render(e.menu,e.focus,e.input_mode,e.music_mode,completed),native=fs.readFileSync(path.join(run,`trace.jsonl.menu-${e.id}.bin`));
 const palette=fs.readFileSync(path.join(run,`trace.jsonl.menu-${e.id}.palette.bin`));
 const differences=[];for(let i=0;i<64000;i++)if(model.pixels[i]!==native[i]){if(differences.length<8)differences.push([i,model.pixels[i],native[i]]);}
 assert.deepStrictEqual(differences,[],JSON.stringify(e));
 for(const v of new Set(native))for(let c=0;c<3;c++)assert.strictEqual(model.palette[v*3+c],palette[v*3+c],JSON.stringify({menu:e.menu,color:v,channel:c}));
 records.push({...e,pixels_sha256:sha(native),palette_sha256:sha(palette),matched_bytes:64000});total+=64000;
}
assert.strictEqual(records.filter(e=>e.menu==='roads').length,30);
assert.deepStrictEqual(records.filter(e=>e.menu==='roads').map(e=>e.focus),Array.from({length:30},(_,i)=>i));
assert.deepStrictEqual([...new Set(records.filter(e=>e.menu==='settings').map(e=>e.focus))].sort(),[0,1,2,3,4]);
assert.strictEqual(records.filter(e=>e.menu==='help').length,2);
const report={matched:true,frames:records.length,indexed_bytes:total,palette_scope:'All palette entries referenced by every native frame',records,
 source_sha256:manifest.source_sha256,trace_sha256:sha(fs.readFileSync(path.join(run,'trace.jsonl'))),
 renderer_sha256:sha(fs.readFileSync(path.join(__dirname,'skyroads-menus.js'))),
 limits:['Original VGA menu pixels at key-wait boundaries; title animations, palette transitions, persistence and gameplay integration are separate work.','Joystick/mouse menu selections exist; their gameplay support is not supplied by this renderer.']};
fs.writeFileSync(path.join(OUT,'menu-validation.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({matched:true,frames:records.length,indexed_bytes:total}));
