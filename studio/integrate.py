#!/usr/bin/env python3
"""Üretilen içerikleri bot deposuna yerleştirir.

- out/<id>/ dosyalarını depoda media/v2/<id>/ altına kopyalar (kalite kapısından geçmeyen içerik kopyalanmaz).
- posts.json'a yeni gönderileri ekler (n = 101'den başlar); yerini aldıkları eski gönderileri "hold" yapar.
- Müzik: eski gönderinin seçilmiş parçası (music_id) korunur; yoksa beklemedeki bir gönderinin parçası kullanılır.
  Yeni Reels konuşmasız (yalnızca efekt), bu yüzden lisanslı müzik sesi 70 (kılavuz §5.9: 70–80).

Kullanım: python3 integrate.py plans/aralik_posts.json /home/claude/lingoof-instagram-bot
"""
import json
import shutil
import sys
from pathlib import Path

STUDIO = Path(__file__).resolve().parent
OUT = STUDIO / 'out'
MUSIC_VOLUME = 70


def main():
    plan = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    repo = Path(sys.argv[2])
    posts = json.loads((repo / 'posts.json').read_text(encoding='utf-8'))
    state = json.loads((repo / 'state.json').read_text(encoding='utf-8'))
    posted = set(state.get('posted', {}))
    by_n = {p['n']: p for p in posts}
    existing_ids = {p.get('src_id') for p in posts if p.get('src_id')}
    next_n = max([100] + [p['n'] for p in posts if isinstance(p['n'], int)]) + 1
    # yedek müzik havuzu: beklemedeki eski gönderilerin seçilmiş parçaları
    used_ids = {str(p.get('music_id')) for p in posts if p.get('music_id') and not p.get('hold')}
    pool = [(str(p['music_id']), p.get('music_title', '')) for p in posts if p.get('hold') and p.get('music_id')]
    pool = [m for m in pool if m[0] not in used_ids]
    problems, added = [], []
    for item in sorted(plan, key=lambda x: (x['date'], x['time'])):
        rid = item['id']
        if rid in existing_ids:
            print(f'zaten ekli: {rid}')
            continue
        qc = json.loads((OUT / rid / 'qc.json').read_text(encoding='utf-8'))
        if qc.get('block'):
            problems.append((rid, qc['block'][:3]))
            continue
        old = by_n.get(item['replaces'])
        if old is not None:
            assert str(old['n']) not in posted, f'{old["n"]} zaten paylaşılmış'
            old['hold'] = True
        dst = repo / 'media' / 'v2' / rid
        dst.mkdir(parents=True, exist_ok=True)
        post = {'n': next_n, 'date': item['date'], 'time': item['time'], 'kind': item['kind'], 'title': item['title'], 'src_id': rid}
        if item['kind'] == 'reels':
            for f in ('reels.mp4', 'reels_muzikli.mp4', 'kapak.jpg'):
                shutil.copy2(OUT / rid / f, dst / f)
            post.update(media=f'v2/{rid}/reels.mp4', media_fallback=f'v2/{rid}/reels_muzikli.mp4', cover=f'v2/{rid}/kapak.jpg',
                        duration_s=qc['duration_s'])
            if old is not None and old.get('music_id'):
                post.update(music_id=str(old['music_id']), music_title=old.get('music_title', ''))
            elif pool:
                mid, mt = pool.pop(0)
                post.update(music_id=mid, music_title=mt)
            post['music_volume'] = MUSIC_VOLUME
            if item.get('trial'):
                post['trial'] = item['trial']
        else:
            files = sorted(p.name for p in (OUT / rid).glob('[0-9][0-9].jpg'))
            for f in files:
                shutil.copy2(OUT / rid / f, dst / f)
            post['media'] = [f'v2/{rid}/{f}' for f in files]
            if item.get('alt_texts'):
                post['alt_texts'] = [a[:900] for a in item['alt_texts'][:len(files)]]
        post['caption'] = item['caption']
        if old is not None:
            post['replaces'] = old['n']
        posts.append(post)
        added.append(post)
        next_n += 1
    # aynı slotta iki etkin gönderi olmasın
    slots = {}
    for p in posts:
        if p.get('hold') or str(p['n']) in posted:
            continue
        key = (p['date'], p['time'])
        assert key not in slots, f'çakışan slot {key}: {slots[key]} ve {p["n"]}'
        slots[key] = p['n']
    (repo / 'posts.json').write_text(json.dumps(posts, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'eklendi: {len(added)} gönderi (n {added[0]["n"] if added else "-"}–{added[-1]["n"] if added else "-"})')
    for rid, b in problems:
        print(f'KALİTE KAPISI: {rid} eklenmedi → {b}')


if __name__ == '__main__':
    main()
