#!/usr/bin/env python3
"""LINGOOF studio v4: içerik planından (content.json) Reels, kapak ve carousel üretir.

Kurallar uretim_kalitesi.md §5'ten (üretim kılavuzu):
- 0. kare tam bir kanca: kanca yazısı, içerik ve Goof ilk karede görünür; ilk cevap ≤4 sn.
- Okunması gereken her şey x 72–1008, y 270–1250 içinde; 1150'nin altında sağ kenar ≤930 (Instagram düğmeleri).
- Yazı: kanca 116, İngilizce cümle 64–68, Türkçe açıklama 52 px; hiçbir yazı 32 px'ten küçük değil.
- Renk: lacivert/krem zemin, lila vurgu, nane yeşili doğru, pembe-kırmızı yanlış. Goof mor zemine konmaz.
- Hareket: Material eğrileri; Goof hep canlı (nefes, salınım, süzülme, tepki pozları).
- Ses: her görsel vuruşta efekt; müzikli sürüm −14 LUFS, tepe ≤ −1,5 dBTP; müzik açıklamadan önce kısılır.
- Kodlama: H.264 High, BT.709 etiketli, 48 kHz AAC, moov başta, düzenleme listesi yok.
- Kalite kapısı: güvenli alan, çakışma, yazı boyu, okuma süresi, ilk kare, dosya özellikleri, ses yüksekliği.

Çıktılar (out/<id>/):
  reels.mp4          yalnızca efektler; Instagram'ın lisanslı müziği yayında API ile eklenir
  reels_muzikli.mp4  efektler + yedek fon müziği (müzik eklenemezse bot bunu kullanır)
  kapak.jpg          kapak (1080×1920)
  01.jpg …           carousel slaytları (1080×1350)
  qc.json            kalite kapısı sonucu

Kullanım: python3 render.py content.json [id ...]
"""
import difflib
import functools
import hashlib
import html
import http.server
import io
import json
import re
import struct
import subprocess
import sys
import threading
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms
from playwright.sync_api import sync_playwright

import sfx

STUDIO = Path(__file__).resolve().parent
TMP = STUDIO / 'tmp'
OUT = STUDIO / 'out'
PORT = 8765
FPS = 30
W, H = 1080, 1920
CW, CH = 1080, 1350
_server = None
SRGB = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()


def serve():
    global _server
    if _server:
        return

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    _server = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), functools.partial(Quiet, directory=str(STUDIO)))
    threading.Thread(target=_server.serve_forever, daemon=True).start()


def _font_links():
    local = STUDIO / 'fonts' / 'dm-sans'
    if local.exists():                      # depoda taşınan kopya (zamanlanmış görevler npm'siz çalışsın)
        return '<link rel="stylesheet" href="/fonts/dm-sans/dm-sans.css">'
    return ''.join(f'<link rel="stylesheet" href="/node_modules/@fontsource/dm-sans/{w}.css">' for w in (400, 500, 600, 700, 800))


def doc(body, script, w=W, h=H, theme='night'):
    return f'''<!doctype html><html lang="tr"><head><meta charset="utf-8">{_font_links()}
<link rel="stylesheet" href="/base.css"><style>:root{{--W:{w}px;--H:{h}px}}</style>
<script src="/engine.js"></script></head><body class="{theme}">{body}
<script>{script}
document.fonts.ready.then(() => Promise.all([...document.images].map(i => i.complete ? 1 : new Promise(r => {{ i.onload = r; i.onerror = r; }}))))
  .then(() => {{ E.measure(); E.seek(0); window.READY = true; }});
</script></body></html>'''


def esc(s):
    return html.escape(s, quote=False)


def js(v):
    return json.dumps(v, ensure_ascii=False)


def plain(s):
    return re.sub(r'<[^>]+>', '', html.unescape(s)).strip()


# ---------- okuma süresi (kılavuz §5.4) ----------

def hold_tr(text):
    return max(1.0, 0.4 + len(plain(text)) / 15)


def hold_en(text):
    return max(1.3, 0.5 + len(plain(text)) / 12)


F = 1 / FPS                     # bir kare (saniye)


def r3(x):
    return round(x, 3)


# ---------- anahtar kare yardımcıları ----------

def show(t_in, t_out=None, kind='pop', d_in=9 * F, d_out=6 * F):
    """Giriş/çıkış: pop (y +40→0, ölçek 0,94→1, %6 taşma), up (y +40→0), fade. t_in ≤ 0: ilk karede hazır."""
    k = {}
    if t_in <= 0:
        k['opacity'] = [[0, 1]]
    else:
        k['opacity'] = [[0, 0], [t_in, 0], [r3(t_in + 4 * F), 1, 'enter']]
        if kind in ('pop', 'up'):
            k['y'] = [[0, 40], [t_in, 40], [r3(t_in + d_in), 0, 'enter']]
        if kind == 'pop':
            k['scale'] = [[0, 0.94], [t_in, 0.94], [r3(t_in + d_in), 1, 'pop']]
    if t_out is not None:
        k['opacity'] += [[t_out, 1], [r3(t_out + d_out), 0, 'exit']]
        k.setdefault('y', [[0, 0]])
        k['y'] += [[t_out, 0], [r3(t_out + d_out), -24, 'exit']]
    return k


def collapse(t_close, t_open=None, d=10 * F):
    """Bloğun yüksekliğini kapatır (alttakiler yukarı kayar); t_open'da geri açar. Opaklık da birlikte."""
    c = [[0, 0], [t_close, 0], [r3(t_close + d), 1, 'move']]
    o = [[0, 1], [t_close, 1], [r3(t_close + 6 * F), 0, 'exit']]
    if t_open is not None:
        t_open = r3(t_open + 6 * F)            # önce çıkanlar kaybolsun, sonra blok geri açılsın (geçişte çakışma olmaz)
        c += [[t_open, 1], [r3(t_open + d), 0, 'move']]
        o += [[r3(t_open + 3 * F), 0], [r3(t_open + d), 1, 'enter']]
    return {'collapse': c, 'opacity': o}


def shake(t, amp=12, frames=9):
    """3 sönümlü salınım, 9 kare."""
    k = [[0, 0], [t, 0]]
    n = 6
    for i in range(1, n + 1):
        k.append([r3(t + frames * F * i / n), 0 if i == n else (amp if i % 2 else -amp) * (1 - i / n), 'inOutSine'])
    return k


def squash(times):
    """Poz değişiminde ezilip uzama (alan korunur): 2 kare öncü, iniş, geri sekme, oturma."""
    sx, sy = [[0, 1]], [[0, 1]]
    for t in times:
        sy += [[r3(t - 2 * F), 1], [t, 0.96, 'inOutSine'], [r3(t + 3 * F), 1.08, 'enter'], [r3(t + 9 * F), 1, 'inOutSine']]
        sx += [[r3(t - 2 * F), 1], [t, 1 / 0.96, 'inOutSine'], [r3(t + 3 * F), 1 / 1.08, 'enter'], [r3(t + 9 * F), 1, 'inOutSine']]
    return {'sx': sx, 'sy': sy}


def hop(t, h=40):
    return [[0, 0], [t, 0], [r3(t + 5 * F), -h, 'enter'], [r3(t + 11 * F), 0, 'inCubic']]


def poses(seq):
    """seq: [(t, 'goof_x'), ...] → (katman adları, her katman için opaklık anahtarları). Geçişler anlık; ezilme maskeler."""
    names = []
    for _, p in seq:
        if p not in names:
            names.append(p)
    out = {}
    for p in names:
        keys = [[0, 1 if seq[0][1] == p else 0]]
        for t, q in seq[1:]:
            keys += [[r3(t - 0.001), keys[-1][1], 'step'], [t, 1 if q == p else 0, 'step']]
        out[p] = keys
    return names, out


def idle_js(sel, dur):
    """Nefes ±%2 (~2,6 sn), salınım ±1,5° (~4,2 sn), süzülme ±6 px (~3 sn); dönemler süreye tam bölünür."""
    def per(p0):
        return dur / max(1, round(dur / p0))
    return f'E.idle({js(sel)}, {{breath: [0.02, {per(2.6):.4f}], sway: [1.5, {per(4.2):.4f}], float: [6, {per(3.0):.4f}]}});'


def beats(t_from, t_to, step=1.9):
    """Uzun okuma beklemesinde ara vuruş anları (≤3 sn olaysız aralık kuralı)."""
    out, t = [], t_from
    while t < t_to - 0.5:
        out.append(r3(t))
        t += step
    return out


def with_beats(seq, times, cycle):
    """Poz dizisine ara vuruşları ekler (sırayı korur)."""
    seq = list(seq) + [(t, cycle[i % len(cycle)]) for i, t in enumerate(times)]
    return sorted(seq, key=lambda x: x[0])


def tracks_js(tracks):
    lines = []
    for sel, props in tracks:
        for prop, keys in props.items():
            lines.append(f'E.add({js(sel)}, {js(prop)}, {js(keys)});')
    return '\n'.join(lines)


# ---------- HTML parçaları ----------

CHECK = '<svg viewBox="0 0 24 24"><path d="M4 12.5l5 5L20 6.5" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/></svg>'
CROSS = '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round"/></svg>'


def top(badge):
    return (f'<div class="top"><div class="badge">{badge}</div>'
            f'<div class="brand"><img src="/goof/goof_avatar.png">LINGOOF</div></div>')


def goof(names, size, gid='goof', style=''):
    imgs = ''.join(f'<img id="{gid}_{n}" src="/goof/{n}.png">' for n in names)
    return (f'<div class="goofbox" id="{gid}" style="width:{size}px;height:{size}px;{style}">'
            f'<div class="shadow"></div>{imgs}</div>')


def say(text, tail=True, avatar=False, style='', sid='say'):
    av = '<img class="av" src="/goof/goof_avatar.png">' if avatar else ''
    return f'<div class="say ess{" tail" if tail else ""}" id="{sid}" data-min="46" style="{style}">{av}<div>{text}</div></div>'


def diff_tokens(wrong, fix):
    a, b = wrong.split(), fix.split()
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == 'equal':
            out += [('eq', w) for w in a[i1:i2]]
        if op in ('delete', 'replace'):
            out += [('bad', w) for w in a[i1:i2]]
        if op in ('insert', 'replace'):
            out += [('good', w) for w in b[j1:j2]]
    return out


def sentence_html(tokens, size=None):
    parts = []
    for i, (kind, w) in enumerate(tokens):
        cls = {'eq': 'tok', 'bad': 'tok bad grow', 'good': 'tok good grow'}[kind]
        if i == len(tokens) - 1:
            cls += ' end'
        deco = '<span class="mk"></span>'
        if kind == 'bad':
            deco += '<span class="wave"></span><span class="strike"></span>'
        parts.append(f'<span class="{cls}" id="tk{i}">{deco}{esc(w)}</span>')
    st = f' style="font-size:calc(var(--k) * {size}px)"' if size else ''
    return f'<div class="sent" data-min="52"{st}>{"".join(parts)}</div>'


def bg_track(dur):
    return ('#bg', {'scale': [[0, 1], [r3(dur / 2), 1.035, 'inOutSine'], [r3(dur), 1, 'inOutSine']]})


class Reel:
    """Şablonların döndürdüğü sahne: gövde, betik, süre, ses işaretleri, kapak, denetim bilgisi."""

    def __init__(self, body, script, dur, cues, theme, payoff, cover, dips=(), f0=('#hook', '#goof'), notes=()):
        self.body, self.script, self.dur, self.cues, self.theme = body, script, dur, cues, theme
        self.payoff, self.cover, self.dips, self.f0, self.notes = payoff, cover, list(dips), list(f0), list(notes)


# ---------- Reels şablonları ----------

def t_hata(s):
    """Hata Avı: 3 sn sayaç → yanlış kelime kırmızı, dalgalı çizgi → kelime yerinde düzelir → Goof Türkçe açıklar."""
    theme = s.get('theme', 'night')
    toks = diff_tokens(s['wrong'], s['fix'])
    bad = [i for i, (k, _) in enumerate(toks) if k == 'bad']
    good = [i for i, (k, _) in enumerate(toks) if k == 'good']
    T_FLIP, T_FIX, T_SAY = 3.0, 3.5, 4.4
    expl = s['explain']
    t_end = max(T_SAY + 0.3 + hold_tr(expl) + 0.4, T_FIX + 0.3 + hold_en(s['fix']) + hold_tr(expl))
    T_BACK = r3(t_end)
    dur = r3(T_BACK + 0.7)
    xb = beats(r3(T_SAY + 1.9), T_BACK)
    names, pk = poses(with_beats([(0, 'goof_focus'), (1.5, 'goof_pose_look_up'), (T_FLIP, 'goof_alert'), (T_FIX + 0.2, 'goof_hype'),
                                  (T_SAY, 'goof_pose_point_right'), (T_BACK, 'goof_focus')], xb, ['goof_proud', 'goof_calm']))
    inner = (f'<div class="hook" id="hook" data-min="96" style="--hs:{s.get("hook_size", 124)}px">{s.get("hook", "Bu cümlede<br><em>1 hata</em> var.")}</div>'
             f'<div class="slot" id="mid"><div class="timer" id="timer"><div class="bar" id="bar"></div></div>'
             f'<div class="pill ok" id="okp">{CHECK} DOĞRUSU</div></div>'
             f'<div class="card ess" id="card" style="margin:0 14px">{sentence_html(toks, s.get("sent_size"))}</div>'
             f'<div class="row" id="row">{goof(names, 380, style="margin-left:-34px")}'
             f'{say(expl, style="flex:1;margin-top:26px")}</div>')
    body = '<div class="bg" id="bg"></div>' + f'<div class="stack" id="stack">{top(s.get("badge", "HATA AVI"))}{inner}</div>'
    tr = [
        bg_track(dur),
        ('#hook', {**collapse(T_FIX, T_BACK), 'scale': [[0, 1.04], [r3(6 * F), 1, 'enter']]}),
        ('#bar', {'w': [[0, 100], [T_FLIP, 0, 'linear'], [T_BACK, 0], [r3(T_BACK + 0.5), 100, 'move']]}),
        ('#timer', {'opacity': [[0, 1], [T_FLIP, 1], [r3(T_FLIP + 4 * F), 0, 'exit'], [T_BACK, 0], [r3(T_BACK + 6 * F), 1, 'enter']]}),
        ('#okp', {**show(T_FIX, T_BACK), 'x': [[0, 0]]}),
        ('#card', {'x': shake(T_FLIP)}),
        ('#say', show(T_SAY, T_BACK, 'up')),
        ('#goof', {**squash([1.5, T_FLIP, T_FIX + 0.2, T_SAY] + xb + [T_BACK]), 'y': hop(T_FIX + 0.2, 34)}),
    ]
    for i in bad:
        tr.append((f'#tk{i}', {
            '--on': [[0, 0], [T_FLIP, 0], [r3(T_FLIP + F), 1, 'linear'], [T_BACK, 1], [r3(T_BACK + 4 * F), 0, 'linear']],
            '--mk': [[0, 0], [T_FLIP, 0], [r3(T_FLIP + 3 * F), 1, 'enter'], [T_FIX, 1], [r3(T_FIX + 6 * F), 0, 'exit']],
            '--draw': [[0, 0], [T_FLIP, 0], [r3(T_FLIP + 8 * F), 1, 'linear'], [T_BACK, 1], [r3(T_BACK + 4 * F), 0, 'linear']],
            'strike': [[0, 0], [r3(T_FLIP + 4 * F), 0], [r3(T_FLIP + 10 * F), 100, 'linear'], [T_BACK, 100], [r3(T_BACK + 4 * F), 0, 'linear']],
            'grow': [[0, 1], [T_FIX, 1], [r3(T_FIX + 8 * F), 0, 'move'], [r3(T_BACK + 4 * F), 0], [r3(T_BACK + 12 * F), 1, 'move']],
            'opacity': [[0, 1], [T_FIX, 1], [r3(T_FIX + 6 * F), 0, 'exit'], [r3(T_BACK + 4 * F), 0], [r3(T_BACK + 12 * F), 1, 'enter']],
        }))
    for i in good:
        tg = r3(T_FIX + 3 * F)
        tr.append((f'#tk{i}', {
            'grow': [[0, 0], [tg, 0], [r3(tg + 8 * F), 1, 'move'], [T_BACK, 1], [r3(T_BACK + 8 * F), 0, 'move']],
            'opacity': [[0, 0], [r3(tg + 3 * F), 0], [r3(tg + 8 * F), 1, 'enter'], [T_BACK, 1], [r3(T_BACK + 5 * F), 0, 'exit']],
            '--mk': [[0, 0], [r3(tg + 6 * F), 0], [r3(tg + 12 * F), 1, 'enter'], [T_BACK, 1], [r3(T_BACK + 4 * F), 0, 'exit']],
            'scale': [[0, 1], [r3(tg + 6 * F), 1], [r3(tg + 9 * F), 1.08, 'enter'], [r3(tg + 15 * F), 1, 'pop']],
        }))
    tr += [(f'#goof_{n}', {'opacity': k}) for n, k in pk.items()]
    script = tracks_js(tr) + idle_js('#goof', dur)
    cues = [(0.02, sfx.pop2(0.9, 0.45)), (1.0, sfx.tick2(0.3, 1)), (1.5, sfx.boing(0.18)), (2.0, sfx.tick2(0.3, 2)),
            (T_FLIP, sfx.buzz2()), (r3(T_FIX - 0.1), sfx.whoosh2(0.3, 0.2)), (r3(T_FIX + 0.4), sfx.chime(0.4)),
            (T_SAY, sfx.pop2(1.1, 0.35)), (r3(T_BACK - 0.05), sfx.whoosh2(0.35, 0.18, up=False))]
    cues += [(x, sfx.boing(0.12) if i % 2 == 0 else sfx.tick2(0.18, i)) for i, x in enumerate(xb)]
    cover = cover_html(theme, s.get('badge', 'HATA AVI'), s.get('cover', 'Bu cümlede<br><em>hata</em> var'),
                       f'<div class="card" style="padding:40px 48px">{sentence_html([("eq", w) for w in s["wrong"].split()])}</div>', 'goof_alert')
    return Reel(body, script, dur, cues, theme, T_FIX + 0.4, cover, dips=[T_FLIP, T_SAY])


def t_quiz(s):
    """3 Saniye Testi: iki seçenek, sayaç; doğru seçenek nane yeşili, yanlış kapanır, Goof açıklar."""
    theme = s.get('theme', 'night')
    opts, ans = s['options'], s['answer']
    T_REV, T_COL, T_SAY = 3.0, 3.6, 4.3
    expl = s['explain']
    t_end = max(T_SAY + 0.3 + hold_tr(expl) + 0.4, T_REV + 0.3 + hold_en(opts[ans]) + hold_tr(expl))
    T_BACK = r3(t_end)
    dur = r3(T_BACK + 0.7)
    xb = beats(r3(T_SAY + 1.9), T_BACK)
    names, pk = poses(with_beats([(0, 'goof_focus'), (1.5, 'goof_pose_look_down'), (T_REV, 'goof_celebrate'), (T_SAY, 'goof_proud'),
                                  (T_BACK, 'goof_focus')], xb, ['goof_calm', 'goof_proud']))
    keys = 'ABC'
    opt_html = ''.join(
        f'<div class="opt ess" id="o{i}" data-min="52" style="margin:0 106px 0 28px"><span class="key" data-min="32">{keys[i]}</span><span>{esc(o)}</span></div>'
        for i, o in enumerate(opts))
    inner = (f'<div class="hook" id="hook" data-min="96" style="--hs:{s.get("hook_size", 124)}px">{s["hook"]}</div>'
             f'<div class="row" id="trow" style="align-items:center"><div class="slot" style="flex:1">'
             f'<div class="timer" id="timer"><div class="bar" id="bar"></div></div>'
             f'<div class="pill ok" id="okp">{CHECK} DOĞRU CEVAP: {keys[ans]}</div></div>'
             f'{goof(names, 290, style="margin-right:40px")}</div>'
             f'<div id="opts" style="display:flex;flex-direction:column;row-gap:18px">{opt_html}</div>'
             f'{say(expl, tail=False, avatar=True, style="margin-right:78px")}')
    body = '<div class="bg" id="bg"></div>' + f'<div class="stack" id="stack">{top(s.get("badge", "3 SANİYE TESTİ"))}{inner}</div>'
    wrong = [i for i in range(len(opts)) if i != ans]
    tr = [
        bg_track(dur),
        ('#hook', {**collapse(T_COL, T_BACK), 'scale': [[0, 1.04], [r3(6 * F), 1, 'enter']]}),
        ('#bar', {'w': [[0, 100], [T_REV, 0, 'linear'], [T_BACK, 0], [r3(T_BACK + 0.5), 100, 'move']]}),
        ('#timer', {'opacity': [[0, 1], [T_REV, 1], [r3(T_REV + 4 * F), 0, 'exit'], [T_BACK, 0], [r3(T_BACK + 6 * F), 1, 'enter']]}),
        ('#okp', show(T_REV, T_BACK)),
        (f'#o{ans}', {'scale': [[0, 1], [r3(T_REV - 3 * F), 1], [T_REV, 0.96, 'inOutSine'], [r3(T_REV + 6 * F), 1.06, 'bounce'], [r3(T_REV + 12 * F), 1, 'enter']],
                      '--okv': [[0, 0], [T_REV, 0], [r3(T_REV + F), 1, 'linear'], [T_BACK, 1], [r3(T_BACK + F), 0, 'linear']]}),
        ('#say', show(T_SAY, T_BACK, 'up')),
        ('#goof', {**squash([1.5, T_REV, T_SAY] + xb + [T_BACK]), 'y': hop(T_REV, 40)}),
    ]
    for i in wrong:
        tr.append((f'#o{i}', {
            'opacity': [[0, 1], [T_REV, 1], [r3(T_REV + 4 * F), 0.35, 'exit'], [T_COL, 0.35], [r3(T_COL + 6 * F), 0, 'exit'],
                        [r3(T_BACK + 9 * F), 0], [r3(T_BACK + 16 * F), 1, 'enter']],
            'collapse': [[0, 0], [T_COL, 0], [r3(T_COL + 10 * F), 1, 'move'], [r3(T_BACK + 6 * F), 1], [r3(T_BACK + 16 * F), 0, 'move']],
            'x': shake(r3(T_REV + 2 * F), 10)}))
    tr += [(f'#goof_{n}', {'opacity': k}) for n, k in pk.items()]
    script = tracks_js(tr) + idle_js('#goof', dur) + f"""
E.hook(t => {{ const o = document.getElementById('o{ans}'); const v = parseFloat(o.style.getPropertyValue('--okv') || 0);
  o.classList.toggle('ok', v > 0.5); }});"""
    cues = [(0.02, sfx.pop2(0.9, 0.45)), (1.0, sfx.tick2(0.3, 1)), (1.5, sfx.boing(0.16)), (2.0, sfx.tick2(0.3, 2)),
            (T_REV, sfx.chime(0.42)), (r3(T_COL - 0.05), sfx.whoosh2(0.3, 0.18)), (T_SAY, sfx.pop2(1.1, 0.35)),
            (r3(T_BACK - 0.05), sfx.whoosh2(0.35, 0.18, up=False))]
    cues += [(x, sfx.tick2(0.18, i)) for i, x in enumerate(xb)]
    teaser = ''.join(f'<div class="opt" style="margin-top:18px"><span class="key" data-min="32">{keys[i]}</span><span>{esc(o)}</span></div>' for i, o in enumerate(opts))
    cover = cover_html(theme, s.get('badge', '3 SANİYE TESTİ'), s.get('cover', plain(s['hook'])), f'<div>{teaser}</div>', 'goof_focus')
    return Reel(body, script, dur, cues, theme, T_REV, cover, dips=[T_REV, T_SAY])


def t_pov(s):
    """POV sohbet: karşı taraf yazar → ders kitabı cevabı → Goof utanır → native cevap gelir → Goof açıklar."""
    theme = s.get('theme', 'night')
    T_DOTS, T_WRONG, T_BUZZ, T_SWAP, T_SAY = 0.6, 1.2, 2.3, 3.1, 4.1
    expl = s['explain']
    t_end = max(T_SAY + 0.3 + hold_tr(expl) + 0.4, T_SWAP + 0.3 + hold_en(s['right']) + hold_tr(expl) * 0.8)
    T_BACK = r3(t_end)
    dur = r3(T_BACK + 0.7)
    xb = beats(r3(T_SAY + 1.9), T_BACK)
    names, pk = poses(with_beats([(0, 'goof_pose_look_up'), (T_WRONG, 'goof_sleepy'), (T_BUZZ, 'goof_pose_facepalm'), (T_SWAP, 'goof_celebrate'),
                                  (T_SAY, 'goof_proud'), (T_BACK, 'goof_pose_look_up')], xb, ['goof_calm', 'goof_proud']))
    inner = (f'<div class="hook" id="hook" data-min="96" style="--hs:{s.get("hook_size", 108)}px">{s["hook"]}</div>'
             f'<div class="row" id="r1" style="justify-content:space-between">'
             f'<div style="display:flex;flex-direction:column;row-gap:14px;padding-top:24px;max-width:600px">'
             f'<div class="who">{esc(s["them_name"])}</div><div class="bubble them ess" id="them" data-min="52">{esc(s["them"])}</div></div>'
             f'{goof(names, 310, style="margin-right:-10px")}</div>'
             f'<div class="slot" id="reply" style="justify-items:end;margin-right:78px">'
             f'<div class="bubble me" id="dots" style="letter-spacing:12px">• • •</div>'
             f'<div class="bubble me ess" id="wrong" data-min="52" style="max-width:760px"><span class="label" data-min="32">{s.get("wrong_tag", "DERS KİTABI CEVABI")}</span>{esc(s["wrong"])}</div>'
             f'<div class="bubble good ess" id="right" data-min="52" style="max-width:760px"><span class="label" data-min="32">{s.get("right_tag", "NATIVE CEVABI")}</span>{esc(s["right"])}</div></div>'
             f'{say(expl, tail=False, avatar=True, style="margin-right:78px")}')
    body = '<div class="bg" id="bg"></div>' + f'<div class="stack" id="stack">{top(s.get("badge", "POV"))}{inner}</div>'
    tr = [
        bg_track(dur),
        ('#hook', {**collapse(T_SWAP, T_BACK), 'scale': [[0, 1.04], [r3(6 * F), 1, 'enter']]}),
        ('#dots', show(T_DOTS, r3(T_WRONG - 0.12), 'pop', d_out=3 * F)),
        ('#wrong', {**show(T_WRONG, r3(T_SWAP - 0.05), 'pop'), 'x': shake(T_BUZZ, 12)}),
        ('#right', show(T_SWAP, T_BACK, 'pop')),
        ('#say', show(T_SAY, T_BACK, 'up')),
        ('#goof', {**squash([T_WRONG, T_BUZZ, T_SWAP, T_SAY] + xb + [T_BACK]), 'y': hop(T_SWAP, 40)}),
    ]
    tr += [(f'#goof_{n}', {'opacity': k}) for n, k in pk.items()]
    script = tracks_js(tr) + idle_js('#goof', dur)
    cues = [(0.02, sfx.pop2(0.85, 0.42)), (T_DOTS, sfx.type_clicks(6, 0.08, 0.5)), (T_WRONG, sfx.pop2(0.8, 0.4)), (T_BUZZ, sfx.buzz2()),
            (r3(T_SWAP - 0.08), sfx.whoosh2(0.3, 0.18)), (r3(T_SWAP + 0.2), sfx.chime(0.42)), (T_SAY, sfx.pop2(1.1, 0.35)),
            (r3(T_BACK - 0.05), sfx.whoosh2(0.35, 0.18, up=False))]
    cues += [(x, sfx.tick2(0.18, i)) for i, x in enumerate(xb)]
    teaser = (f'<div class="who" style="margin-bottom:14px">{esc(s["them_name"])}</div>'
              f'<div class="bubble them" style="display:inline-block">{esc(s["them"])}</div>')
    cover = cover_html(theme, s.get('badge', 'POV'), s.get('cover', plain(s['hook'])), teaser, 'goof_pose_facepalm')
    return Reel(body, script, dur, cues, theme, T_SWAP + 0.2, cover, dips=[T_BUZZ, T_SAY])


def t_nasil(s):
    """Türkçe ifade → kelimesi kelimesine çeviri (üstü çizilir) → 3 doğal karşılık → kaydet."""
    theme = s.get('theme', 'day')
    opts = s['options']
    T_X, T_LIST, STEP = 0.8, 1.7, 1.6
    t_in = [r3(T_LIST + 0.1 + STEP * i) for i in range(len(opts))]
    last = opts[-1]
    t_end = t_in[-1] + 0.3 + hold_en(last['en']) + hold_tr(last.get('tr', '')) * 0.7
    T_CTA = r3(t_in[-1] + 1.3)
    T_BACK = r3(max(t_end, T_CTA + 1.6))
    dur = r3(T_BACK + 0.7)
    na, pa = poses([(0, 'goof_oops'), (T_X, 'goof_pose_facepalm'), (T_BACK, 'goof_oops')])
    nb, pb = poses([(0, 'goof_pose_point_right'), (r3(t_in[-1]), 'goof_hype'), (T_CTA, 'goof_celebrate'), (T_BACK, 'goof_pose_point_right')])
    cards = ''.join(
        f'<div class="phrase ess" id="op{i}" data-min="40"><div class="key" data-min="32">{i + 1}</div><div><div class="en">{esc(o["en"])}</div>'
        + (f'<div class="tr">{esc(o["tr"])}</div>' if o.get('tr') else '') + '</div></div>'
        for i, o in enumerate(opts))
    inner = (f'<div class="hook" id="hook" data-min="96" style="--hs:{s.get("hook_size", 112)}px">{s["hook"]}</div>'
             f'<div class="row" id="lrow" style="justify-content:space-between;align-items:center">'
             f'<div class="literal ess" id="lit" data-min="52" style="margin-left:14px"><div class="label err" data-min="32">KELİMESİ KELİMESİNE</div><div><span class="lt">{esc(s["literal"])}</span></div></div>'
             f'{goof(na, 310, "goofa", "margin-right:-10px")}</div>'
             f'<div id="list" style="display:flex;flex-direction:column;row-gap:18px;margin-right:78px">{cards}</div>'
             f'<div class="row" id="brow" style="align-items:center">{goof(nb, 270, "goofb", "margin-left:-24px")}'
             f'<div class="pill ok ess" id="cta" data-min="36">{esc(s.get("cta", "Kaydet, lazım olacak"))}</div></div>')
    body = '<div class="bg" id="bg"></div>' + f'<div class="stack" id="stack">{top(s.get("badge", "TÜRKÇE → İNGİLİZCE"))}{inner}</div>'
    tr = [
        bg_track(dur),
        ('#hook', {**collapse(T_LIST, T_BACK), 'scale': [[0, 1.04], [r3(6 * F), 1, 'enter']]}),
        ('#lrow', collapse(T_LIST, T_BACK)),
        ('#lit', {'x': shake(T_X, 10)}),
        ('#lit .lt', {'strike': [[0, 0], [T_X, 0], [r3(T_X + 8 * F), 100, 'linear'], [r3(T_BACK + 6 * F), 100], [r3(T_BACK + 14 * F), 0, 'linear']]}),
        ('#goofa', squash([T_X, T_BACK])),
        ('#goofb', {**show(r3(T_LIST + 8 * F), T_BACK, 'pop'), **squash([t_in[-1], T_CTA]), 'y': hop(T_CTA, 36)}),
        ('#cta', show(T_CTA, T_BACK, 'pop')),
    ]
    tr += [(f'#op{i}', show(t, T_BACK, 'up')) for i, t in enumerate(t_in)]
    tr += [(f'#goofa_{n}', {'opacity': k}) for n, k in pa.items()]
    tr += [(f'#goofb_{n}', {'opacity': k}) for n, k in pb.items()]
    script = tracks_js(tr) + idle_js('#goofa', dur) + idle_js('#goofb', dur)
    cues = [(0.02, sfx.pop2(0.9, 0.42)), (T_X, sfx.buzz2(0.32)), (r3(T_LIST - 0.05), sfx.whoosh2(0.3, 0.18))]
    cues += [(r3(t + 6 * F), sfx.pop2(1.0 + 0.12 * i, 0.4)) for i, t in enumerate(t_in)]
    cues += [(r3(T_CTA + 6 * F), sfx.chime(0.36)), (r3(T_BACK - 0.05), sfx.whoosh2(0.35, 0.18, up=False))]
    teaser = (f'<div class="literal" style="display:inline-block"><div class="label err">KELİMESİ KELİMESİNE</div>'
              f'<div><span class="lt">{esc(s["literal"])}</span></div></div>')
    cover = cover_html(theme, s.get('badge', 'TÜRKÇE → İNGİLİZCE'), s.get('cover', plain(s['hook'])), teaser, 'goof_oops')
    return Reel(body, script, dur, cues, theme, t_in[0] + 0.2, cover, dips=[t_in[0]], f0=('#hook', '#goofa', '#lit'))


def t_vs(s):
    """Türk usulü vs native: üç tur; her turda bağlam + Türk usulü cümle, sonra native karşılığı."""
    theme = s.get('theme', 'night')
    rounds = s['rounds']
    STEP = 3.4
    t0 = [r3(STEP * i) for i in range(len(rounds))]
    t_na = [r3(t + 1.3) for t in t0]
    t_end = t_na[-1] + 0.3 + max(hold_en(rounds[-1]['na']), 1.8)
    T_BACK = r3(t_end)
    dur = r3(T_BACK + 0.7)
    seq = []
    for i in range(len(rounds)):
        seq += [(t0[i] if i else 0, 'goof_sleepy' if i % 2 == 0 else 'goof_oops'), (t_na[i], 'goof_celebrate' if i % 2 == 0 else 'goof_hype')]
    seq.append((T_BACK, 'goof_sleepy'))
    names, pk = poses(seq)
    rhtml = ''
    for i, r in enumerate(rounds):
        rhtml += (f'<div id="rd{i}" style="display:flex;flex-direction:column;row-gap:18px;margin-right:78px">'
                  f'<div class="h1 ess" data-min="60" style="font-size:calc(var(--k) * 80px)">{r["ctx"]}</div>'
                  f'<div class="vs tr ess" id="tr{i}" data-min="52"><div class="label err" data-min="32">TÜRK USULÜ</div><div class="ph">{esc(r["tr"])}</div></div>'
                  f'<div class="vs na ess" id="na{i}" data-min="52"><div class="label" data-min="32">NATIVE</div><div class="ph">{esc(r["na"])}</div></div></div>')
    inner = (f'<div class="row" id="hrow" style="justify-content:space-between;align-items:center">'
             f'<div class="hook" id="hook" data-min="96" style="--hs:{s.get("hook_size", 112)}px">{s.get("hook", "Türk usulü<br>vs <em>native</em>")}</div>'
             f'{goof(names, 320, style="margin-right:-14px")}</div>'
             f'<div class="slot" id="rounds">{rhtml}</div>')
    body = '<div class="bg" id="bg"></div>' + f'<div class="stack" id="stack">{top(s.get("badge", "TÜRK USULÜ vs NATIVE"))}{inner}</div>'
    tr = [bg_track(dur), ('#hook', {'scale': [[0, 1.04], [r3(6 * F), 1, 'enter']]})]
    for i in range(len(rounds)):
        t_out = r3(t0[i + 1] - 0.15) if i + 1 < len(rounds) else T_BACK
        tr.append((f'#rd{i}', show(t0[i], t_out, 'up') if i else
                   {'opacity': [[0, 1], [t_out, 1], [r3(t_out + 6 * F), 0, 'exit'], [r3(T_BACK + 4 * F), 0], [r3(T_BACK + 12 * F), 1, 'enter']]}))
        tr.append((f'#na{i}', show(t_na[i], T_BACK if i == 0 else None, 'pop')))
    tr.append(('#goof', {**squash([t for t in t0[1:]] + t_na + [T_BACK]), 'y': hop(t_na[0], 36)}))
    tr += [(f'#goof_{n}', {'opacity': k}) for n, k in pk.items()]
    script = tracks_js(tr) + idle_js('#goof', dur)
    cues = [(0.02, sfx.pop2(0.9, 0.42))]
    for i in range(len(rounds)):
        if i:
            cues.append((r3(t0[i] - 0.1), sfx.whoosh2(0.3, 0.16)))
        cues += [(r3(t0[i] + 0.6), sfx.buzz2(0.22) if i == 0 else sfx.tick2(0.25, i)), (r3(t_na[i] + 6 * F), sfx.chime(0.36))]
    cues.append((r3(T_BACK - 0.05), sfx.whoosh2(0.35, 0.18, up=False)))
    r0 = rounds[0]
    teaser = (f'<div class="vs tr" style="margin-bottom:18px"><div class="label err">TÜRK USULÜ</div><div class="ph">{esc(r0["tr"])}</div></div>'
              f'<div class="vs na"><div class="label">NATIVE</div><div class="ph">?</div></div>')
    cover = cover_html(theme, s.get('badge', 'TÜRK USULÜ vs NATIVE'), s.get('cover', plain(s.get('hook', 'Türk usulü vs native'))), teaser, 'goof_sleepy')
    return Reel(body, script, dur, cues, theme, t_na[0] + 0.2, cover, dips=t_na[:1], f0=('#hook', '#goof', '#rd0'))


def t_urun(s):
    """Uygulamada böyle: alıştırmada yanlış seçim → Goof'un Türkçe açıklaması → uygulamanın gerçek ekranı."""
    theme = s.get('theme', 'day')
    opts = s['options']
    pick, right = s.get('pick', 1), s.get('right', 0)
    T_TAP, T_BUZZ, T_FB = 1.0, 1.2, 1.8
    expl = s['explain']
    T_S2 = r3(T_FB + 0.3 + hold_en(plain(s['fix'])) + hold_tr(expl))
    T_BACK = r3(T_S2 + 3.6)
    dur = r3(T_BACK + 0.7)
    xb = beats(r3(T_FB + 2.0), T_S2)
    names, pk = poses(with_beats([(0, 'goof_pose_look_down'), (T_BUZZ, 'goof_alert'), (T_FB, 'goof_pose_point_left'), (T_S2, 'goof_celebrate'),
                                  (T_BACK, 'goof_pose_look_down')], xb, ['goof_proud', 'goof_pose_point_left']))
    chips = ''.join(f'<span class="opt" id="c{i}" style="display:inline-flex;padding:14px 40px;margin-right:16px">{esc(o)}</span>' for i, o in enumerate(opts))
    scene1 = (f'<div id="s1" style="display:flex;flex-direction:column;row-gap:24px">'
              f'<div class="card ess" id="ex" data-min="36" style="margin-right:250px">'
              f'<div class="label" data-min="32" style="color:var(--violet)">{s.get("task", "BOŞLUĞU DOLDUR")}</div>'
              f'<div style="margin-top:14px;font:700 calc(var(--k) * 64px)/1.2 DM Sans;color:var(--navy)">{s["sentence"]}</div>'
              f'<div style="margin-top:22px;display:flex;flex-wrap:wrap;row-gap:16px">{chips}</div></div>'
              f'<div class="card ess" id="fb" data-min="46" style="background:#FFF1EC;box-shadow:0 14px 0 #F6D9CF;margin-right:78px">'
              f'<div style="font:800 calc(var(--k) * 60px)/1 Bricolage;color:#B42318">{esc(s.get("verdict", "Neredeyse!"))}</div>'
              f'<div style="margin-top:16px;font:700 calc(var(--k) * 56px)/1.2 DM Sans">{s["fix"]}</div>'
              f'<div style="margin-top:14px;font:500 calc(var(--k) * 48px)/1.3 DM Sans;color:var(--ink-2)">{expl}</div></div></div>')
    scene2 = (f'<div id="s2" style="display:flex;flex-direction:column;row-gap:26px">'
              f'<div class="h1 ess" data-min="60">{s.get("s2_title", "Hatanı <em>Türkçe</em><br>açıklayan koç")}</div>'
              f'<div class="row" style="column-gap:34px;align-items:flex-start">'
              f'<div class="phone" style="width:330px;height:640px"><div class="screen" style="background-image:url(/shots/{s.get("screen", "screen_hata.png")})"></div></div>'
              f'<div style="display:flex;flex-direction:column;row-gap:24px;padding-top:20px">'
              f'<div class="pill ok ess" data-min="36">{CHECK} iPhone\'da ücretsiz</div>'
              f'<div class="cta ess" data-min="44" style="max-width:470px">{esc(s.get("s2_line", "Link profilde: @lingoof.app"))}</div></div></div></div>')
    inner = (f'<div class="hook" id="hook" data-min="96" style="--hs:{s.get("hook_size", 120)}px">{s.get("hook", "Yanlış yaz.<br><em>Goof açıklasın.</em>")}</div>'
             f'<div class="slot" id="scenes">{scene1}{scene2}</div>')
    body = ('<div class="bg" id="bg"></div>' + f'<div class="stack" id="stack">{top(s.get("badge", "LINGOOF\'TA BÖYLE"))}{inner}</div>'
            + goof(names, 300, style='position:absolute;left:740px;top:600px'))
    tr = [
        bg_track(dur),
        ('#hook', {**collapse(T_FB, T_BACK), 'scale': [[0, 1.04], [r3(6 * F), 1, 'enter']]}),
        ('#fb', show(r3(T_FB + 10 * F), T_S2, 'up')),
        ('#ex', {'opacity': [[0, 1], [T_S2, 1], [r3(T_S2 + 6 * F), 0, 'exit'], [r3(T_BACK + 3 * F), 0], [r3(T_BACK + 10 * F), 1, 'enter']]}),
        ('#s2', show(r3(T_S2 + 0.15), T_BACK, 'up')),
        (f'#c{pick}', {'scale': [[0, 1], [T_TAP, 1], [r3(T_TAP + 3 * F), 0.92, 'inOutSine'], [r3(T_TAP + 9 * F), 1.04, 'pop'], [r3(T_TAP + 14 * F), 1, 'enter']],
                       'x': shake(T_BUZZ, 10)}),
        ('#goof', {**squash([T_BUZZ, T_FB] + xb + [r3(T_S2 + 14 * F), r3(T_BACK + 14 * F)]), 'y': hop(r3(T_S2 + 14 * F), 40),
                   'opacity': [[0, 1], [T_S2, 1], [r3(T_S2 + 4 * F), 0, 'exit'], [r3(T_S2 + 8 * F), 0], [r3(T_S2 + 14 * F), 1, 'enter'],
                               [T_BACK, 1], [r3(T_BACK + 4 * F), 0, 'exit'], [r3(T_BACK + 8 * F), 0], [r3(T_BACK + 14 * F), 1, 'enter']]}),
    ]
    tr += [(f'#goof_{n}', {'opacity': k}) for n, k in pk.items()]
    script = tracks_js(tr) + idle_js('#goof', dur) + f"""
E.hook(t => {{
  const c = document.getElementById('c{pick}'), on = t >= {T_TAP + 0.1} && t < {T_BACK};
  c.style.background = on ? '#FFE4E8' : ''; c.style.boxShadow = on ? '0 0 0 5px #BE123C' : ''; c.style.color = on ? '#BE123C' : '';
  const g = document.getElementById('goof');
  // Goof sahne 1'de alıştırma kartının sağ üstünde, sahne 2'de çağrı yazısının altında (yerleşimden hesaplanır)
  const s2 = t >= {r3(T_S2 + 6 * F)} && t < {r3(T_BACK + 6 * F)};
  if (s2) {{ const c = document.querySelector('#s2 .cta').getBoundingClientRect(); g.style.left = c.left + 'px'; g.style.top = (c.bottom + 10) + 'px'; }}
  else {{ const e = document.getElementById('ex').getBoundingClientRect(); g.style.left = '720px'; g.style.top = (e.top - 30) + 'px'; }}
}});"""
    cues = [(0.02, sfx.pop2(0.9, 0.42)), (T_TAP, sfx.tick2(0.4, 1)), (T_BUZZ, sfx.buzz2()), (r3(T_FB - 0.05), sfx.whoosh2(0.3, 0.18)),
            (r3(T_FB + 6 * F), sfx.pop2(1.05, 0.35)),
            (r3(T_S2 - 0.05), sfx.whoosh2(0.35, 0.2)), (r3(T_S2 + 0.4), sfx.chime(0.36)), (r3(T_S2 + 2.2), sfx.boing(0.14)),
            (r3(T_BACK - 0.05), sfx.whoosh2(0.35, 0.18, up=False))]
    cues += [(x, sfx.tick2(0.18, i)) for i, x in enumerate(xb)]
    teaser = (f'<div style="display:flex;column-gap:30px;align-items:flex-start"><div class="phone" style="width:300px;height:580px">'
              f'<div class="screen" style="background-image:url(/shots/{s.get("screen", "screen_hata.png")})"></div></div></div>')
    cover = cover_html(theme, s.get('badge', "LINGOOF'TA BÖYLE"), s.get('cover', plain(s.get('hook', 'Yanlış yaz, Goof açıklasın'))), teaser, 'goof_celebrate', goof_size=480)
    return Reel(body, script, dur, cues, theme, T_FB + 0.2, cover, dips=[T_FB, T_S2], f0=('#hook', '#goof', '#ex'))


TEMPLATES = {'hata': t_hata, 'quiz': t_quiz, 'pov': t_pov, 'nasil': t_nasil, 'vs': t_vs, 'urun': t_urun}


def cover_html(theme, badge, title, teaser, pose, goof_size=560):
    """Kapak: büyük başlık (≤5 kelime), içerikten bir parça, ifadeli büyük Goof; ana öğeler y 300–1500 içinde."""
    return (f'<div class="bg"></div><div class="stack" style="top:300px;row-gap:34px">{top(badge)}'
            f'<div class="hook" style="--hs:132px">{title}</div><div style="margin-right:420px">{teaser}</div></div>'
            f'<div class="goofbox" style="position:absolute;width:{goof_size}px;height:{goof_size}px;right:20px;top:{1580 - goof_size}px">'
            f'<div class="shadow"></div><img src="/goof/{pose}.png"></div>')


# ---------- Carousel (kılavuz §5.11) ----------

def carousel_slides(s):
    """Kapak (lacivert) → içerik (krem) → [test, cevap] → özet (kaydedilen slayt) → son (kaydet/gönder/yorum)."""
    items = s['items']
    quiz = s.get('quiz')
    n_total = 1 + len(items) + (2 if quiz else 0) + 1 + 1
    slides = []
    pg = lambda i, dark=False: f'<div class="pager" style="right:72px;top:100px;color:{"var(--t3)" if dark else "#8A8FA8"}">{i}/{n_total}</div>'
    brand = '<div class="brand" style="position:absolute;left:72px;bottom:72px"><img src="/goof/goof_avatar.png">LINGOOF</div>'
    # 1 kapak
    slides.append(('night', f'''<div class="bg"></div>
<div class="badge" style="position:absolute;left:72px;top:96px">{s.get('kicker', '')}</div>{pg(1, True)}
<div class="hook" style="position:absolute;left:72px;top:200px;width:936px;--hs:{s.get('hook_size', 118)}px">{s['hook']}</div>
<div style="position:absolute;left:72px;top:{s.get('promise_y', 700)}px;width:640px;font:500 46px/1.3 'DM Sans';color:var(--t2)">{s.get('promise', '')}</div>
<div class="goofbox" style="position:absolute;width:520px;height:520px;right:-150px;bottom:150px"><div class="shadow"></div><img src="/goof/{s.get('hook_goof', 'goof_pose_point_left')}.png"></div>
<div style="position:absolute;left:72px;bottom:170px;font:700 40px/1 'DM Sans';color:var(--lilac)">Kaydır →</div>{brand}'''))
    poses_ = ['goof_pose_point_left', 'goof_calm', 'goof_pose_look_up', 'goof_proud', 'goof_hype', 'goof_focus', 'goof_pose_neutral']
    for i, it in enumerate(items):
        extra = ''
        if it.get('reply'):
            extra += (f'<div class="label ok" style="margin-top:34px">KARŞILIK</div>'
                      f'<div style="margin-top:12px;align-self:flex-start;max-width:760px;background:var(--ok-bg);border:4px solid #34D08A;border-radius:30px;'
                      f'padding:22px 30px;font:700 48px/1.2 \'DM Sans\';color:var(--ok-l)">{esc(it["reply"])}</div>')
        if it.get('tip'):
            extra += (f'<div style="margin-top:30px;max-width:700px;background:#fff;border-radius:30px;padding:24px 30px;font:500 42px/1.3 \'DM Sans\';'
                      f'color:var(--navy);box-shadow:0 0 0 3px var(--line)"><b style="color:var(--err-l)">İpucu: </b>{it["tip"]}</div>')
        slides.append(('day', f'''<div class="bg"></div>
<div class="badge" style="position:absolute;left:72px;top:96px">{esc(it.get('when', ''))}</div>{pg(i + 2)}
<div style="position:absolute;left:72px;top:196px;width:936px;display:flex;flex-direction:column">
 <div style="background:#fff;border-radius:44px;border-bottom-left-radius:12px;padding:40px 46px;box-shadow:0 12px 0 var(--line),0 0 0 3px var(--line)">
  <div style="font:700 {it.get('size', 64)}px/1.12 'DM Sans';letter-spacing:-1px;color:var(--navy)">{esc(it['en'])}</div>
  <div style="margin-top:18px;font:500 46px/1.28 'DM Sans';color:var(--ink-2)">{esc(it['tr'])}</div>
 </div>{extra}
</div>
<div class="goofbox" style="position:absolute;width:300px;height:300px;right:56px;bottom:60px"><div class="shadow"></div><img src="/goof/{poses_[i % len(poses_)]}.png"></div>'''))
    if quiz:
        keys = 'ABC'
        opts = ''.join(f'<div class="opt" style="margin-top:20px;font-size:52px"><span class="key">{keys[j]}</span><span>{esc(o)}</span></div>' for j, o in enumerate(quiz['options']))
        k = len(items) + 2
        slides.append(('day', f'''<div class="bg"></div>
<div class="badge" style="position:absolute;left:72px;top:96px;background:var(--err-l)">MİNİ TEST</div>{pg(k)}
<div class="h1" style="position:absolute;left:72px;top:196px;width:936px;font-size:72px">{quiz['q']}</div>
<div style="position:absolute;left:72px;top:{quiz.get('opts_y', 470)}px;width:800px">{opts}</div>
<div style="position:absolute;left:72px;bottom:96px;width:620px;font:700 42px/1.25 'DM Sans';color:var(--violet)">Cevabını yorumlara yaz, sonra kaydır →</div>
<div class="goofbox" style="position:absolute;width:280px;height:280px;right:56px;bottom:50px"><div class="shadow"></div><img src="/goof/goof_focus.png"></div>'''))
        slides.append(('night', f'''<div class="bg"></div>
<div class="badge" style="position:absolute;left:72px;top:96px">CEVAP: {keys[quiz['answer']]}</div>{pg(k + 1, True)}
<div class="hook" style="position:absolute;left:72px;top:200px;width:936px;--hs:96px">{esc(quiz['options'][quiz['answer']])}</div>
<div style="position:absolute;left:72px;top:{quiz.get('why_y', 560)}px;width:700px;font:500 48px/1.3 'DM Sans';color:var(--t2)">{quiz['why']}</div>
<div class="goofbox" style="position:absolute;width:400px;height:400px;right:40px;bottom:90px"><div class="shadow"></div><img src="/goof/goof_celebrate.png"></div>{brand}'''))
    # özet
    rows = ''.join(f'<div style="display:flex;gap:22px;align-items:baseline;padding:16px 0;border-bottom:3px solid var(--line)">'
                   f'<div style="font:700 44px/1.2 \'DM Sans\';color:var(--navy)">{esc(it["en"])}</div></div>' for it in items)
    slides.append(('day', f'''<div class="bg"></div>
<div class="badge" style="position:absolute;left:72px;top:96px">ÖZET · KAYDET</div>{pg(n_total - 1)}
<div class="h1" style="position:absolute;left:72px;top:190px;width:936px;font-size:76px">{s.get('recap_title', 'Hepsi bir arada')}</div>
<div style="position:absolute;left:72px;top:330px;width:936px;background:#fff;border-radius:40px;padding:20px 44px;box-shadow:0 12px 0 var(--line),0 0 0 3px var(--line)">{rows}</div>'''))
    # son
    slides.append(('night', f'''<div class="bg"></div>
<div class="badge" style="position:absolute;left:72px;top:96px">{s.get('last_badge', 'SONRAKİ ADIM')}</div>{pg(n_total, True)}
<div class="hook" style="position:absolute;left:72px;top:200px;width:936px;--hs:92px">{s.get('save', 'Kaydet,<br><em>lazım olacak.</em>')}</div>
<div style="position:absolute;left:72px;top:{s.get('last_y', 520)}px;width:640px;display:flex;flex-direction:column;row-gap:30px;font:500 46px/1.3 'DM Sans';color:var(--t2)">
 <div><b style="color:var(--t1)">Gönder:</b> {s.get('send', 'Bunu bilmesi gereken arkadaşına gönder.')}</div>
 <div><b style="color:var(--t1)">Yorum:</b> {s.get('ask', 'Sen hangisini kullanıyorsun?')}</div>
 <div style="color:var(--t3);font-size:40px">Her gün bir kalıp: @lingoof.app</div>
 <div style="color:var(--t3);font-size:36px">{s.get('app_line', "Goof'la günde 5 dakika tekrar et: LINGOOF, iPhone'da ücretsiz.")}</div>
</div>
<div class="goofbox" style="position:absolute;width:420px;height:420px;right:30px;bottom:110px"><div class="shadow"></div><img src="/goof/goof_celebrate.png"></div>{brand}'''))
    return slides


# ---------- ses ----------

def write_wav(path, x, channels=1):
    x = np.clip(x, -1, 1)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sfx.SR)
        w.writeframes((x * 32767).astype('<i2').tobytes())


def loudness(path, extra=''):
    """ffmpeg loudnorm ölçümü: entegre yükseklik (LUFS), gerçek tepe (dBTP), LRA."""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', f'loudnorm=print_format=json{extra}', '-f', 'null', '-'],
                       capture_output=True, text=True)
    m = re.search(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr, re.S)
    return json.loads(m.group(0))


def master(src, dst, I=-14.0):
    """Kazanç + tepe sınırlayıcı: entegre −14 LUFS'e getir, örnek tepesi −3,5 dBFS'te kesilsin
    (AAC kodlayıcı tepeyi biraz taşırır; sonuç ≤ −1 dBTP kalır). Sapma varsa kazancı düzeltip tekrarla."""
    g = I - float(loudness(src)['input_i'])
    for _ in range(4):
        af = f'volume={g:.2f}dB,alimiter=limit=0.668:attack=2:release=80:level=disabled,aresample=48000'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-af', af, '-ar', '48000', str(dst)], check=True)
        li = float(loudness(dst)['input_i'])
        if abs(li - I) <= 0.25:
            break
        g += I - li


def build_audio(rid, n_frames, cues, dips):
    dur = n_frames / FPS
    fx = sfx.mix(cues, dur + 1)[: n_frames * (sfx.SR // FPS)]                  # ses tam kare sayısı kadar (1 kare = 1600 örnek)
    peak = np.abs(fx).max() or 1
    fx_only = fx / peak * 0.5                                                  # −6 dBFS tepe (lisanslı müziğin altına)
    seed = int(hashlib.md5(rid.encode()).hexdigest(), 16) % 2
    music = sfx.backing_120(dur + 1, seed=seed)[: len(fx)]
    tt = np.arange(len(music)) / sfx.SR
    g = np.ones(len(music))
    for t in dips:                                                             # açıklamadan önce müziği 6 dB kıs
        d = np.clip(np.minimum((tt - (t - 0.3)) / 0.06, ((t + 0.35) - tt) / 0.25), 0, 1)
        g = np.minimum(g, 1 - d * (1 - 10 ** (-6 / 20)))
    music *= g
    write_wav(TMP / 'm.wav', music)
    lm = float(loudness(TMP / 'm.wav')['input_i'])
    music *= 10 ** ((-23 - lm) / 20)                                           # yatak −23 LUFS; mastering sonrası ≈ −16/−17
    mix = music + fx / peak * 0.89                                             # efekt tepesi −1 dBFS (sınırlayıcı keser)
    write_wav(TMP / 'fx.wav', np.stack([fx_only, fx_only], 1).reshape(-1), channels=2)
    write_wav(TMP / 'mix_raw.wav', np.stack([mix, mix], 1).reshape(-1), channels=2)
    master(TMP / 'mix_raw.wav', TMP / 'mix.wav')
    return TMP / 'fx.wav', TMP / 'mix.wav'


# ---------- kodlama ve dosya denetimi ----------

VF = ('zscale=matrix=709:range=limited:dither=error_diffusion,format=yuv420p,'
      'setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv')
X264 = ['-c:v', 'libx264', '-preset', 'slow', '-tune', 'animation', '-crf', '16', '-maxrate', '14M', '-bufsize', '28M',
        '-profile:v', 'high', '-level:v', '4.1', '-g', '60', '-keyint_min', '30', '-bf', '0', '-x264-params', 'open-gop=0',
        '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']


def mux(video, audio, dst):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(video), '-i', str(audio), '-map', '0:v', '-map', '1:a', '-c:v', 'copy',
                    '-c:a', 'aac', '-b:a', '128k', '-ar', '48000', '-ac', '2', '-movflags', '+faststart', '-use_editlist', '0', str(dst)],
                   check=True)


def mp4_boxes(path):
    data = Path(path).read_bytes()
    top, i = [], 0
    while i + 8 <= len(data):
        size, typ = struct.unpack('>I4s', data[i:i + 8])
        if size == 1:
            size = struct.unpack('>Q', data[i + 8:i + 16])[0]
        top.append((typ.decode('latin1'), i, size))
        if size < 8:
            break
        i += size
    moov = next((b for b in top if b[0] == 'moov'), None)
    has_elst = moov is not None and b'elst' in data[moov[1]:moov[1] + moov[2]]
    return [b[0] for b in top], has_elst


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True)
    return json.loads(r.stdout)


def file_qc(path, dur, music):
    errs = []
    p = probe(path)
    v = next(s for s in p['streams'] if s['codec_type'] == 'video')
    a = next((s for s in p['streams'] if s['codec_type'] == 'audio'), None)
    want = {'width': 1080, 'height': 1920, 'codec_name': 'h264', 'profile': 'High', 'pix_fmt': 'yuv420p', 'r_frame_rate': '30/1',
            'color_space': 'bt709', 'color_primaries': 'bt709', 'color_transfer': 'bt709', 'color_range': 'tv'}
    for k, val in want.items():
        if v.get(k) != val:
            errs.append(f'{path.name}: {k}={v.get(k)} (beklenen {val})')
    if not a or a['codec_name'] != 'aac' or a['sample_rate'] != '48000' or a['channels'] != 2:
        errs.append(f'{path.name}: ses AAC 48 kHz stereo değil')
    if a and abs(float(v['duration']) - float(a['duration'])) > 0.06:
        errs.append(f'{path.name}: görüntü/ses süresi farkı {abs(float(v["duration"]) - float(a["duration"])):.3f} sn')
    if int(p['format'].get('bit_rate', 0)) > 25_000_000:
        errs.append(f'{path.name}: bit hızı yüksek')
    boxes, elst = mp4_boxes(path)
    if 'moov' not in boxes or 'mdat' not in boxes or boxes.index('moov') > boxes.index('mdat'):
        errs.append(f'{path.name}: moov başta değil')
    if elst:
        errs.append(f'{path.name}: düzenleme listesi (elst) var')
    info = {}
    if music:
        m = loudness(path)
        info = {'lufs': float(m['input_i']), 'tp': float(m['input_tp']), 'lra': float(m['input_lra'])}
        if abs(info['lufs'] + 14) > 1:
            errs.append(f'{path.name}: yükseklik {info["lufs"]} LUFS (hedef −14±1)')
        if info['tp'] > -1.0:
            errs.append(f'{path.name}: gerçek tepe {info["tp"]} dBTP (≤ −1)')
        r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', str(path), '-af', 'silencedetect=noise=-50dB:d=0.25', '-f', 'null', '-'],
                           capture_output=True, text=True)
        if 'silence_start' in r.stderr:
            errs.append(f'{path.name}: 250 ms\'den uzun sessizlik')
    return errs, info


def save_jpeg(png_bytes, path, q):
    im = Image.open(io.BytesIO(png_bytes)).convert('RGB')
    im.save(path, 'JPEG', quality=q, subsampling=0, optimize=True, icc_profile=SRGB)


# ---------- üretim ----------

def open_page(browser, name, html_text, w, h):
    TMP.mkdir(exist_ok=True)
    (TMP / f'{name}.html').write_text(html_text, encoding='utf-8')
    pg = browser.new_page(viewport={'width': w, 'height': h}, device_scale_factor=1)
    pg.goto(f'http://127.0.0.1:{PORT}/tmp/{name}.html')
    pg.wait_for_function('window.READY === true', timeout=30000)
    return pg


def render_reel(item, browser, frames=True):
    sc = TEMPLATES[item['template']](item)
    rid = item['id']
    out = OUT / rid
    out.mkdir(parents=True, exist_ok=True)
    qc = {'block': [], 'warn': [], 'notes': sc.notes}
    pg = open_page(browser, rid, doc(sc.body, sc.script, theme=sc.theme), W, H)
    times = [round(i * 0.2, 2) for i in range(int(sc.dur / 0.2) + 1)]
    fit = pg.evaluate(f'QC.fit({js(times)})')
    qc['k'] = fit['k']
    qc['block'] += fit['v']
    bad0 = pg.evaluate(f'QC.frame0({js(sc.f0)})')
    if bad0:
        qc['block'].append(f'ilk karede görünmüyor: {bad0}')
    if sc.payoff > 4.0:
        qc['block'].append(f'ilk cevap {sc.payoff:.1f} sn (≤4)')
    if not 8 <= sc.dur <= 14:
        qc['warn'].append(f'süre {sc.dur} sn (mikro: 8–12)')
    ts = sorted(t for t, _ in sc.cues)
    gaps = [b - a for a, b in zip(ts, ts[1:])]
    if gaps and max(gaps) > 3.0:
        qc['warn'].append(f'{max(gaps):.1f} sn olaysız aralık')
    close = [(a, b) for a, b in zip(ts, ts[1:]) if b - a < 0.1]
    if close:
        qc['warn'].append(f'100 ms içinde iki efekt: {close}')
    if frames:
        video = TMP / f'{rid}_v.mp4'
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'png', '-i', '-',
                               '-vf', VF] + X264 + ['-an', str(video)], stdin=subprocess.PIPE)
        n_frames = int(round(sc.dur * FPS))
        for i in range(n_frames):
            pg.evaluate(f'E.seek({i / FPS:.5f})')
            ff.stdin.write(pg.screenshot(type='png'))
        ff.stdin.close()
        ff.wait()
    pg.close()
    cp = open_page(browser, rid + '_kapak', doc(sc.cover, '', theme=sc.theme), W, H)
    save_jpeg(cp.screenshot(type='png'), out / 'kapak.jpg', 92)
    cp.close()
    if frames:
        fx, mix = build_audio(rid, n_frames, sc.cues, sc.dips)
        mux(video, fx, out / 'reels.mp4')
        mux(video, mix, out / 'reels_muzikli.mp4')
        for f, music in (('reels.mp4', False), ('reels_muzikli.mp4', True)):
            errs, info = file_qc(out / f, sc.dur, music)
            qc['block'] += errs
            if info:
                qc['audio'] = info
    qc['duration_s'] = round(sc.dur, 2)
    (out / 'qc.json').write_text(json.dumps(qc, ensure_ascii=False, indent=1), encoding='utf-8')
    return {'duration_s': round(sc.dur, 1), 'k': qc['k'], 'block': qc['block'], 'warn': qc['warn'], 'audio': qc.get('audio')}


def render_carousel(item, browser):
    out = OUT / item['id']
    out.mkdir(parents=True, exist_ok=True)
    files, block = [], []
    for i, (theme, body) in enumerate(carousel_slides(item)):
        name = f'{item["id"]}_{i + 1}'
        pg = open_page(browser, name, doc(body, '', CW, CH, theme), CW, CH)
        v = pg.evaluate('QC.scan([0], false)')
        block += [f'slayt {i + 1}: {x["msg"]}' for x in v]
        f = f'{i + 1:02d}.jpg'
        save_jpeg(pg.screenshot(type='png'), out / f, 93)
        pg.close()
        files.append(f)
    (out / 'qc.json').write_text(json.dumps({'block': block}, ensure_ascii=False, indent=1), encoding='utf-8')
    return {'files': files, 'block': block}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    plan = json.loads(Path(args[0]).read_text(encoding='utf-8'))
    only = set(args[1:])
    frames = '--no-video' not in sys.argv
    serve()
    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/usr/bin/google-chrome',
                                    args=['--force-color-profile=srgb', '--disable-lcd-text', '--hide-scrollbars'])
        for item in plan:
            if only and item['id'] not in only:
                continue
            r = render_reel(item, browser, frames) if item['kind'] == 'reels' else render_carousel(item, browser)
            results[item['id']] = r
            flag = 'ENGEL' if r.get('block') else 'tamam'
            print(f'{flag}: {item["id"]} → {json.dumps({k: v for k, v in r.items() if k != "files"}, ensure_ascii=False)}', flush=True)
        browser.close()
    prev = OUT / 'sonuc.json'
    allr = json.loads(prev.read_text(encoding='utf-8')) if prev.exists() else {}
    allr.update(results)
    prev.write_text(json.dumps(allr, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
