#!/usr/bin/env python3
"""LINGOOF Instagram botu.

posts.json'daki planı Türkiye saatiyle, her gönderinin kendi tarih ve saatinde resmi Instagram API'siyle paylaşır:
reels (video + kapak) ve carousel (2–10 JPEG). Medya dosyaları deponun GitHub Pages sayfasından herkese açık
adresle verilir; Instagram dosyayı oradan kendisi çeker. Hangi gönderinin paylaşıldığı state.json'da tutulur,
aynı gönderi iki kez gitmez.

Ortam değişkenleri:
  IG_TOKEN   Instagram uzun ömürlü erişim token'ı (GitHub secret)
  MODE       "post" (varsayılan): saati gelen gönderiyi paylaşır
             "dry":      hiçbir şey göndermez; token'ı, hesabı ve sıradaki gönderiyi gösterir
             "validate": sıradaki reels ve carousel için Instagram'da hazırlık kaydı oluşturur ama YAYINLAMAZ;
                         Instagram'ın dosyaları kabul ettiğini doğrular (hesapta hiçbir şey görünmez)
Yalnızca Python standart kütüphanesi kullanılır.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
TZ = ZoneInfo('Europe/Istanbul')
CAPTION_MAX = 2200            # Instagram açıklama sınırı
HASHTAG_MAX = 30
CAROUSEL_MIN, CAROUSEL_MAX = 2, 10
MAX_TRIES = 3                 # aynı gönderi bu kadar kez hata verirse atlanır


def load(name, default=None):
    path = ROOT / name
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def save(name, obj):
    (ROOT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


class Api:
    def __init__(self, token, version):
        self.token = token
        self.base = f'https://graph.instagram.com/{version}' if version else 'https://graph.instagram.com'

    def call(self, method, path, params=None):
        query = dict(params or {}, access_token=self.token)
        body = urllib.parse.urlencode(query).encode()
        url = f'{self.base}/{path}'
        if method == 'GET':
            req = urllib.request.Request(f'{url}?{body.decode()}')
        else:
            req = urllib.request.Request(url, data=body, method='POST')
        last = None
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=90) as r:
                    return json.loads(r.read().decode())
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors='replace').replace(self.token, '***')
                if e.code >= 500 and attempt < 2:      # Meta tarafında geçici hata
                    last = f'{e.code} {detail}'
                    time.sleep(15 * (attempt + 1))
                    continue
                raise RuntimeError(f'Instagram API {e.code} ({path}): {detail}') from None
            except urllib.error.URLError as e:
                last = str(e)
                time.sleep(15 * (attempt + 1))
        raise RuntimeError(f'Instagram API bağlantı hatası ({path}): {last}')


def wait_ready(api, cid, timeout):
    """Hazırlık kaydı (container) işlenene kadar bekler. Videolarda Instagram dosyayı indirip işler, birkaç dakika sürebilir."""
    waited, step = 0, 5
    while waited <= timeout:
        st = api.call('GET', cid, {'fields': 'status_code,status'})
        code = st.get('status_code')
        if code in ('FINISHED', 'PUBLISHED'):
            return
        if code in ('ERROR', 'EXPIRED'):
            raise RuntimeError(f'Instagram dosyayı işleyemedi ({code}): {st.get("status")}')
        time.sleep(step)
        waited += step
        step = min(step + 5, 20)
    raise RuntimeError(f'Instagram dosyayı {timeout} saniyede işleyemedi')


def slot_time(post):
    d = date.fromisoformat(post['date'])
    hh, mm = (int(x) for x in post['time'].split(':'))
    return datetime(d.year, d.month, d.day, hh, mm, tzinfo=TZ)


def media_base(cfg):
    base = cfg.get('media_base_url') or 'auto'
    if base != 'auto':
        return base.rstrip('/') + '/'
    repo = os.environ.get('GITHUB_REPOSITORY')
    if not repo:
        return None
    owner, name = repo.split('/', 1)
    return f'https://{owner.lower()}.github.io/{name}/media/'


def files_of(post):
    media = post['media'] if isinstance(post['media'], list) else [post['media']]
    return media + ([post['cover']] if post.get('cover') else [])


def check_post(post):
    """Gönderinin biçimini kontrol eder; sorun varsa açıklamasını döndürür."""
    cap = post.get('caption', '')
    if len(cap) > CAPTION_MAX:
        return f'açıklama {len(cap)} karakter (sınır {CAPTION_MAX})'
    if cap.count('#') > HASHTAG_MAX:
        return f'açıklamada {cap.count("#")} hashtag var (sınır {HASHTAG_MAX})'
    if post['kind'] == 'reels':
        if not isinstance(post['media'], str) or not post['media'].lower().endswith(('.mp4', '.mov')):
            return 'reels için tek bir .mp4 ya da .mov dosyası gerekli'
    elif post['kind'] == 'carousel':
        m = post['media']
        if not isinstance(m, list) or not CAROUSEL_MIN <= len(m) <= CAROUSEL_MAX:
            return f'carousel için {CAROUSEL_MIN}–{CAROUSEL_MAX} görsel gerekli'
        if any(not x.lower().endswith(('.jpg', '.jpeg')) for x in m):
            return 'carousel görselleri JPEG olmalı'
    else:
        return f'bilinmeyen tür: {post["kind"]}'
    return None


def url_ok(url):
    try:
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status == 200
    except Exception:
        return False


def build(api, ig_id, post, base, timeout):
    """Gönderinin hazırlık kaydını oluşturur ve işlenmesini bekler; yayınlamaz. Kayıt kimliğini döndürür."""
    cap = post.get('caption', '')
    if post['kind'] == 'reels':
        params = {'media_type': 'REELS', 'video_url': base + post['media'], 'caption': cap,
                  'share_to_feed': 'true'}
        if post.get('cover'):
            params['cover_url'] = base + post['cover']
        elif post.get('thumb_offset_ms') is not None:
            params['thumb_offset'] = str(int(post['thumb_offset_ms']))
        cid = api.call('POST', f'{ig_id}/media', params)['id']
        wait_ready(api, cid, timeout)
        return cid
    children = []
    for f in post['media']:
        c = api.call('POST', f'{ig_id}/media', {'image_url': base + f, 'is_carousel_item': 'true'})['id']
        children.append(c)
    for c in children:
        wait_ready(api, c, 180)
    cid = api.call('POST', f'{ig_id}/media', {'media_type': 'CAROUSEL', 'children': ','.join(children), 'caption': cap})['id']
    wait_ready(api, cid, 180)
    return cid


def report(title, msg, level='error'):
    one = msg.replace('%', '%25').replace('\r', '').replace('\n', '%0A')
    print(f'::{level} title={title}::{one}')
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            f.write(f'### {title}\n\n```\n{msg}\n```\n')


def fail(state, now, n, err):
    state['last_error'] = {'at': now.isoformat(timespec='seconds'), 'n': n, 'error': str(err)[:800]}
    if n is not None:
        tries = state.setdefault('failures', {})
        tries[str(n)] = tries.get(str(n), 0) + 1
        if tries[str(n)] >= MAX_TRIES and n not in state['skipped']:
            state['skipped'].append(n)
            print(f'#{n} {MAX_TRIES} kez hata verdi, atlanıyor.')
    save('state.json', state)
    report('Instagram paylaşımı başarısız', f'#{n}: {err}' if n is not None else str(err))
    sys.exit(1)


def cleanup(post):
    """Paylaşılan gönderinin medya dosyalarını depodan siler; Pages sitesi küçük kalır (dosyalar git geçmişinde durur)."""
    for f in files_of(post):
        p = ROOT / 'media' / f
        p.unlink(missing_ok=True)
        d = p.parent
        while d != ROOT / 'media' and d.exists() and not any(d.iterdir()):
            d.rmdir()
            d = d.parent


def main():
    cfg = load('config.json', {})
    state = load('state.json', {'posted': {}, 'skipped': []})
    posts = load('posts.json', [])
    mode = (os.environ.get('MODE') or 'post').strip().lower()
    token = os.environ.get('IG_TOKEN', '').strip()
    now = datetime.now(TZ)
    timeout = int(cfg.get('video_timeout_seconds', 600))

    if not token:
        sys.exit('IG_TOKEN tanımlı değil: GitHub > Settings > Secrets and variables > Actions altına ekle.')
    api = Api(token, cfg.get('api_version', 'v24.0'))
    try:
        me = api.call('GET', 'me', {'fields': 'user_id,username,account_type'})
    except RuntimeError as e:
        fail(state, now, None, f'Instagram hesabına bağlanılamadı (token geçersiz ya da süresi dolmuş olabilir): {e}')
    ig_id = me.get('user_id') or me.get('id')
    print(f'Hesap: @{me.get("username")} ({me.get("account_type", "?")})  ·  Türkiye saati: {now:%d.%m.%Y %H:%M}')
    base = media_base(cfg)

    bad = [(p['n'], check_post(p)) for p in posts if check_post(p)]
    for n, why in bad:
        report('Plan hatası', f'#{n}: {why}', 'warning')

    grace = timedelta(hours=float(cfg.get('grace_hours', 6)))
    done = set(state['posted']) | {str(n) for n in state['skipped']}
    pending = sorted((p for p in posts if str(p['n']) not in done), key=slot_time)
    due = [p for p in pending if slot_time(p) <= now]
    fresh = [p for p in due if now - slot_time(p) <= grace]
    stale = [p for p in due if p not in fresh]

    if mode in ('dry', 'validate'):
        try:
            lim = api.call('GET', f'{ig_id}/content_publishing_limit', {'fields': 'quota_usage,config'})
            print(f'Son 24 saatte API ile paylaşılan: {lim.get("data", [{}])[0].get("quota_usage", "?")}')
        except RuntimeError as e:
            print(f'(Not) Paylaşım kotası okunamadı: {e}')
        upcoming = [p for p in pending if p not in stale]
        print(f'Bekleyen gönderi: {len(upcoming)}  ·  medya adresi: {base}')
        if stale:
            print(f'(Not) Saati {grace} saatten fazla geçmiş {len(stale)} gönderi ilk gerçek çalışmada atlanacak.')
        if mode == 'dry':
            for p in upcoming[:4]:
                missing = [f for f in files_of(p) if not url_ok(base + f)] if base else ['(medya adresi yok)']
                print(f'\n#{p["n"]} · {slot_time(p):%d.%m %H:%M} · {p["kind"]} · {p.get("title", "")}'
                      + (f'\n  EKSİK DOSYA: {", ".join(missing)}' if missing else '  · dosyalar yerinde'))
            return
        tested = set()
        # Plandaki gönderilerden önce depodaki deneme dosyaları (media/_deneme) denenir; plan boşken de doğrulama yapılabilir.
        for p in cfg.get('test_posts', []) + upcoming:
            if p['kind'] in tested or check_post(p):
                continue
            missing = [f for f in files_of(p) if not url_ok(base + f)]
            if missing:
                print(f'#{p["n"]} atlandı, dosyalar henüz yayında değil: {", ".join(missing)}')
                continue
            t0 = time.time()
            try:
                cid = build(api, ig_id, p, base, timeout)
                print(f'DOĞRULANDI · #{p["n"]} {p["kind"]}: Instagram dosyaları kabul etti ({time.time() - t0:.0f} sn). Yayınlanmadı.')
                tested.add(p['kind'])
            except RuntimeError as e:
                report('Doğrulama başarısız', f'#{p["n"]} {p["kind"]}: {e}')
            if tested >= {'reels', 'carousel'}:
                break
        return

    for p in stale:
        state['skipped'].append(p['n'])
        state.setdefault('missed', []).append({'n': p['n'], 'slot': f'{p["date"]} {p["time"]}'})
        report('Saati geçen gönderi atlandı', f'#{p["n"]} ({slot_time(p):%d.%m %H:%M}) {p.get("title", "")}', 'warning')
    if not fresh:
        save('state.json', state)
        nxt = next((p for p in pending if slot_time(p) > now), None)
        print('Şu an paylaşılacak bir şey yok.' + (f' Sıradaki: #{nxt["n"]} · {slot_time(nxt):%d.%m.%Y %H:%M}' if nxt else ' Plan tamamlandı.'))
        return
    for p in fresh[:-1]:                     # aynı anda birden çok gönderi düşerse en yenisi gider, diğerleri raporlanır
        state['skipped'].append(p['n'])
        state.setdefault('missed', []).append({'n': p['n'], 'slot': f'{p["date"]} {p["time"]}'})
    post = fresh[-1]

    why = check_post(post)
    if why:
        fail(state, now, post['n'], why)
    missing = [f for f in files_of(post) if not url_ok(base + f)]
    if missing:
        fail(state, now, post['n'], f'medya dosyası yayında değil (GitHub Pages açık mı, dosya yüklendi mi?): {", ".join(missing)}')
    try:
        cid = build(api, ig_id, post, base, timeout)
        media_id = api.call('POST', f'{ig_id}/media_publish', {'creation_id': cid})['id']
    except RuntimeError as e:
        fail(state, now, post['n'], e)
    entry = {'id': media_id, 'at': now.isoformat(timespec='seconds'), 'kind': post['kind']}
    try:
        entry['permalink'] = api.call('GET', media_id, {'fields': 'permalink'}).get('permalink')
    except RuntimeError:
        pass
    state['posted'][str(post['n'])] = entry
    state.get('failures', {}).pop(str(post['n']), None)
    if cfg.get('cleanup_after_post', True):
        cleanup(post)
    save('state.json', state)
    print(f"Paylaşıldı: #{post['n']} {post['kind']} ({post['date']} {post['time']}) → {entry.get('permalink') or media_id}")


if __name__ == '__main__':
    main()
