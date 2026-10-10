(()=>{
 const canvas=document.getElementById('menu'),ctx=canvas.getContext('2d'),status=document.getElementById('status');
 let renderer,menu='main',focus=0,inputMode=0,musicMode=0,completed=Array(30).fill(0);
 function draw(){if(!renderer)return;const r=renderer.render(menu,focus,inputMode,musicMode,completed),rgba=new Uint8ClampedArray(64000*4);
   for(let i=0;i<64000;i++){const c=r.pixels[i]*3;for(let k=0;k<3;k++)rgba[i*4+k]=(r.palette[c+k]<<2)|(r.palette[c+k]>>4);rgba[i*4+3]=255;}
   ctx.putImageData(new ImageData(rgba,320,200),0,0);
   status.textContent=menu==='roads'?'Banval '+(focus+1)+' / 30':menu==='help'?'Hjälpsida '+(focus+1)+' / 2':menu==='settings'?'Controls · '+['keyboard','joystick','mouse'][inputMode]+' · music '+(musicMode?'none':'AdLib'):['Start!','Controls','Help'][focus];
 }
 function show(next){menu=next;focus=0;draw();canvas.focus();}
 for(const name of ['main','settings','help','roads'])document.getElementById(name).onclick=()=>show(name);
 canvas.addEventListener('keydown',e=>{
   if(!renderer||menu!=='help'&&!['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Enter','Escape'].includes(e.code))return;e.preventDefault();
   if(menu==='help'){if(e.code==='Escape'||focus===1){menu='main';focus=2;}else focus=1;draw();return;}
   focus=renderer.navigate(menu,focus,e.code);
   if(e.code==='Escape'){const old=menu;menu='main';focus=old==='settings'?1:old==='help'?2:0;}
   if(e.code==='Enter'){
     if(menu==='main'){menu=['roads','settings','help'][focus];focus=0;}
     else if(menu==='settings'){if(focus<3)inputMode=focus;else musicMode=focus-3;}
     else {draw();status.textContent='Bana '+(focus+1)+' vald i förhandsvisningen. Spelkopplingen återstår.';return;}
   }draw();
 });
 fetch('menus/manifest.json').then(r=>{if(!r.ok)throw Error('Menyresurser saknas');return r.json();}).then(async m=>{
   await Promise.all(Object.values(m.assets).flatMap(a=>a.images.map(async im=>{const r=await fetch('menus/'+im.file);if(!r.ok)throw Error('Menybild saknas');im.pixels=new Uint8Array(await r.arrayBuffer());})));
   completed=m.initial_profile.completed;inputMode=m.initial_profile.input_mode;musicMode=m.initial_profile.music_mode;
   renderer=createSkyRoadsMenus(m.assets);draw();
 }).catch(e=>status.textContent=e.message);
})();
