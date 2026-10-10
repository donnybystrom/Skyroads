/* VGA draws after physics at the next outer boundary, before its timer wait.
 * P/Escape/failure gates precede that draw. Hold the previous picture when
 * paused/returned; redraw immediately when the pause release protocol ends.
 * EGA's BIOS page-flip latency is a separate, unimplemented display mode. */
function selectSkyRoadsPresentation(before,after,previous){
  if(after.attempt_number!==before.attempt_number)return {...after.state};
  if(after.game_phase==='attempt'&&['playing','finishing'].includes(after.phase)){
    const state={...after.state};
    if(after.phase==='playing'&&state.surface2)state.height=(state.height-128)&65535;
    return state;
  }
  return {...previous};
}
if(typeof module!=='undefined')module.exports={selectSkyRoadsPresentation};
