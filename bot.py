#!/usr/bin/env python3
"""LINGOOF Instagram botu.

posts.json'daki planı Türkiye saatiyle, her gönderinin kendi tarih ve saatinde resmi Instagram API'siyle paylaşır:
reels (video + kapak) ve carousel (2–10 JPEG). Medya dosyaları deponun GitHub Pages sayfasından herkese açık
adresle verilir; Instagram dosyayı oradan kendisi çeker. Hangi gönderinin paylaşıldığı state.json'da tutulur,
aynı gönderi iki kez gitmez.

Ortam değişkenleri:
  IG_TOKEN   Instagram uzun ömürlü erişim token'ı (GitHub secret; "Instagram ile giriş")
  FB_TOKEN   Facebook ile giriş token'ı (GitHub secret). Varsa bot graph.facebook.com üzerinden çalışır ve reels'e
             Instagram'ın müzik kütüphanesinden ses ekleyebilir (Instagram Audio API yalnızca Facebook ile girişte var).
  MODE       "post" (varsayılan): saati gelen gönderiyi paylaşır
             "dry":      hiçbir şey göndermez; token'ı, hesabı ve sıradaki gönderiyi gösterir
             "validate": sıradaki reels ve carousel için Instagram'da hazırlık kaydı oluşturur ama YAYINLAMAZ;
                         Instagram'ın dosyaları kabul ettiğini doğrular (hesapta hiçbir şey görünmez)
             "audio":    trend müzik ve sesleri listeler (yalnızca FB_TOKEN ile); hiçbir şey göndermez
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
    def __init__(self, token, version, host='graph.instagram.com'):
        self.token = token
        self.host = host
        self.base = f'https://{host}/{version}' if version else f'https://{host}'

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
        if post.get('trial') and post['trial'] not in ('MANUAL', 'SS_PERFORMANCE'):
            return 'trial yalnızca MANUAL ya da SS_PERFORMANCE olabilir'
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


AUDIO_PATHS = ('ig_audio',)


def audio_list(api, ig_id, audio_type='music', query=None):
    """Instagram Audio API: sorgu yoksa o anki trend listesini döndürür. Uç noktanın tam yolu belgelerde net olmadığı
    için bilinen iki biçim sırayla denenir; ilk çalışan kullanılır."""
    params = {'audio_type': audio_type}
    if query:
        params['search_query'] = query
    last = None
    for path in AUDIO_PATHS:
        try:
            r = api.call('GET', path, dict(params, ig_user_id=ig_id))
        except RuntimeError as e:
            last = e
            continue
        items = r.get('audio') or r.get('data') or []
        out = []
        for it in items:
            aid = it.get('audio_id') or it.get('id')
            if aid:
                out.append({'id': str(aid), 'title': it.get('title', ''), 'artist': it.get('display_artist') or it.get('ig_username', ''),
                            'ms': it.get('duration_in_ms') or it.get('duration_ms') or 0})
        return out
    raise RuntimeError(f'Müzik listesi alınamadı: {last}')


def pick_audio(api, ig_id, post, state, cfg):
    """Reels için müzik seçer: gönderide 'music_query' varsa onunla arar, yoksa trend listesini kullanır.
    Son kullanılan parçaları tekrar etmemeye çalışır. Seçemezse None döner (gönderi kendi sesiyle gider)."""
    mcfg = cfg.get('music', {})
    if not mcfg.get('enabled') or post.get('music') is False or api.host != 'graph.facebook.com':
        return None
    kind = post.get('music_type') or mcfg.get('type', 'music')
    try:
        items = audio_list(api, ig_id, kind, post.get('music_query'))
        if not items and post.get('music_query'):
            items = audio_list(api, ig_id, kind)
    except RuntimeError as e:
        print(f'(Not) {e}')
        return None
    used = set(state.get('audio_used', [])[-int(mcfg.get('no_repeat', 12)):])
    need = int(post.get('duration_ms', 0))
    fit = [a for a in items if a['id'] not in used and (not need or not a['ms'] or a['ms'] >= need)]
    pick = (fit or [a for a in items if a['id'] not in used] or items or [None])[0]
    if not pick:
        return None
    return dict(pick, audio_volume=int(post.get('music_volume', mcfg.get('audio_volume', 30))),
                video_volume=int(mcfg.get('video_volume', 100)))


def build(api, ig_id, post, base, timeout, audio=None):
    """Gönderinin hazırlık kaydını oluşturur ve işlenmesini bekler; yayınlamaz. Kayıt kimliğini döndürür."""
    cap = post.get('caption', '')
    if post['kind'] == 'reels':
        params = {'media_type': 'REELS', 'video_url': base + post['media'], 'caption': cap}
        if post.get('trial'):  # deneme reels: önce takipçi olmayanlara gösterilir
            params['trial_params'] = json.dumps({'graduation_strategy': post['trial']})
        else:
            params['share_to_feed'] = 'true'
        if audio:
            params['audio_configuration'] = json.dumps({'audio_id': audio['id'], 'audio_volume': audio['audio_volume'],
                                                        'video_volume': audio['video_volume']})
        elif post.get('audio_name'):
            params['audio_name'] = post['audio_name']
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
    fb_token = os.environ.get('FB_TOKEN', '').strip()
    now = datetime.now(TZ)
    timeout = int(cfg.get('video_timeout_seconds', 600))
    version = cfg.get('api_version', 'v24.0')

    api = None
    if fb_token and (cfg.get('facebook_login') or mode == 'audio'):
        # Facebook ile giriş: hesabı bağlı Facebook sayfası üzerinden bulur. Olmazsa IG_TOKEN'a düşer.
        fapi = Api(fb_token, version, 'graph.facebook.com')
        want = cfg.get('ig_username', 'lingoof.app').lstrip('@').lower()
        try:
            pages = fapi.call('GET', 'me/accounts', {'fields': 'name,instagram_business_account{id,username}', 'limit': '100'}).get('data', [])
            acc = next((p['instagram_business_account'] for p in pages
                        if p.get('instagram_business_account', {}).get('username', '').lower() == want), None)
            if acc:
                api, ig_id = fapi, acc['id']
                print(f'Hesap: @{acc["username"]} (Facebook ile giriş)  ·  Türkiye saati: {now:%d.%m.%Y %H:%M}')
            else:
                report('Facebook bağlantısı', f'@{want} bu token ile erişilen Facebook sayfalarına bağlı görünmüyor; IG_TOKEN kullanılıyor.', 'warning')
        except RuntimeError as e:
            report('Facebook bağlantısı', f'FB_TOKEN ile bağlanılamadı, IG_TOKEN kullanılıyor: {e}', 'warning')
    if api is None:
        if not token:
            sys.exit('IG_TOKEN tanımlı değil: GitHub > Settings > Secrets and variables > Actions altına ekle.')
        api = Api(token, version)
        try:
            me = api.call('GET', 'me', {'fields': 'user_id,username,account_type'})
        except RuntimeError as e:
            fail(state, now, None, f'Instagram hesabına bağlanılamadı (token geçersiz ya da süresi dolmuş olabilir): {e}')
        ig_id = me.get('user_id') or me.get('id')
        print(f'Hesap: @{me.get("username")} ({me.get("account_type", "?")})  ·  Türkiye saati: {now:%d.%m.%Y %H:%M}')

    if mode == 'audio':
        if api.host != 'graph.facebook.com':
            sys.exit('Müzik listesi için FB_TOKEN gerekli (Instagram Audio API yalnızca Facebook ile girişte var).')
        for q in [x.strip() for x in (os.environ.get('AUDIO_Q') or cfg.get('music', {}).get('probe_queries', '')).split('|') if x.strip()]:
            try:
                items = audio_list(api, ig_id, 'music', q)
                print(f'\n== ara: {q} · {len(items)} sonuç')
                for it in items[:12]:
                    print(f"  {it['id']} · {it['title']} · {it['artist']} · {it['ms'] // 1000 if it['ms'] else '?'} sn")
            except RuntimeError as e:
                print(f'\n== ara: {q} · HATA {e}')
        for kind in ('music', 'original_sound'):
            for path in AUDIO_PATHS:
                p = path.format(ig=ig_id)
                prm = {'audio_type': kind} if '{ig}' in path else {'audio_type': kind, 'ig_user_id': ig_id}
                try:
                    r = api.call('GET', p, prm)
                    items = r.get('audio') or r.get('data') or []
                    print(f'\n== {kind} · {p}: {len(items)} sonuç · alanlar: {sorted(items[0].keys()) if items else "-"}')
                    for it in items[:15]:
                        print(f"  {it.get('audio_id') or it.get('id')} · {it.get('title', '')} · {it.get('display_artist') or it.get('ig_username', '')} · {it.get('duration_in_ms', '')}")
                except RuntimeError as e:
                    print(f'\n== {kind} · {p}: HATA {e}')
        return
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
                audio = pick_audio(api, ig_id, p, state, cfg) if p['kind'] == 'reels' else None
                if audio:
                    print(f'Müzik: {audio["title"]} · {audio["artist"]} ({audio["id"]})')
                cid = build(api, ig_id, p, base, timeout, audio)
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
    audio = pick_audio(api, ig_id, post, state, cfg) if post['kind'] == 'reels' else None
    try:
        try:
            cid = build(api, ig_id, post, base, timeout, audio)
        except RuntimeError as e:
            if not audio:
                raise
            # Müzik eklenemezse gönderi kaçmasın: kendi sesiyle tekrar denenir.
            report('Müzik eklenemedi', f'#{post["n"]}: {audio["title"]} ({audio["id"]}) → {e}. Kendi sesiyle paylaşılıyor.', 'warning')
            audio = None
            cid = build(api, ig_id, post, base, timeout)
        media_id = api.call('POST', f'{ig_id}/media_publish', {'creation_id': cid})['id']
    except RuntimeError as e:
        fail(state, now, post['n'], e)
    entry = {'id': media_id, 'at': now.isoformat(timespec='seconds'), 'kind': post['kind']}
    if audio:
        entry['audio'] = {k: audio[k] for k in ('id', 'title', 'artist')}
        state.setdefault('audio_used', []).append(audio['id'])
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
