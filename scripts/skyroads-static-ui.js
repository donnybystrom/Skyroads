/* Host-only wording: the Pages build verifies locally in JavaScript. */
(()=>{const base=$('replay').onclick;$('replay').onclick=async()=>{await base();
 for(const id of ['status','recordingNote'])$(id).textContent=$(id).textContent.replaceAll('Python','JavaScript');};})();
