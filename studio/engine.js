// LINGOOF studio: zamana göre çizilen sahne motoru. E.seek(t) her karede çağrılır; aynı t her zaman aynı kareyi üretir.
window.E = (() => {
  // Material hareket eğrileri (cubic-bezier) ve geri esneme (easeOutBack) aileleri
  function bezier(x1, y1, x2, y2) {
    const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
    const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
    const sx = t => ((ax * t + bx) * t + cx) * t, sy = t => ((ay * t + by) * t + cy) * t;
    return x => {
      let lo = 0, hi = 1, t = x;
      for (let i = 0; i < 50; i++) { const v = sx(t); if (Math.abs(v - x) < 1e-7) break; if (v < x) lo = t; else hi = t; t = (lo + hi) / 2; }
      return sy(t);
    };
  }
  const back = s => t => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2);
  const ease = {
    linear: t => t,
    outCubic: t => 1 - Math.pow(1 - t, 3),
    inCubic: t => t * t * t,
    inOutCubic: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    outQuint: t => 1 - Math.pow(1 - t, 5),
    inOutSine: t => -(Math.cos(Math.PI * t) - 1) / 2,
    step: t => (t < 1 ? 0 : 1),
    enter: bezier(0.05, 0.7, 0.1, 1.0),   // beliren her şey
    exit: bezier(0.3, 0.0, 0.8, 0.15),    // çıkan her şey
    move: bezier(0.2, 0.0, 0.0, 1.0),     // ekranda yer değiştirme
    pop: back(1.3),                       // %6 taşma: kart, hap, cevap
    bounce: back(1.70158),                // %10 taşma: Goof zıplaması, damga
    outBack: back(1.70158),
    outBackSoft: back(1.1),
  };
  const tracks = [];
  const hooks = [];
  const idles = [];
  // keys: [[t, value, easeName], ...] — easeName, bir önceki anahtardan bu anahtara geçişin eğrisi
  function add(sel, prop, keys) {
    const els = typeof sel === 'string' ? document.querySelectorAll(sel) : [sel];
    els.forEach(el => tracks.push({ el, prop, keys }));
  }
  // sürekli canlılık: nefes (sy), salınım (rot), süzülme (y); dönemler videonun süresine tam bölünür, döngü dikişsiz olur
  function idle(sel, o) {
    document.querySelectorAll(sel).forEach(el => idles.push({ el, o }));
  }
  function val(keys, t) {
    if (t <= keys[0][0]) return keys[0][1];
    for (let i = 1; i < keys.length; i++) {
      const [t1, v1, e] = keys[i];
      const [t0, v0] = keys[i - 1];
      if (t <= t1) {
        const p = t1 === t0 ? 1 : (t - t0) / (t1 - t0);
        return v0 + (v1 - v0) * ease[e || 'enter'](Math.max(0, Math.min(1, p)));
      }
    }
    return keys[keys.length - 1][1];
  }
  // doğal ölçüleri kaydet: 'grow' (satır içi kelime eklenir/silinir) ve 'collapse' (blok yüksekliği kapanır) için
  function measure() {
    const seen = new Set();
    for (const tr of tracks) {
      if (seen.has(tr.el) || (tr.prop !== 'grow' && tr.prop !== 'collapse')) continue;
      seen.add(tr.el);
      const el = tr.el;
      // ilk ölçümde öğenin kendi satır içi değerlerini sakla; motor yalnızca bunlara geri döner (kenar boşlukları silinmez)
      if (!el._orig) el._orig = { maxWidth: el.style.maxWidth, marginRight: el.style.marginRight, height: el.style.height,
                                  marginBottom: el.style.marginBottom, minHeight: el.style.minHeight, overflow: el.style.overflow };
      Object.assign(el.style, el._orig);
    }
    for (const el of seen) {
      const cs = getComputedStyle(el);
      el._nw = el.offsetWidth;
      el._mr = parseFloat(cs.marginRight) || 0;
      el._nh = el.offsetHeight;
      el._gap = parseFloat(getComputedStyle(el.parentElement).rowGap) || 0;
    }
  }
  function seek(t) {
    const state = new Map();
    for (const tr of tracks) {
      if (!state.has(tr.el)) state.set(tr.el, {});
      state.get(tr.el)[tr.prop] = val(tr.keys, t);
    }
    for (const { el, o } of idles) {
      if (!state.has(el)) state.set(el, {});
      const s = state.get(el);
      const TAU = Math.PI * 2;
      if (o.float) s.y = (s.y ?? 0) + o.float[0] * Math.sin(TAU * t / o.float[1]);
      if (o.breath) { const k = 1 + o.breath[0] * Math.sin(TAU * t / o.breath[1]); s.sy = (s.sy ?? 1) * k; s.sx = (s.sx ?? 1) / k; }
      if (o.sway) s.rot = (s.rot ?? 0) + o.sway[0] * Math.sin(TAU * t / o.sway[1] + 0.7);
    }
    for (const [el, s] of state) {
      const has = k => s[k] !== undefined;
      if (has('x') || has('y') || has('scale') || has('sx') || has('sy') || has('rot')) {
        const tx = s.x ?? 0, ty = s.y ?? 0, sc = s.scale ?? 1, sx = s.sx ?? 1, sy = s.sy ?? 1, rot = s.rot ?? 0;
        el.style.transform = `translate(${tx}px, ${ty}px) rotate(${rot}deg) scale(${sc * sx}, ${sc * sy})`;
      }
      if (has('opacity')) el.style.opacity = Math.max(0, Math.min(1, s.opacity));
      if (has('w')) el.style.width = `${s.w}%`;
      if (has('blur')) el.style.filter = s.blur > 0.05 ? `blur(${s.blur}px)` : 'none';
      if (has('strike')) el.style.setProperty('--strike', `${s.strike}%`);
      if (has('grow')) {
        if (el._nw === undefined) measure();
        const g = Math.max(0, Math.min(1, s.grow));
        el.style.maxWidth = g >= 0.999 ? el._orig.maxWidth : `${g * el._nw}px`;
        el.style.marginRight = g >= 0.999 ? el._orig.marginRight : `${g * el._mr}px`;
      }
      if (has('collapse')) {
        if (el._nh === undefined) measure();
        const c = Math.max(0, Math.min(1, s.collapse));
        const o = el._orig;
        el.style.height = c <= 0.001 ? o.height : `${(1 - c) * el._nh}px`;
        el.style.marginBottom = c <= 0.001 ? o.marginBottom : `${-c * el._gap}px`;
        el.style.minHeight = c <= 0.001 ? o.minHeight : '0px';   // esnek kutu öğesi içeriğinden küçülebilsin
        el.style.overflow = c <= 0.001 ? o.overflow : 'hidden';
      }
      for (const k in s) if (k.startsWith('--')) el.style.setProperty(k, s[k]);
    }
    for (const h of hooks) h(t);
  }
  return { add, idle, seek, measure, ease, hook: f => hooks.push(f) };
})();

// Kalite denetimi: güvenli alan, çakışma, yazı boyu, taşma. Her örnek anda görünen öğeler ölçülür.
// Her ihlal {t, kind: 'zone'|'size', msg}; sığdırma yalnızca 'zone' ihlallerini çözmek için yazıyı küçültür.
window.QC = (() => {
  const Z = { x0: 72, x1: 1008, y0: 270, y1: 1250, railY: 1150, railX: 930, bodyY: 1500, bodyX: 850 };
  function opacityOf(el) {
    let o = 1;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) o *= parseFloat(getComputedStyle(e).opacity);
    return o;
  }
  const r4 = r => ({ l: r.left, t: r.top, r: r.right, b: r.bottom });
  const R = b => `(${Math.round(b.l)},${Math.round(b.t)})-(${Math.round(b.r)},${Math.round(b.b)})`;
  function inZone(b, name, out, t, tol = 2) {
    if (b.l < Z.x0 - tol || b.r > Z.x1 + tol || b.t < Z.y0 - tol || b.b > Z.y1 + tol)
      out.push({ t, kind: 'zone', msg: `${name}: güvenli alan dışı ${R(b)}` });
    else if (b.b > Z.railY + tol && b.r > Z.railX + tol)
      out.push({ t, kind: 'zone', msg: `${name}: sağ alt düğmelerin altında ${R(b)}` });
  }
  function label(el) { return (el.id ? '#' + el.id : (el.className || el.tagName).toString().split(' ')[0]) + ' «' + (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 28) + '»'; }
  function at(t, reel) {
    const out = [];
    E.seek(t);
    const boxes = [];
    if (reel) {
      document.querySelectorAll('.ess').forEach(el => {
        if (opacityOf(el) < 0.6) return;
        const b = r4(el.getBoundingClientRect());
        if (b.r - b.l < 2 || b.b - b.t < 2) return;
        inZone(b, label(el), out, t);
        if (el.scrollWidth > el.clientWidth + 3 && getComputedStyle(el).overflow !== 'visible') out.push({ t, kind: 'zone', msg: `${label(el)}: yazı taşıyor` });
        if (opacityOf(el) > 0.97) boxes.push({ el, b });
      });
      document.querySelectorAll('.goofbox').forEach(el => {
        if (opacityOf(el) < 0.6) return;
        const r = el.getBoundingClientRect(), w = r.width, h = r.height;
        // Goof 2.0: gözler ve yanaklar kutunun yatayda %25–75, dikeyde %34–66 bölgesinde
        const face = { l: r.left + 0.25 * w, r: r.right - 0.25 * w, t: r.top + 0.34 * h, b: r.top + 0.66 * h };
        inZone(face, `Goof yüzü #${el.id}`, out, t);
        const body = { l: r.left + 0.18 * w, r: r.right - 0.18 * w, b: r.top + 0.92 * h };
        if (body.b > Z.bodyY) out.push({ t, kind: 'zone', msg: `Goof gövdesi çok aşağıda #${el.id}` });
        if (body.b > Z.y1 && body.r > Z.bodyX + 60) out.push({ t, kind: 'zone', msg: `Goof gövdesi sağ alt köşede #${el.id}` });
        if (opacityOf(el) > 0.97) boxes.push({ el, b: face, goof: true });
      });
      for (let i = 0; i < boxes.length; i++)
        for (let j = i + 1; j < boxes.length; j++) {
          const A = boxes[i], B = boxes[j];
          if (A.el.contains(B.el) || B.el.contains(A.el)) continue;
          const ix = Math.min(A.b.r, B.b.r) - Math.max(A.b.l, B.b.l), iy = Math.min(A.b.b, B.b.b) - Math.max(A.b.t, B.b.t);
          if (ix > 4 && iy > 4) out.push({ t, kind: 'zone', msg: `çakışma: ${A.goof ? 'Goof #' + A.el.id : label(A.el)} × ${B.goof ? 'Goof #' + B.el.id : label(B.el)}` });
        }
    }
    // yazı boyu: görünür her yazı ≥32 px, data-min verilmişse ondan büyük; carousel'da yazılar kenardan ≥72 px içeride
    document.querySelectorAll('body *').forEach(el => {
      if (el.closest('script,style')) return;
      const own = [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
      if (!own || opacityOf(el) < 0.6) return;
      const fs = parseFloat(getComputedStyle(el).fontSize);
      const min = parseFloat(el.closest('[data-min]')?.dataset.min || 32);
      if (fs < min - 0.5) out.push({ t, kind: 'size', msg: `küçük yazı ${Math.round(fs)} px < ${min}: ${label(el)}` });
      if (!reel) {
        const r = el.getBoundingClientRect();
        if (r.left < 70 || r.right > document.documentElement.clientWidth - 70 || r.bottom > document.documentElement.clientHeight - 60)
          out.push({ t, kind: 'zone', msg: `kenara yakın yazı: ${label(el)} ${R(r4(r))}` });
      }
    });
    return out;
  }
  function scan(times, reel = true) {
    const all = [];
    for (const t of times) all.push(...at(t, reel));
    E.seek(0);
    // aynı ihlali bir kez, ilk görüldüğü anla raporla
    const seen = new Map();
    for (const v of all) if (!seen.has(v.msg)) seen.set(v.msg, v);
    return [...seen.values()].map(v => ({ ...v, msg: `${v.t.toFixed(1)} sn ${v.msg}` }));
  }
  // sığdırma: alan ihlali kalmayana dek yazı ölçeğini (--k) küçült; küçültme yazıyı tabanın altına düşürürse dur
  function fit(times, steps = [1, 0.96, 0.92, 0.88]) {
    let first = null, best = null;
    for (const k of steps) {
      document.documentElement.style.setProperty('--k', k);
      E.measure();
      const v = scan(times);
      if (!first) first = { k, v };
      const zone = v.filter(x => x.kind === 'zone'), size = v.filter(x => x.kind === 'size');
      if (!zone.length) { best = { k, v }; break; }
      if (size.length) break;
    }
    const res = best || first;
    document.documentElement.style.setProperty('--k', res.k);
    E.measure();
    E.seek(0);
    return { k: res.k, v: res.v.map(x => x.msg) };
  }
  function frame0(sels) {
    E.seek(0);
    const bad = [];
    for (const s of sels) document.querySelectorAll(s).forEach(el => { if (opacityOf(el) < 0.99) bad.push(s); });
    return bad;
  }
  return { at, scan, fit, frame0, Z };
})();
