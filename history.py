#!/usr/bin/env python3
"""Instagram hesabındaki tüm geçmiş gönderileri listeler: history.json ve okunabilir history.md.

Hangi hazır videonun daha önce paylaşıldığını bulmak için kullanılır. Hiçbir şey paylaşmaz, değiştirmez.
Ortam değişkeni: IG_TOKEN
"""
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bot import Api, load

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo('Europe/Istanbul')
FIELDS = 'id,caption,media_type,media_product_type,timestamp,permalink,thumbnail_url,media_url'


def main():
    token = os.environ.get('IG_TOKEN', '').strip()
    if not token:
        sys.exit('IG_TOKEN tanımlı değil.')
    cfg = load('config.json', {})
    api = Api(token, cfg.get('api_version', 'v24.0'))
    me = api.call('GET', 'me', {'fields': 'user_id,username'})
    ig_id = me.get('user_id') or me.get('id')
    items, after = [], None
    while True:
        params = {'fields': FIELDS, 'limit': 100}
        if after:
            params['after'] = after
        page = api.call('GET', f'{ig_id}/media', params)
        items += page.get('data', [])
        after = page.get('paging', {}).get('cursors', {}).get('after')
        if not page.get('paging', {}).get('next') or not after:
            break
    items.sort(key=lambda m: m.get('timestamp', ''))
    (ROOT / 'history.json').write_text(json.dumps(items, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')

    lines = [f'# @{me.get("username")} geçmiş gönderileri', '',
             f'{len(items)} gönderi · {datetime.now(TZ):%d.%m.%Y %H:%M} itibarıyla', '',
             '| Tarih | Tür | Açıklamanın başı | Link |', '| --- | --- | --- | --- |']
    for m in items:
        ts = datetime.fromisoformat(m['timestamp'].replace('+0000', '+00:00')).astimezone(TZ)
        kind = m.get('media_product_type', '') if m.get('media_product_type') == 'REELS' else m.get('media_type', '')
        cap = (m.get('caption') or '').replace('\n', ' ').replace('|', '/')[:90]
        lines.append(f'| {ts:%d.%m.%Y %H:%M} | {kind} | {cap} | [aç]({m.get("permalink", "")}) |')
    (ROOT / 'history.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'@{me.get("username")}: {len(items)} gönderi history.md dosyasına yazıldı.')


if __name__ == '__main__':
    main()
