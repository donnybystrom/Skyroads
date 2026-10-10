/* Menu pictures and navigation recovered from the original 16-bit program. */
function createSkyRoadsMenus(assets){
 function blit(frame,image,offset=image.offset,opaque=false){for(let y=0;y<image.height;y++)for(let x=0;x<image.width;x++){
   const v=image.pixels[y*image.width+x];if(v||opaque)frame[offset+y*320+x]=v;}}
 function palette(groups){const p=new Uint8Array(768);for(const g of groups)p.set(g.rgb6,g.base*3);return p;}
 function render(menu,focus=0,inputMode=0,musicMode=0,completed=Array(30).fill(0)){
   const f=new Uint8Array(64000);let p;
   if(menu==='main'){
     const a=assets.intro,b=assets.mainmenu;blit(f,a.images[0]);blit(f,a.images[1]);blit(f,b.images[focus]);
     p=palette([a.palettes[0],a.palettes[2],a.palettes[4],b.palettes[0]]);
   }else if(menu==='settings'){
     const a=assets.setmenu;blit(f,a.images[0]);blit(f,a.images[6+inputMode]);blit(f,a.images[9+musicMode]);blit(f,a.images[1+focus]);p=palette(a.palettes);
   }else if(menu==='help'){
     const a=assets.helpmenu;blit(f,a.images[focus]);p=palette([a.palettes[focus]]);
   }else if(menu==='roads'){
     const a=assets.gomenu;blit(f,a.images[0]);
     for(let i=0;i<30;i++)for(let j=0;j<Math.min(completed[i],7);j++)blit(f,a.images[1],0x11f0+Math.floor(i%15/3)*0x30c0+i%3*0xb40+(i>=15?160:0)+7*j,true);
     const offset=0xf3e+Math.floor(focus/3)%5*0x30c0+focus%3*0xb40+(focus>=15?160:0);
     for(let y=0;y<9;y++)for(let x=0;x<48;x++)if(y===0||y===8||x===0||x===47)f[offset+y*320+x]=1;
     p=palette(a.palettes);
   }else throw Error('Unknown original menu');
   return {pixels:f,palette:p};
 }
 function navigate(menu,focus,key){
   if(menu==='main')return key==='ArrowUp'?Math.max(0,focus-1):key==='ArrowDown'?Math.min(2,focus+1):focus;
   if(menu==='settings'){
     if(key==='ArrowLeft')return Math.max(0,focus-1);if(key==='ArrowRight')return Math.min(4,focus+1);
     if(key==='ArrowUp')return focus===3?0:focus===4?1:focus;
     if(key==='ArrowDown')return focus===0?3:focus<3?4:focus;return focus;
   }
   if(menu==='roads')return Math.min(29,key==='ArrowUp'?Math.max(0,focus-1):key==='ArrowDown'?focus+1:key==='ArrowLeft'?(focus<15?0:focus-15):key==='ArrowRight'?focus+15:focus);
   return focus;
 }
 return {render,navigate};
}
if(typeof module!=='undefined')module.exports={createSkyRoadsMenus};
