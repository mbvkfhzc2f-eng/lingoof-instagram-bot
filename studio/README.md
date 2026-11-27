# LINGOOF stüdyo

Instagram Reels, kapak ve carousel üretim hattı. Kod buradadır; Goof pozları, uygulama yazı tipi ve ekran görüntüleri uygulamanın
özel deposundan `setup_assets.py` ile alınır ve bu (herkese açık) depoya konmaz. Yapay zekâ görsel, video ya da ses modeli kullanılmaz:
sahneler Chrome'da HTML ile çizilir, sesler kodla sentezlenir.

## Kurulum

```bash
pip install --break-system-packages playwright numpy pillow   # tarayıcı indirme yok: /usr/bin/google-chrome kullanılır
python3 setup_assets.py /yol/lingoof-ios                      # goof/, fonts/*.ttf, shots/
```

ffmpeg'de `zscale` süzgeci olmalı (`ffmpeg -filters | grep zscale`).

## Akış

1. **Plan**: `plans/<ad>.py` içeriği ve açıklamaları tanımlar; çalıştırınca `plans/<ad>.json` (render girdisi) ve
   `plans/<ad>_posts.json` (gönderiler) çıkar.
2. **Üret**: `python3 render.py plans/<ad>.json [id ...]`. Önce `--no-video` ile yalnızca yerleşim denetimi ve kapaklar hızlıca çıkar.
3. **Bak**: `python3 preview.py plans/<ad>.json onizleme.jpg [id ...]` seçilen anların temas sayfasını yapar
   (kırmızı çizgiler Instagram arayüzünün kapladığı alanlar).
4. **Yerleştir**: `python3 integrate.py plans/<ad>_posts.json ..` dosyaları `media/v2/<id>/` altına kopyalar, `posts.json`'a ekler,
   yerini aldığı eski gönderiyi `hold` yapar. Kalite kapısından geçmeyen içerik eklenmez.

## Şablonlar

| Şablon | Ne | Zemin |
|---|---|---|
| `hata` | Hata Avı: 3 sn sayaç, yanlış kelime kırmızı dalgalı çizgiyle işaretlenir, cümle yerinde düzelir, Goof Türkçe açıklar | lacivert |
| `quiz` | 3 Saniye Testi: iki seçenek, doğru olan yeşerir, yanlış kapanır, Goof açıklar | lacivert |
| `pov` | POV sohbet: karşı taraf yazar, ders kitabı cevabı gelir, Goof utanır, native cevap gelir | lacivert |
| `nasil` | Türkçe ifade: kelimesi kelimesine çeviri çizilir, 3 doğal karşılık gelir | krem |
| `vs` | Türk usulü vs native: üç tur | lacivert |
| `urun` | Uygulamada böyle: alıştırmada yanlış seçim, Goof'un açıklaması, uygulamanın gerçek ekranı | krem |

Alanlar için `plans/aralik.py` örnek: her şablon için en az bir tam örnek var.

## Kalite kuralları (uretim_kalitesi.md §5'ten)

- **İlk kare tam bir kanca**: kanca yazısı, içerik ve Goof 0. karede görünür. İlk cevap ≤4 sn. Süre 8–12 sn, son kare ilk kareye döner.
- **Güvenli alan**: okunacak her şey ve Goof'un yüzü x 72–1008, y 270–1250 içinde; y 1150'nin altında sağ kenar ≤930 (beğen/yorum düğmeleri).
- **Yazı**: kanca 124, İngilizce cümle 64–72, Türkçe açıklama 56 px; açıklama ≤12 kelime; hiçbir yazı 32 px'ten küçük değil.
  Sığmazsa ölçek en çok %12 küçülür; yine sığmıyorsa metin kısaltılır.
- **Renk**: lacivert #1B1433 ya da krem #FAF8F3 zemin; Goof mor zemine konmaz. Doğru #6EE7B7/#047857, yanlış #FF8FA3/#BE123C.
- **Hareket**: Material eğrileri (giriş 9 kare, çıkış 6 kare, %6 taşma). Goof hep canlı: nefes, salınım, süzülme, tepki pozları;
  uzun okuma beklemelerinde ~2 sn'de bir ara vuruş (3 sn'den uzun olaysız aralık yok).
- **Okuma süresi**: Türkçe `0,4 + karakter/15` sn, İngilizce `0,5 + karakter/12` sn (şablonlar süreyi buna göre uzatır).
- **Ses**: her görsel vuruşta efekt. `reels.mp4` yalnızca efekt (Instagram'ın lisanslı müziği yayında eklenir, ses 70);
  `reels_muzikli.mp4` 120 BPM yedek fon müziğiyle −14 LUFS, tepe ≤ −1 dBTP, müzik açıklamadan önce 6 dB kısılır.
- **Kodlama**: H.264 High, BT.709 etiketli, 30 fps, B-kare yok, 48 kHz AAC, moov başta, düzenleme listesi yok.
- **Kapak**: 1080×1920, ≤5 kelimelik büyük başlık, ifadeli büyük Goof, içerikten bir parça.
- **Carousel**: 1080×1350, JPEG q93 4:4:4 sRGB; kapak ve son slayt lacivert, içerik krem; özet slaytı (kaydedilen) ve
  kaydet/gönder/yorum çağrısıyla biter. Sahte düğme yok.

`render.py` bunların hepsini ölçer ve `out/<id>/qc.json`'a yazar; `block` boş değilse içerik yayına girmez.

## İçerik kuralları

- İngilizce cümleler doğal ve doğru olmalı; emin olunmayan kalıp kullanılmaz. Türkçe açıklama kısa ve sohbet dilinde.
- Uygulama hakkında yalnızca App Store'daki iddialar: günde 5 dakika, A1'den C1'e, hatayı Goof Türkçe açıklar, iPhone'da ücretsiz.
- Açıklamada en çok 5 hashtag; ilk satır aranabilir anahtar kelimeyle başlar; yorum, kaydetme ya da gönderme çağrısıyla biter.
- Ürün cümlesi yaklaşık 3 gönderide 1; `urun` şablonu ayda 3–4 kez.
