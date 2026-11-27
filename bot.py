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
             "muzik":    planlanan müzik parçalarını Instagram'a sorar, reddedilenleri listeler (yayınlamaz)
             "olc":      paylaşılmış son reels'leri Instagram'daki son halleriyle indirir (ses dengesi ölçümü için)
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
HASHTAG_MAX = 5               # Instagram Aralık 2025'ten beri gönderi başına en fazla 5 hashtag'e izin veriyor
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
    return media + ([post['cover']] if post.get('cover') else []) + ([post['media_fallback']] if post.get('media_fallback') else [])


def hashtags(cap):
    """Açıklamadaki gerçek hashtag'ler: # işaretinden sonra en az bir harf gelen kelimeler (#1, #2 gibi sayılar sayılmaz)."""
    import re
    return re.findall(r'#\w*[^\W\d_]\w*', cap)


def check_post(post):
    """Gönderinin biçimini kontrol eder; sorun varsa açıklamasını döndürür."""
    cap = post.get('caption', '')
    if len(cap) > CAPTION_MAX:
        return f'açıklama {len(cap)} karakter (sınır {CAPTION_MAX})'
    if len(hashtags(cap)) > HASHTAG_MAX:
        return f'açıklamada {len(hashtags(cap))} hashtag var (sınır {HASHTAG_MAX})'
    if post.get('collaborators') and (not isinstance(post['collaborators'], list) or len(post['collaborators']) > 3):
        return 'collaborators en fazla 3 kullanıcı adından oluşan bir liste olmalı'
    if post['kind'] == 'reels':
        if not isinstance(post['media'], str) or not post['media'].lower().endswith(('.mp4', '.mov')):
            return 'reels için tek bir .mp4 ya da .mov dosyası gerekli'
        if post.get('media_fallback') and not post['media_fallback'].lower().endswith(('.mp4', '.mov')):
            return 'media_fallback bir .mp4 ya da .mov dosyası olmalı'
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
    vol = dict(audio_volume=int(post.get('music_volume', mcfg.get('audio_volume', 30))), video_volume=int(mcfg.get('video_volume', 100)))
    override = cfg.get('music_overrides', {}).get(str(post['n']))
    if override or post.get('music_id'):
        aid = (override or {}).get('id') or post['music_id']
        return dict(id=str(aid), title=(override or {}).get('title') or post.get('music_title', ''), artist=(override or {}).get('artist', ''), ms=0, **vol)
    if not mcfg.get('auto'):
        return None                      # yalnızca seçilmiş parçalar; trend listesinden kendiliğinden seçim kapalı
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
    return dict(pick, **vol)


def build(api, ig_id, post, base, timeout, audio=None, media=None):
    """Gönderinin hazırlık kaydını oluşturur ve işlenmesini bekler; yayınlamaz. Kayıt kimliğini döndürür."""
    cap = post.get('caption', '')
    extra = {}
    if post.get('collaborators'):  # ortak gönderi: davet edilen hesap kabul edince iki profilde ve iki kitlede görünür
        extra['collaborators'] = json.dumps([u.lstrip('@') for u in post['collaborators']])
    if post.get('location_id'):
        extra['location_id'] = str(post['location_id'])
    if post['kind'] == 'reels':
        params = {'media_type': 'REELS', 'video_url': base + (media or post['media']), 'caption': cap, **extra}
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
    alts = post.get('alt_texts') or []
    for i, f in enumerate(post['media']):
        item = {'image_url': base + f, 'is_carousel_item': 'true'}
        alt = alts[i] if i < len(alts) else post.get('alt_text')
        if alt:  # erişilebilirlik ve arama için görsel açıklaması
            item['alt_text'] = alt[:1000]
        try:
            c = api.call('POST', f'{ig_id}/media', item)['id']
        except RuntimeError:
            if 'alt_text' not in item:
                raise
            item.pop('alt_text')        # alan bu API sürümünde kabul edilmezse görsel alt metinsiz gider
            c = api.call('POST', f'{ig_id}/media', item)['id']
        children.append(c)
    for c in children:
        wait_ready(api, c, 180)
    cid = api.call('POST', f'{ig_id}/media', {'media_type': 'CAROUSEL', 'children': ','.join(children), 'caption': cap, **extra})['id']
    wait_ready(api, cid, 180)
    return cid


def post_story(api, ig_id, post, base, timeout):
    """Yayınlanan reels'i takipçilerin Story akışında da gösterir (deneme reels'te yapılmaz: onlar önce takipçi olmayanlara gider).
    Fon müzikli sürüm varsa o kullanılır, çünkü Story'ye Instagram müziği eklenemiyor. Hata olursa ana gönderi etkilenmez."""
    video = post.get('media_fallback') or post['media']
    cid = api.call('POST', f'{ig_id}/media', {'media_type': 'STORIES', 'video_url': base + video})['id']
    wait_ready(api, cid, timeout)
    return api.call('POST', f'{ig_id}/media_publish', {'creation_id': cid})['id']


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
    if mode == 'muzik':
        # Planlanan her müzik parçasını kısa deneme videosuyla Instagram'a sorar (yayınlamaz):
        # hangi parçaların kabul edilmediği önceden görülür.
        base = media_base(cfg)
        test = next(p for p in cfg.get('test_posts', []) if p['kind'] == 'reels')
        ids = {}
        for p in posts:
            if str(p['n']) in state['posted']:
                continue
            if p.get('music_id'):
                ids.setdefault(str(p['music_id']), [p.get('music_title', ''), []])[1].append(p['n'])
        for o in cfg.get('music_overrides', {}).values():
            ids.setdefault(str(o['id']), [o.get('title', ''), []])
        print(f'{len(ids)} farklı parça deneniyor')
        cids = {}
        for aid in ids:
            try:
                r = api.call('POST', f'{ig_id}/media', {'media_type': 'REELS', 'video_url': base + test['media'], 'share_to_feed': 'false',
                    'audio_configuration': json.dumps({'audio_id': aid, 'audio_volume': 18, 'video_volume': 100})})
                cids[aid] = r['id']
            except RuntimeError as e:
                print(f'RED  {aid} · {ids[aid][0]} · gönderiler {ids[aid][1]} · {e}')
        t0 = time.time(); left = dict(cids)
        while left and time.time() - t0 < 600:
            time.sleep(15)
            for aid, cid in list(left.items()):
                st = api.call('GET', cid, {'fields': 'status_code,status'})
                if st.get('status_code') in ('FINISHED', 'PUBLISHED'):
                    print(f'TAMAM {aid} · {ids[aid][0]}'); left.pop(aid)
                elif st.get('status_code') == 'ERROR':
                    print(f'RED  {aid} · {ids[aid][0]} · gönderiler {ids[aid][1]} · {st.get("status")}'); left.pop(aid)
        for aid in left:
            print(f'BELİRSİZ {aid} · {ids[aid][0]}')
        return
    if mode == 'olc':
        # Paylaşılmış reels'leri Instagram'ın yayındaki haliyle indirir (müzik eklenmiş son karışım);
        # dosyalar iş akışında 1 günlük artifact olarak saklanır, ses dengesi ölçülür.
        import urllib.request
        os.makedirs('olcum', exist_ok=True)
        if token:
            try:
                me = Api(token, version).call('GET', 'me', {'fields': 'username,account_type'})
                print(f'Hesap türü: {me.get("account_type")}')
            except RuntimeError as e:
                print(f'Hesap türü okunamadı: {e}')
        reels = sorted(((n, e) for n, e in state['posted'].items() if e.get('kind') == 'reels'), key=lambda kv: kv[1].get('at', ''))
        for n, e in reels[-int(os.environ.get('OLC_ADET', '2')):]:
            try:
                info = api.call('GET', e['id'], {'fields': 'media_type,media_product_type,media_url,permalink,timestamp'})
            except RuntimeError as err:
                print(f'#{n} okunamadı: {err}')
                continue
            url = info.pop('media_url', None)
            print(f'#{n} · {info.get("permalink")} · müzik: {(e.get("audio") or {}).get("title", "-")} · ' + ('indiriliyor' if url else 'media_url verilmedi'))
            if url:
                urllib.request.urlretrieve(url, f'olcum/reels_{n}.mp4')
                try:
                    # 0,25 sn'lik pencerelerde ses seviyesi (dBFS); müziksiz sürümle karşılaştırmak için loga yazılır.
                    import subprocess, numpy as np, imageio_ffmpeg
                    raw = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-i', f'olcum/reels_{n}.mp4', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                                         capture_output=True, check=True).stdout
                    x = np.frombuffer(raw, np.float32); w = 12000; k = len(x) // w
                    db = 20 * np.log10(np.sqrt(np.mean(x[:k * w].reshape(k, w) ** 2, axis=1) + 1e-12))
                    print(f'PROFIL #{n} ' + json.dumps([round(float(v), 1) for v in db]))
                except Exception as err:
                    print(f'Ses profili çıkarılamadı: {err}')
        return
    base = media_base(cfg)

    bad = [(p['n'], check_post(p)) for p in posts if check_post(p)]
    for n, why in bad:
        report('Plan hatası', f'#{n}: {why}', 'warning')

    grace = timedelta(hours=float(cfg.get('grace_hours', 6)))
    done = set(state['posted']) | {str(n) for n in state['skipped']}
    # "hold": true olan gönderiler beklemede: paylaşılmaz, atlanmış da sayılmaz (yeniden render ya da sonraki dönem için)
    pending = sorted((p for p in posts if str(p['n']) not in done and not p.get('hold')), key=slot_time)
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
        # Önce sıradaki gerçek gönderiler (müziğiyle birlikte) denenir; dosyaları yayında değilse depodaki deneme dosyaları (media/_deneme).
        for p in upcoming[:6] + cfg.get('test_posts', []):
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
                    print(f'Müzik: {" · ".join(x for x in (audio["title"], audio["artist"]) if x)} ({audio["id"]})')
                cid = build(api, ig_id, p, base, timeout, audio, None if audio else p.get('media_fallback'))
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
    # media: müziksiz (Instagram müziği altına eklenir) · media_fallback: kendi fon müziğimizle
    plain = post.get('media_fallback') if not audio else None
    try:
        try:
            cid = build(api, ig_id, post, base, timeout, audio, plain)
        except RuntimeError as e:
            if not audio:
                raise
            # Müzik eklenemezse gönderi kaçmasın: kendi fon müziğimizle tekrar denenir.
            report('Müzik eklenemedi', f'#{post["n"]}: {audio["title"]} ({audio["id"]}) → {e}. Kendi müziğiyle paylaşılıyor.', 'warning')
            audio = None
            cid = build(api, ig_id, post, base, timeout, None, post.get('media_fallback'))
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
    if post['kind'] == 'reels' and not post.get('trial') and post.get('story', cfg.get('story_after_reel', False)):
        try:
            entry['story'] = post_story(api, ig_id, post, base, timeout)
            print(f'Story olarak da paylaşıldı: {entry["story"]}')
        except RuntimeError as e:
            report('Story paylaşılamadı', f'#{post["n"]}: {e}', 'warning')
    state['posted'][str(post['n'])] = entry
    state.get('failures', {}).pop(str(post['n']), None)
    if cfg.get('cleanup_after_post', True):
        cleanup(post)
    save('state.json', state)
    print(f"Paylaşıldı: #{post['n']} {post['kind']} ({post['date']} {post['time']}) → {entry.get('permalink') or media_id}")


if __name__ == '__main__':
    main()
