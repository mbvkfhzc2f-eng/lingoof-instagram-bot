# LINGOOF Instagram botu

Plandaki (`posts.json`) reels ve carousel'leri Türkiye saatiyle, takvimdeki saatinde Instagram'ın resmi API'siyle paylaşır. GitHub'ın sunucularında ücretsiz çalışır, bilgisayarın açık olması gerekmez.

- Medya dosyaları `media/` klasöründe durur ve deponun GitHub Pages sayfasından yayınlanır; Instagram dosyayı oradan çeker. Paylaşılan gönderinin dosyaları depodan otomatik silinir.
- Aynı gönderi iki kez gitmez. Saati 6 saatten fazla geçen gönderi atlanır ve `state.json` içindeki `missed` listesine yazılır, sonra takvime yeniden yerleştirilir.
- Bir gönderi 3 kez hata verirse atlanır. Her hata GitHub'da kırmızı uyarı olarak görünür ve sana e-posta gelir.
- Token üç günde bir otomatik yenilenir.

## Kurulum (bir kerelik)

**1. Depo ve GitHub Pages.** Depo herkese açık olmalı. **Settings › Pages** altında *Source: Deploy from a branch*, *Branch: main* ve */ (root)* seç, **Save**'e bas. Birkaç dakika sonra `https://mbvkfhzc2f-eng.github.io/lingoof-instagram-bot/` açılır.

**2. Instagram hesabı.** Hesap profesyonel hesap (İşletme ya da İçerik Üreticisi) olmalı: Instagram › Ayarlar › Hesap türü ve araçları.

**3. Meta'da Instagram erişimi.** developers.facebook.com › My Apps › lingoof.app:
1. **Dashboard**'da *Manage messaging and content on Instagram* kullanım durumu yoksa **Use cases › Add use case** ile ekle. Meta bu uygulamaya eklemeye izin vermezse aynı kullanım durumuyla yeni bir uygulama aç.
2. Kullanım durumunu aç (**Customize**) › **API setup with Instagram login**.
3. **Permissions and features** altında `instagram_business_basic`, `instagram_business_content_publish` ve `instagram_business_manage_insights` izinlerini ekle.
4. **Generate access tokens** bölümünde **Add account**'a bas, açılan pencerede lingoof Instagram hesabıyla giriş yap ve izin ver.
5. Hesabın yanındaki **Generate token**'a bas. Çıkan uzun kod 60 gün geçerli bir token.

**4. Token'ı depoya ekle.** Deponun **Settings › Secrets and variables › Actions › New repository secret** sayfasında adı `IG_TOKEN` yap, değer olarak token'ı yapıştır. Token şifre gibidir, kimseyle paylaşma.

**5. Dene.** **Actions › Instagram paylaşımı › Run workflow**:
- `dry`: hesabı ve sıradaki gönderileri gösterir, hiçbir şey göndermez.
- `validate`: Instagram'da deneme dosyaları için hazırlık kaydı açar ama **yayınlamaz**. "DOĞRULANDI" yazıyorsa Instagram dosyaları kabul ediyor demektir.

**6. Geçmişi tara.** **Actions › Instagram geçmişini tara › Run workflow**. Hesaptaki tüm gönderiler `history.md` dosyasına yazılır; hangi hazır videonun daha önce paylaşıldığı buradan çıkarılır.

## İsteğe bağlı: GH_PAT
Meta yenilemede yeni bir token verirse botun onu kendisi kaydedebilmesi için GitHub › Settings › Developer settings › Fine-grained tokens yolundan yalnızca bu depoya yetkili, *Secrets: Read and write* izinli bir token oluştur ve `GH_PAT` adıyla secret olarak ekle.

## Durdurmak
**Actions › Instagram paylaşımı › ⋯ › Disable workflow**. Tekrar açınca plan kaldığı yerden devam eder; saati 6 saatten fazla geçenler atlanır.

## posts.json biçimi
```json
{"n": 1, "date": "2026-11-17", "time": "19:30", "kind": "reels", "title": "Hatayı Bul",
 "media": "2026-11-17/reels.mp4", "cover": "2026-11-17/kapak.jpg", "caption": "…"}
{"n": 2, "date": "2026-11-17", "time": "12:30", "kind": "carousel", "title": "YDS son hafta",
 "media": ["2026-11-17/01.jpg", "2026-11-17/02.jpg"], "caption": "…"}
```
Reels: tek MP4 (H.264, AAC), 9:16, 3–90 saniye. Carousel: 2–10 JPEG, 1080×1350. Açıklama en fazla 2.200 karakter ve 30 hashtag.
