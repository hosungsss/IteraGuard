'use strict';
/* Decorative 3D ribbon knot: pure Canvas2D, no libraries, networking or model calls.
 * Renders a sparse, projected 3D parametric torus knot behind content. The
 * deliberate Gaussian blur and opacity avoid competing with risk guidance.
 * A11y: canvas is aria-hidden; reduced motion draws once; invisible tabs pause.
 */
(function(){
  const canvas = document.getElementById('ambient3d');
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d', { alpha: true });
  if (!ctx) return;
  const motion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)');
  const reduce = !!(motion && motion.matches);
  const state = {frame:0, active:false, w:0, h:0, last:0};
  const TAU = Math.PI*2;
  const POINTS = 300;
  const geometric = [];
  // Closed torus knot (p=2,q=3): not a static ellipse/sprite.
  for(let i=0;i<POINTS;i++){
    const t=i/POINTS*TAU, tube=0.48, major=1.38;
    const r=major+tube*Math.cos(3*t);
    geometric.push([r*Math.cos(2*t),r*Math.sin(2*t),tube*Math.sin(3*t)]);
  }
  function resize(){
    const w=Math.min(Math.max(window.innerWidth || 800,320),2400);
    const h=Math.min(Math.max(window.innerHeight || 700,320),1800);
    const dpr=Math.min(window.devicePixelRatio || 1,1.5);
    if (state.w===w && state.h===h) return;
    state.w=w; state.h=h;
    canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);
    canvas.style.width=w+'px';canvas.style.height=h+'px';
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  function project(point, time){
    const [x,y,z]=point;
    const a=0.42+time*0.11,b=-0.4+time*0.085;
    const X=x*Math.cos(a)-z*Math.sin(a);
    const Z=x*Math.sin(a)+z*Math.cos(a);
    const Y=y*Math.cos(b)-Z*Math.sin(b);
    const ZZ=y*Math.sin(b)+Z*Math.cos(b);
    const perspective=4.7/(4.7+ZZ);
    return [X*perspective,Y*perspective,ZZ,perspective];
  }
  function draw(time){
    resize();
    const w=state.w,h=state.h;
    ctx.clearRect(0,0,w,h);
    const scale=Math.min(w*.30,h*.45,310);
    const cx=w*(w>900?.83:.80),cy=h*(w>900?.39:.27);
    const projected=geometric.map(point=>project(point,time));
    // Draw separated back and front stroke to retain actual 3D occlusion.
    for(let layer=0;layer<2;layer++){
      ctx.lineWidth=layer===0?1.1:1.6;
      ctx.strokeStyle=layer===0?'rgba(89,164,208,.22)':'rgba(142,241,221,.30)';
      ctx.beginPath();let open=false;
      for(let i=0;i<=POINTS;i++){
        const p=projected[i%POINTS];const visible=layer===0?p[2]>=0:p[2]<0;
        if(!visible){open=false;continue;}
        const px=cx+p[0]*scale,py=cy+p[1]*scale;
        if(!open){ctx.moveTo(px,py);open=true;} else ctx.lineTo(px,py);
      }
      ctx.stroke();
    }
    // Quiet nucleus; blurred by container CSS. No high-frequency sparkling.
    const glow=ctx.createRadialGradient(cx,cy,scale*.04,cx,cy,scale*1.55);
    glow.addColorStop(0,'rgba(78,184,164,.07)');
    glow.addColorStop(.65,'rgba(82,132,210,.025)');
    glow.addColorStop(1,'rgba(82,132,210,0)');
    ctx.fillStyle=glow;ctx.beginPath();ctx.arc(cx,cy,scale*1.55,0,TAU);ctx.fill();
  }
  function tick(timestamp){
    if(document.hidden){state.active=false;return;}
    // ≤ 24 fps; the ribbon is atmospheric rather than distracting.
    if(timestamp-state.last>=42){
      state.last=timestamp;state.frame+=1;
      draw(state.frame/24);
    }
    if(!reduce) window.requestAnimationFrame(tick);
  }
  function start(){
    if(reduce){draw(0);return;}
    if(state.active || document.hidden) return;
    state.active=true;window.requestAnimationFrame(tick);
  }
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden){state.active=false;start();}
    else state.active=false;
  });
  window.addEventListener('resize',()=>{state.w=0;draw(reduce?0:state.frame/24);});
  start();
}());
