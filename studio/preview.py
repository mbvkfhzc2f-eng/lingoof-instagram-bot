#!/usr/bin/env python3
"""Önizleme: her Reels için seçilen anlarda kare alır, kapakla birlikte tek bir temas sayfasına dizer.
Kullanım: python3 preview.py content.json çıktı.jpg [id ...]"""
import io
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

import render

plan = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
dst = sys.argv[2]
only = set(sys.argv[3:])
render.serve()
rows = []
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--force-color-profile=srgb', '--hide-scrollbars'])
    for item in plan:
        if item['kind'] != 'reels' or (only and item['id'] not in only):
            continue
        sc = render.TEMPLATES[item['template']](item)
        pg = render.open_page(b, item['id'] + '_pv', render.doc(sc.body, sc.script, theme=sc.theme), render.W, render.H)
        times = [round(i * 0.2, 2) for i in range(int(sc.dur / 0.2) + 1)]
        pg.evaluate(f'QC.fit({json.dumps(times)})')
        want = item.get('preview') or [0, 1.6, round(sc.payoff + 0.4, 2), round(sc.dur * 0.62, 2), round(sc.dur - 0.25, 2)]
        shots = []
        for t in want:
            pg.evaluate(f'E.seek({t})')
            im = Image.open(io.BytesIO(pg.screenshot(type='png'))).convert('RGB')
            shots.append((t, im))
        pg.close()
        cov = render.OUT / item['id'] / 'kapak.jpg'
        if cov.exists():
            shots.append(('kapak', Image.open(cov).convert('RGB')))
        rows.append((item['id'], shots))
    b.close()
tw, th = 270, 480
cols = max(len(s) for _, s in rows)
sheet = Image.new('RGB', (cols * (tw + 8), len(rows) * (th + 30)), (40, 40, 48))
d = ImageDraw.Draw(sheet)
for r, (rid, shots) in enumerate(rows):
    for c, (t, im) in enumerate(shots):
        x, y = c * (tw + 8), r * (th + 30)
        im = im.resize((tw, th))
        # Instagram arayüz alanları: üst 270, alt 1250 çizgisi, sağ alt düğmeler
        dd = ImageDraw.Draw(im)
        sx = tw / 1080
        dd.line([(0, 270 * sx), (tw, 270 * sx)], fill=(255, 0, 0))
        dd.line([(0, 1250 * sx), (tw, 1250 * sx)], fill=(255, 0, 0))
        dd.rectangle([930 * sx, 1150 * sx, tw, th], outline=(255, 0, 0))
        sheet.paste(im, (x, y + 24))
        d.text((x + 4, y + 6), f'{rid} · {t}', fill=(255, 255, 255))
sheet.save(dst, quality=88)
print(dst, sheet.size)
