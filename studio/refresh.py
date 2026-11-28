#!/usr/bin/env python3
"""Kuyruktaki gönderileri yeniden üretilmiş dosyalarla günceller (aynı src_id, aynı slot).

- out/<id>/ dosyalarını media/v2/<id>/ üzerine kopyalar (kalite kapısından geçmeyen atlanır).
- posts.json'da açıklamayı, başlığı ve süreyi plandan yeniler; "hold" ve "hold_reason" alanlarını kaldırır.
- Paylaşılmış gönderilere dokunmaz.

Kullanım: python3 refresh.py plans/aralik_posts.json /yol/lingoof-instagram-bot
"""
import json
import shutil
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
OUT = STUDIO / 'out'


def main():
    plan = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    repo = Path(sys.argv[2])
    posts = json.loads((repo / 'posts.json').read_text(encoding='utf-8'))
    posted = set(json.loads((repo / 'state.json').read_text(encoding='utf-8')).get('posted', {}))
    by_src = {p.get('src_id'): p for p in posts if p.get('src_id')}
    done, skipped = [], []
    for item in plan:
        rid = item['id']
        post = by_src.get(rid)
        if post is None or str(post['n']) in posted:
            skipped.append((rid, 'paylaşılmış' if post else 'kuyrukta yok'))
            continue
        qc = json.loads((OUT / rid / 'qc.json').read_text(encoding='utf-8'))
        if qc.get('block'):
            skipped.append((rid, 'kalite kapısı: ' + '; '.join(qc['block'][:2])))
            continue
        dst = repo / 'media' / 'v2' / rid
        dst.mkdir(parents=True, exist_ok=True)
        if item['kind'] == 'reels':
            for f in ('reels.mp4', 'reels_muzikli.mp4', 'kapak.jpg'):
                shutil.copy2(OUT / rid / f, dst / f)
            post['duration_s'] = qc['duration_s']
        else:
            files = sorted(p.name for p in (OUT / rid).glob('[0-9][0-9].jpg'))
            assert [Path(m).name for m in post['media']] == files, f'{rid}: slayt sayısı değişti'
            for f in files:
                shutil.copy2(OUT / rid / f, dst / f)
        post['caption'] = item['caption']
        post['title'] = item['title']
        post.pop('hold', None)
        post.pop('hold_reason', None)
        done.append(post['n'])
    (repo / 'posts.json').write_text(json.dumps(posts, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'güncellendi: {len(done)} gönderi')
    for rid, why in skipped:
        print(f'atlandı: {rid} ({why})')


if __name__ == '__main__':
    main()
