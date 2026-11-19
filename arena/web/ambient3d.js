'use strict';
/* Pure Canvas 3D ambient sculpture. Presentation only: NO fetch, model, session or input access.
   Drawn from mathematically rotated 3D ribbons; no framework, no remote assets.
   18fps maximum, DPR capped; pauses on hidden tabs, static for reduced-motion users. */
(function () {
  const canvas = document.getElementById('ambient3d');
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d', { alpha: true });
  if (!ctx) return;
  const media = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  const reduced = () => !!media?.matches;
  const SEGMENTS = 144;
  const ribbons = [];
  // Two linked curves over a closed 3D trefoil; depth is preserved for perspective.
  for (const phase of [0, Math.PI / 2]) {
    const points = [];
    for (let i = 0; i <= SEGMENTS; i++) {
      const t = 2 * Math.PI * i / SEGMENTS;
      const r = 1.05 + 0.31 * Math.cos(3 * t + phase);
      points.push([r * Math.cos(2 * t + phase / 3), r * Math.sin(2 * t + phase / 3),
        .52 * Math.sin(3 * t + phase)]);
    }
    ribbons.push(points);
  }
  let w = 0, h = 0, ratio = 1, frame = 0, last = 0, clock = 0, running = false;
  const angular = (a, b, angle) => [a * Math.cos(angle) - b * Math.sin(angle),
    a * Math.sin(angle) + b * Math.cos(angle)];
  function project(point, spin, zoom) {
    let [x, y, z] = point;
    [y, z] = angular(y, z, .4 + spin * .32);
    [x, z] = angular(x, z, spin);
    [x, y] = angular(x, y, -.16 + spin * .12);
    const perspective = 4.4 / (4.4 - z);
    return [x * zoom * perspective, y * zoom * perspective, z];
  }
  function draw(spin) {
    ctx.clearRect(0, 0, w, h);
    const small = w < 680;
    const zoom = Math.min(w * (small ? .26 : .185), h * .38, 235);
    const centerX = w * (small ? .74 : .78), centerY = h * (small ? .2 : .32);
    ctx.save();
    ctx.translate(centerX, centerY);
    // A soft, faint double orbit signals depth without hiding message text.
    for (let orbit = 0; orbit < 2; orbit++) {
      ctx.beginPath();
      for (let i = 0; i <= SEGMENTS; i++) {
        const angle = i * 2 * Math.PI / SEGMENTS;
        const p = project([1.63 * Math.cos(angle), 1.63 * Math.sin(angle), 0],
          spin + orbit * 1.2, zoom);
        if (!i) ctx.moveTo(p[0], p[1]); else ctx.lineTo(p[0], p[1]);
      }
      ctx.strokeStyle = orbit ? 'rgba(130,221,210,.055)' : 'rgba(156,180,255,.065)';
      ctx.lineWidth = orbit ? 1.3 : 1.7;
      ctx.stroke();
    }
    for (let strip = 0; strip < ribbons.length; strip++) {
      const points = ribbons[strip].map(pt => project(pt, spin, zoom));
      const segments = [];
      for (let j = 0; j < points.length - 1; j++) {
        const a = points[j], b = points[j+1];
        segments.push({a,b, depth:(a[2]+b[2])/2});
      }
      segments.sort((a,b)=>a.depth-b.depth);
      for (const seg of segments) {
        const light = Math.max(0, Math.min(1, (seg.depth + 1.7) / 3.4));
        const alpha = .085 + light * .16;
        ctx.beginPath();
        ctx.moveTo(seg.a[0], seg.a[1]); ctx.lineTo(seg.b[0], seg.b[1]);
        ctx.lineWidth = 1.4 + light * 2.7;
        ctx.strokeStyle = strip ? 'rgba(136,206,245,'+alpha.toFixed(3)+')'
                                : 'rgba(119,232,208,'+alpha.toFixed(3)+')';
        ctx.stroke();
      }
    }
    ctx.restore();
  }
  function resize() {
    ratio = Math.min(1.5, window.devicePixelRatio || 1);
    w = Math.max(1, window.innerWidth); h = Math.max(1, window.innerHeight);
    canvas.width = Math.round(w * ratio); canvas.height = Math.round(h * ratio);
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw(clock);
  }
  function tick(now) {
    if (!running) return;
    frame = window.requestAnimationFrame(tick);
    if (now - last < 55) return; // ~18 fps maximum.
    const elapsed = Math.min(80, now - (last || now));
    last = now;
    clock += elapsed * 0.000095; // deliberate 66s orbit.
    draw(clock);
  }
  function sync() {
    const shouldRun = !reduced() && !document.hidden;
    if (shouldRun === running) return;
    running = shouldRun;
    if (running) {
      last = 0;
      frame = window.requestAnimationFrame(tick);
    } else {
      window.cancelAnimationFrame(frame);
      draw(clock);
    }
  }
  resize(); sync();
  window.addEventListener('resize', resize, { passive: true });
  document.addEventListener('visibilitychange', sync);
  if (media?.addEventListener) media.addEventListener('change', sync);
}());
