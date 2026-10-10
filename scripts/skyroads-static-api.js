/* Static-host adapter. Runs the existing deterministic core; no server required. */
function createSkyRoadsStaticReplay(catalog,physicsFactory,cycleFactory){
 const cycle=cycleFactory(physicsFactory(catalog.tables));
 const equal=(a,b)=>JSON.stringify(sort(a))===JSON.stringify(sort(b));
 function sort(v){return Array.isArray(v)?v.map(sort):v&&typeof v==='object'?Object.fromEntries(Object.keys(v).sort().map(k=>[k,sort(v[k])])):v;}
 return recording=>{
   if(recording?.format!=='skyroads-cycle-v2')throw Error('Unknown recording format');
   if(!equal(recording.model_sha256,catalog.model_sha256))throw Error('Recording model identity differs');
   const index=recording.road_index;
   if(!Number.isInteger(index)||!catalog.roads[index]||recording.road_sha256!==catalog.roads[index].sha256)throw Error('Road identity differs');
   if(typeof recording.assist!=='boolean'||!Array.isArray(recording.initial_completed)||recording.initial_completed.length!==30||recording.initial_completed.some(n=>!Number.isInteger(n)||n<0||n>65535))throw Error('Invalid completion counters');
   if(!Array.isArray(recording.samples)||recording.samples.length>20000)throw Error('Invalid recording length');
   for(const s of recording.samples){const i=s.input;if(!i||!Number.isInteger(i.mask)||i.mask<0||i.mask>=2048||!Number.isInteger(i.elapsed)||i.elapsed<0||i.elapsed>65535||typeof i.notice_key!=='boolean')throw Error('Invalid replay input');}
   const result=cycle.replay(catalog,recording);
   if(!equal(result.final,recording.final))throw Error('Final snapshot differs');
   return result;
 };
}
if(typeof module!=='undefined')module.exports={createSkyRoadsStaticReplay};
if(typeof window!=='undefined')(()=>{
 const originalFetch=window.fetch.bind(window),base=new URL('./',document.baseURI);
 const catalog=originalFetch(new URL('api/catalog.json',base)).then(r=>{if(!r.ok)throw Error('Speldata kunde inte hämtas');return r.json();});
 let verify;window.skyroadsStatic=true;
 window.fetch=async(resource,options)=>{
   const raw=typeof resource==='string'?resource:resource instanceof URL?resource.href:resource.url;
   if(raw==='/api/catalog')return Response.json(await catalog);
   if(raw==='/api/cycles/replay'||raw==='/api/cycles/save'){
     try{const data=await catalog;verify??=createSkyRoadsStaticReplay(data,createPhysics,createCycle);
       const recording=JSON.parse(options.body).recording,result=verify(recording);
       if(raw.endsWith('/replay'))return Response.json(result);
       const filename='skyroads-road-'+recording.road_index+'-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';
       const url=URL.createObjectURL(new Blob([JSON.stringify(recording,null,2)+'\n'],{type:'application/json'})),a=document.createElement('a');
       a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
       return Response.json({verified:true,ticks:result.ticks,saved_path:filename});
     }catch(e){return Response.json({error:e.message},{status:400});}
   }
   // Source scripts keep their recorded identity. Root-relative resource paths
   // are resolved inside this Pages project, including /Skyroads/ deployments.
   if(typeof resource==='string'&&/^\/(graphics|audio|menus)\//.test(resource))return originalFetch(new URL(resource.slice(1),base),options);
   return originalFetch(resource,options);
 };
})();
