const $ = id => document.getElementById(id);
const canvas = $('frame'), ctx = canvas.getContext('2d'), video = $('video');
let generation = 0, media = null, objectUrl = null, timer = null, pending = null, controller = null;
function stop() {
  generation++; clearTimeout(timer); controller?.abort(); pending?.reject(new Error('Stopped')); pending = null;
  media?.getTracks().forEach(track => track.stop()); media = null;
  video.pause(); video.srcObject = null; video.removeAttribute('src'); video.load();
  if (objectUrl) URL.revokeObjectURL(objectUrl); objectUrl = null;
  $('status').textContent = 'Camera stopped.'; $('result').textContent = '';
}
window.addEventListener('pagehide', stop);
$('stop').onclick = stop;
async function processFrame(source, tag, caption) {
  if (tag !== generation) return;
  const w = source.videoWidth || source.naturalWidth || source.width;
  const h = source.videoHeight || source.naturalHeight || source.height;
  const scale = Math.min(1, 640 / Math.max(w, h));
  canvas.width = Math.max(1, Math.round(w*scale)); canvas.height = Math.max(1, Math.round(h*scale));
  ctx.drawImage(source,0,0,canvas.width,canvas.height);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', .84));
  if (tag !== generation) return;
  controller = new AbortController();
  const response = await fetch('/infer', {method:'POST',body:blob,signal:controller.signal});
  if (!response.ok) throw new Error('Frame could not be processed (HTTP ' + response.status + ').');
  const data = await response.json(); if (tag !== generation) return;
  ctx.lineWidth=3; ctx.font='bold 15px sans-serif';
  for (const item of data.detections) {
    const [x,y,r,b]=item.box;
    ctx.strokeStyle=item.label === 'smoke' ? '#65cfff' : '#ff7755'; ctx.fillStyle=ctx.strokeStyle;
    ctx.strokeRect(x*canvas.width,y*canvas.height,(r-x)*canvas.width,(b-y)*canvas.height);
    ctx.fillText(item.label+' '+Math.round(item.score*100)+'%',x*canvas.width,Math.max(16,y*canvas.height-3));
  }
  $('status').textContent = caption + ' · CPU ' + data.processing_ms + ' ms';
  $('result').textContent = data.detections.length ? data.detections.map(d=>d.label+' '+Math.round(d.score*100)+'%').join(', ') : 'No flame or smoke detected in this frame.';
}
function loop(tag, capture) {
  async function next() {
    if (generation !== tag) return;
    try { await capture(); if (generation === tag) timer=setTimeout(next,1000); }
    catch(error) { if (generation === tag) { stop(); $('status').textContent=error.message; } }
  }
  next();
}
$('webcam').onclick = async () => {
  stop(); const tag=generation;
  try {
    const stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{width:{ideal:640},height:{ideal:360}}});
    if (tag!==generation) { stream.getTracks().forEach(track=>track.stop()); return; }
    media=stream; video.srcObject=stream; await video.play();
    loop(tag,()=>processFrame(video,tag,'Local webcam'));
  } catch(error) { if(tag===generation) {stop(); $('status').textContent=error.message;} }
};
$('file').onchange = async () => {
  stop(); const tag=generation, file=$('file').files[0]; if(!file) return;
  try {
    if(file.type.startsWith('video/')) {
      objectUrl=URL.createObjectURL(file); video.src=objectUrl; await video.play();
      loop(tag,()=>processFrame(video,tag,'Local video'));
    } else {
      const image=await createImageBitmap(file); try {await processFrame(image,tag,'Local image');} finally {image.close();}
    }
  } catch(error) {if(tag===generation) $('status').textContent=error.message;}
};
const viewerWindow = window.parent !== window ? window.parent : window.opener;
const viewerOrigin = new URLSearchParams(location.search).get('viewer');
const localOrigin = viewerOrigin && /^http:\/\/(localhost|127\.0\.0\.1)(:\d+)?$/.test(viewerOrigin);
window.addEventListener('message',event=>{
  if(event.source!==viewerWindow || event.origin!==viewerOrigin || !pending || event.data?.id!==pending.id) return;
  if(event.data.error) pending.reject(new Error(event.data.error)); else pending.resolve(event.data);
});
$('drone').onclick = () => {
  stop(); const tag=generation;
  if(!localOrigin || !viewerWindow) { $('status').textContent='Open Camera view from the fleet dashboard to use a drone.'; return; }
  loop(tag,async ()=>{
    const id=crypto.randomUUID();
    let timeout;
    const reply=await new Promise((resolve,reject)=>{
      pending={id,resolve,reject}; timeout=setTimeout(()=>reject(new Error('Fleet viewer unavailable. Reopen Camera view.')),5000);
      viewerWindow.postMessage({type:'drone-frame',id},viewerOrigin);
    }).finally(()=>{clearTimeout(timeout);pending=null;});
    const image=await createImageBitmap(reply.blob);
    try {await processFrame(image,tag,'Drone '+(reply.drone+1)+' · tour '+(reply.run+1)+' · '+reply.time+' s');} finally {image.close();}
  });
};


$('example').onclick = async () => {
  stop(); const tag = generation;
  try {
    const response = await fetch('/reference.jpg');
    if (!response.ok) throw new Error('Reference image unavailable');
    const image = await createImageBitmap(await response.blob());
    try { await processFrame(image, tag, 'Reference image'); } finally { image.close(); }
  } catch (error) { if (tag === generation) $('status').textContent = error.message; }
};

if (new URLSearchParams(location.search).get('source') === 'drone') $('drone').click();
