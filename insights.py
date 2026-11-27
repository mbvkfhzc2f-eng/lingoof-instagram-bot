#!/usr/bin/env python3
"""LINGOOF Instagram istatistik toplayıcı. Hiçbir şey paylaşmaz, yalnızca okur.

Her çalışmada hesaptaki gönderilerin güncel istatistiklerini okur ve şunları yazar:
  insights_latest.json  her gönderinin son değerleri ve hesap özeti
  insights.jsonl        her gönderi için 24 saat, 72 saat ve 7 gün dolduğunda alınan kalıcı ölçüm (karar verileri)
  insights.md           okunabilir tablo: son gönderiler, oranlar, LRS puanı, hesap özeti

Oranlar (erişime göre): paylaşım/erişim, kayıt/erişim, beğeni/erişim; reels'te izlenme oranı (ortalama izlenme
süresi / video süresi) ve ilk 3 saniyede kalma (1 - atlama oranı). LRS: son 30 reels'e göre z puanlarıyla
0,30 izlenme oranı + 0,20 kalma + 0,25 paylaşım + 0,15 kayıt + 0,10 beğeni.

Ortam değişkenleri: IG_TOKEN ve/veya FB_TOKEN (bot.py ile aynı).
"""
import json
import math
import os
import statistics as st
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot import Api, load, save, TZ

ROOT = Path(__file__).resolve().parent
REEL_METRICS = ['views', 'reach', 'likes', 'comments', 'shares', 'saved', 'total_interactions',
                'ig_reels_avg_watch_time', 'ig_reels_video_view_total_time', 'reels_skip_rate', 'reposts']
FEED_METRICS = ['views', 'reach', 'likes', 'comments', 'shares', 'saved', 'total_interactions',
                'follows', 'profile_visits', 'profile_activity', 'reposts']
ACCOUNT_METRICS = ['reach', 'views', 'accounts_engaged', 'total_interactions', 'likes', 'comments', 'shares',
                   'saves', 'follows_and_unfollows', 'profile_links_taps']
MILESTONES = [('24s', 24), ('72s', 72), ('7g', 168)]
unsupported = set()


def connect(cfg):
    version = cfg.get('api_version', 'v24.0')
    fb_token = os.environ.get('FB_TOKEN', '').strip()
    token = os.environ.get('IG_TOKEN', '').strip()
    if fb_token and cfg.get('facebook_login'):
        fapi = Api(fb_token, version, 'graph.facebook.com')
        want = cfg.get('ig_username', 'lingoof.app').lstrip('@').lower()
        try:
            pages = fapi.call('GET', 'me/accounts', {'fields': 'name,instagram_business_account{id,username}', 'limit': '100'}).get('data', [])
            acc = next((p['instagram_business_account'] for p in pages
                        if p.get('instagram_business_account', {}).get('username', '').lower() == want), None)
            if acc:
                return fapi, acc['id']
        except RuntimeError as e:
            print(f'(Not) Facebook bağlantısı kurulamadı, IG_TOKEN deneniyor: {e}')
    if not token:
        sys.exit('IG_TOKEN ya da FB_TOKEN tanımlı değil.')
    api = Api(token, version)
    me = api.call('GET', 'me', {'fields': 'user_id,username'})
    return api, me.get('user_id') or me.get('id')


def metric_values(data):
    out = {}
    for m in data.get('data', []):
        name = m.get('name')
        if 'total_value' in m:
            tv = m['total_value']
            out[name] = tv.get('value')
            for b in tv.get('breakdowns', []) or []:
                for r in b.get('results', []):
                    key = name + ':' + '/'.join(str(x) for x in r.get('dimension_values', []))
                    out[key] = r.get('value')
        elif m.get('values'):
            out[name] = m['values'][-1].get('value')
    return out


def media_insights(api, mid, metrics):
    """Önce hepsini birden ister; desteklenmeyen bir metrik tüm isteği bozarsa tek tek dener ve desteklenmeyeni not eder."""
    wanted = [m for m in metrics if m not in unsupported]
    try:
        return metric_values(api.call('GET', f'{mid}/insights', {'metric': ','.join(wanted)}))
    except RuntimeError:
        pass
    out = {}
    for m in wanted:
        try:
            out.update(metric_values(api.call('GET', f'{mid}/insights', {'metric': m})))
        except RuntimeError as e:
            if 'not supported' in str(e).lower() or 'invalid' in str(e).lower() or '(#100)' in str(e):
                unsupported.add(m)
    return out


def account_summary(api, ig_id):
    info = {}
    try:
        info.update(api.call('GET', ig_id, {'fields': 'username,followers_count,follows_count,media_count'}))
    except RuntimeError as e:
        print(f'(Not) Hesap bilgisi okunamadı: {e}')
    until = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for days in (1, 7, 28):
        since = until - timedelta(days=days)
        vals = {}
        for m in ACCOUNT_METRICS:
            params = {'metric': m, 'period': 'day', 'metric_type': 'total_value',
                      'since': int(since.timestamp()), 'until': int(until.timestamp())}
            if m == 'follows_and_unfollows':
                params['breakdown'] = 'follow_type'
            try:
                vals.update(metric_values(api.call('GET', f'{ig_id}/insights', params)))
            except RuntimeError:
                continue
        info[f'son_{days}_gun'] = vals
    return info


def rate(a, b):
    return round(a / b, 4) if a is not None and b else None


def zscores(values):
    xs = [v for v in values if v is not None]
    if len(xs) < 3:
        return [0.0 if v is not None else None for v in values]
    mu, sd = st.mean(xs), st.pstdev(xs) or 1.0
    return [None if v is None else (v - mu) / sd for v in values]


def main():
    cfg = load('config.json', {})
    state = load('state.json', {'posted': {}})
    posts = {str(p['n']): p for p in load('posts.json', [])}
    id_to_n = {e['id']: n for n, e in state.get('posted', {}).items() if e.get('id')}
    api, ig_id = connect(cfg)
    now = datetime.now(timezone.utc)

    items, after = [], None
    while True:
        params = {'fields': 'id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count', 'limit': 100}
        if after:
            params['after'] = after
        page = api.call('GET', f'{ig_id}/media', params)
        items += page.get('data', [])
        after = page.get('paging', {}).get('cursors', {}).get('after')
        if not page.get('paging', {}).get('next') or not after:
            break

    latest = load('insights_latest.json', {}) or {}
    old_media = latest.get('media', {})
    snaps_path = ROOT / 'insights.jsonl'
    taken = set()
    if snaps_path.exists():
        for line in snaps_path.read_text(encoding='utf-8').splitlines():
            try:
                s = json.loads(line)
                taken.add((s['id'], s['milestone']))
            except Exception:
                continue

    media_out, new_snaps = {}, []
    for m in items:
        ts = datetime.fromisoformat(m['timestamp'].replace('+0000', '+00:00'))
        age_h = (now - ts).total_seconds() / 3600
        reel = m.get('media_product_type') == 'REELS'
        # 21 günden eski gönderiler her çalışmada yeniden okunmaz; son değerleri korunur (API kotası için)
        if age_h > 24 * 21 and m['id'] in old_media:
            media_out[m['id']] = old_media[m['id']]
            continue
        vals = media_insights(api, m['id'], REEL_METRICS if reel else FEED_METRICS)
        n = id_to_n.get(m['id'])
        post = posts.get(str(n)) if n else None
        rec = {
            'id': m['id'], 'n': n, 'tur': 'reels' if reel else m.get('media_type', '').lower(),
            'tarih': ts.astimezone(TZ).isoformat(timespec='minutes'), 'yas_saat': round(age_h, 1),
            'link': m.get('permalink'), 'ilk_satir': (m.get('caption') or '').split('\n')[0][:90],
            'seri': (post or {}).get('title'), 'sure_sn': (post or {}).get('duration_s'),
            'deneme': (post or {}).get('trial'), 'metrikler': vals,
        }
        media_out[m['id']] = rec
        for name, hours in MILESTONES:
            if age_h >= hours and (m['id'], name) not in taken and age_h < hours + 24 * 3:
                new_snaps.append({'at': now.isoformat(timespec='seconds'), 'milestone': name, **rec})

    account = account_summary(api, ig_id)
    save('insights_latest.json', {'guncelleme': now.astimezone(TZ).isoformat(timespec='minutes'), 'hesap': account,
                                  'desteklenmeyen_metrikler': sorted(unsupported), 'media': media_out})
    if new_snaps:
        with snaps_path.open('a', encoding='utf-8') as f:
            for s in new_snaps:
                f.write(json.dumps(s, ensure_ascii=False) + '\n')
    write_report(media_out, account, now)
    print(f'{len(media_out)} gönderi okundu, {len(new_snaps)} yeni ölçüm kaydı. Takipçi: {account.get("followers_count")}')


def write_report(media_out, account, now):
    rows = sorted(media_out.values(), key=lambda r: r['tarih'], reverse=True)
    reels = [r for r in rows if r['tur'] == 'reels'][:30]

    def g(r, k):
        v = r['metrikler'].get(k)
        return v if isinstance(v, (int, float)) else None

    feats = []
    for r in reels:
        reach = g(r, 'reach')
        dur = r.get('sure_sn')
        avg = g(r, 'ig_reels_avg_watch_time')
        avg_s = avg / 1000 if avg and avg > 100 else avg          # API milisaniye döndürüyor
        skip = g(r, 'reels_skip_rate')
        skip = skip / 100 if skip and skip > 1 else skip
        feats.append({
            'watch': (avg_s / dur) if avg_s and dur else None,
            'hold3': (1 - skip) if skip is not None else None,
            'sends': rate(g(r, 'shares'), reach), 'saves': rate(g(r, 'saved'), reach), 'likes': rate(g(r, 'likes'), reach),
            'avg_s': avg_s,
        })
    z = {k: zscores([f[k] for f in feats]) for k in ('watch', 'hold3', 'sends', 'saves', 'likes')}
    weights = {'watch': .30, 'hold3': .20, 'sends': .25, 'saves': .15, 'likes': .10}
    for i, f in enumerate(feats):
        parts = [(weights[k], z[k][i]) for k in weights if z[k][i] is not None]
        f['lrs'] = round(sum(w * v for w, v in parts) / sum(w for w, _ in parts), 2) if parts else None

    def pct(v):
        return '–' if v is None else f'%{v * 100:.1f}'.replace('.', ',')

    def num(v):
        return '–' if v is None else f'{v:,.0f}'.replace(',', '.')

    lines = [f'# @lingoof.app istatistikleri', '', f'Güncelleme: {now.astimezone(TZ):%d.%m.%Y %H:%M} (Türkiye saati)', '']
    a7 = account.get('son_7_gun', {})
    a28 = account.get('son_28_gun', {})
    lines += ['## Hesap', '',
              f'- Takipçi: {num(account.get("followers_count"))} · gönderi: {num(account.get("media_count"))}',
              f'- Son 7 gün: görüntüleme {num(a7.get("views"))}, erişim {num(a7.get("reach"))}, etkileşim {num(a7.get("total_interactions"))}, '
              f'takip {num(a7.get("follows_and_unfollows:FOLLOWER"))}, takipten çıkma {num(a7.get("follows_and_unfollows:NON_FOLLOWER"))}, '
              f'profil linki dokunuşu {num(a7.get("profile_links_taps"))}',
              f'- Son 28 gün: görüntüleme {num(a28.get("views"))}, erişim {num(a28.get("reach"))}, etkileşim {num(a28.get("total_interactions"))}', '']
    lines += ['## Son reels (LRS: son 30 reels\'e göre; 0 ortalama, + iyi)', '',
              '| Tarih | # | İlk satır | İzlenme | Erişim | Ort. izlenme | İzlenme oranı | İlk 3 sn kalma | Paylaşım/erişim | Kayıt/erişim | LRS |',
              '|---|---|---|---|---|---|---|---|---|---|---|']
    for r, f in zip(reels, feats):
        lines.append(f'| {r["tarih"][:16].replace("T", " ")} | {r["n"] or ""} | [{r["ilk_satir"][:50].replace("|", "/")}]({r["link"]}) | '
                     f'{num(g(r, "views"))} | {num(g(r, "reach"))} | {"–" if f["avg_s"] is None else f"{f['avg_s']:.1f} sn"} | '
                     f'{pct(f["watch"])} | {pct(f["hold3"])} | {pct(f["sends"])} | {pct(f["saves"])} | {"–" if f["lrs"] is None else f["lrs"]} |')
    feed = [r for r in rows if r['tur'] != 'reels'][:20]
    lines += ['', '## Son carousel ve görseller', '',
              '| Tarih | # | İlk satır | Görüntüleme | Erişim | Kayıt/erişim | Paylaşım/erişim | Takip | Profil ziyareti |',
              '|---|---|---|---|---|---|---|---|---|']
    for r in feed:
        reach = g(r, 'reach')
        lines.append(f'| {r["tarih"][:16].replace("T", " ")} | {r["n"] or ""} | [{r["ilk_satir"][:50].replace("|", "/")}]({r["link"]}) | '
                     f'{num(g(r, "views"))} | {num(reach)} | {pct(rate(g(r, "saved"), reach))} | {pct(rate(g(r, "shares"), reach))} | '
                     f'{num(g(r, "follows"))} | {num(g(r, "profile_visits"))} |')
    lines += ['', 'Kalıcı ölçümler (24 sa, 72 sa, 7 gün) insights.jsonl dosyasında. Karar için 72 saatlik ölçüm esas alınır.', '']
    (ROOT / 'insights.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
