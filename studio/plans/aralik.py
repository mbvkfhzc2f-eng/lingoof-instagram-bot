#!/usr/bin/env python3
"""28 Kasım – 31 Aralık 2026 içerik planı: 33 Reels + 15 carousel.
Çıktılar: plans/aralik.json (render.py girdisi) ve plans/aralik_posts.json (posts.json'a eklenecek gönderiler).
Her yeni gönderi, eski kuyruktaki aynı slotun yerine geçer (eski gönderi "hold" olur; müzik seçimi eskisinden alınır)."""
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

TAGS = {
    'hata': '#ingilizcehataları #ingilizcegramer #ingilizceöğren #lingoof',
    'gramer': '#ingilizcegramer #ingilizcetest #ingilizceöğren #lingoof',
    'nasil': '#ingilizcenasıldenir #günlükingilizce #ingilizceöğren #lingoof',
    'pov': '#ingilizcekonuşma #günlükingilizce #ingilizceöğren #lingoof',
    'yurtdisi': '#erasmus #yurtdışı #ingilizcekonuşma #günlükingilizce #lingoof',
    'komik': '#ingilizcekomik #günlükingilizce #ingilizceöğren #lingoof',
    'yalanci': '#ingilizcekelime #yalancıkelimeler #ingilizceöğren #lingoof',
    'yeniyil': '#yeniyıl #ingilizceöğren #günlükingilizce #lingoof',
    'urun': '#ingilizceöğren #ingilizceuygulama #günlükingilizce #lingoof',
}
P_HATA = "LINGOOF'ta hata yap, Goof nedenini Türkçe açıklasın. Ücretsiz indir, link profilde."
P_GENEL = "LINGOOF: A1'den C1'e İngilizce, Goof'la sesli prova. Ücretsiz indir, link profilde."
P_YURT = "Erasmus+, Work & Travel ve iş görüşmesi yolları LINGOOF'ta: önce hazırlan, sonra Goof'la prova yap. Link profilde."


def plain(s):
    return re.sub(r'<[^>]+>', '', s).replace('&nbsp;', ' ').strip()


def cap(lines, tags, product=None):
    body = '\n'.join(lines).strip()
    if product:
        body += '\n\n' + product
    return body + '\n\n' + TAGS[tags]


# ---------- Reels ----------
# slot: (eski n, tarih, saat, deneme)
R = []


def reel(slot, item, caption, title):
    R.append({'slot': slot, 'item': item, 'caption': caption, 'title': title})


reel((28, '2026-11-28', '19:30', 'SS_PERFORMANCE'), {
    'id': 'r01-pov-whatsup', 'template': 'pov',
    'hook': "POV: Erasmus'ta<br><em>ilk gün</em>", 'them_name': 'EMMA · EV ARKADAŞIN', 'them_avatar': 'char_emma', 'them': "What's up?",
    'wrong': "I'm fine, thank you. And you?", 'right': 'Not much! Just unpacking. You?',
    'explain': "<b>What's up?</b> nasılsın değil, <b>ne var ne yok</b> demek.", 'cover': "“What's up?”<br><em>deyince</em>"},
    cap(["“What's up?” diye sorulunca “I'm fine, thank you” deme 🙈",
         "What's up? hâl hatır sormaz, ne var ne yok der. Doğal cevap: Not much! You?",
         "", "Erasmus'a gidecek arkadaşına gönder, ilk gün rezil olmasın 😅"], 'yurtdisi'), "What's up cevabı")

reel((30, '2026-11-29', '19:30', None), {
    'id': 'r02-nasil-kolaygelsin', 'template': 'nasil',
    'hook': "‘Kolay gelsin’<br><em>nasıl denir?</em>", 'literal': 'Let it come easy!',
    'options': [{'en': "Don't work too hard!", 'tr': 'Çalışan bir arkadaşa'},
                {'en': 'Good luck with it!', 'tr': 'Yeni işe başlayana'},
                {'en': 'Hang in there!', 'tr': 'Zorlanan birine'}],
    'cover': "‘Kolay gelsin’<br><em>nasıl denir?</em>"},
    cap(["“Kolay gelsin” İngilizcede nasıl denir? “Let it come easy” değil 😅",
         "Duruma göre: Don't work too hard! · Good luck with it! · Hang in there!",
         "", "Kaydet, lazım olacak 📌 Hangi Türkçe ifadenin İngilizcesini merak ediyorsun? Yorumlara yaz, Goof cevaplasın."],
        'nasil', P_GENEL), 'Kolay gelsin')

reel((52, '2026-11-30', '19:30', None), {
    'id': 'r03-hata-agree', 'template': 'hata', 'hook': 'Bu cümlede<br><em>1 hata</em> var.',
    'wrong': 'I am agree with you.', 'fix': 'I agree with you.',
    'explain': '<b>agree</b> bir fiil: önüne <b>am/is/are</b> gelmez.', 'cover': '“I am agree”<br><em>deme</em>'},
    cap(["“I am agree” yanlış! İngilizcede doğrusu: I agree with you ✅",
         "agree zaten bir fiil; önüne am/is/are gelmez.",
         "", "Hatayı 3 saniyede buldun mu? Yorumlara yaz 👇 Hep “I am agree” diyen arkadaşına da gönder."], 'hata', P_HATA), 'I am agree')

reel((32, '2026-12-01', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r04-quiz-bored', 'template': 'quiz', 'hook': 'Sıkıldın.<br><em>Hangisini dersin?</em>',
    'options': ["I'm bored.", "I'm boring."], 'answer': 0,
    'explain': "<b>I'm boring</b> = ben sıkıcıyım. Sıkıldıysan: <b>I'm bored.</b>", 'cover': 'Sıkıldın.<br><em>Hangisi?</em>'},
    cap(["Sıkıldığında “I'm boring” deme, “ben sıkıcıyım” demiş olursun 😅",
         "Sıkıldıysan: I'm bored. Sıkıcı bir şey için: It's boring.",
         "", "3 saniyede bildin mi? A mı B mi, yorumlara yaz 👇"], 'gramer'), 'Bored boring')

reel((58, '2026-12-02', '19:30', None), {
    'id': 'r05-urun-evening', 'template': 'urun', 'hook': 'Yanlış yaz.<br><em>Goof açıklasın.</em>',
    'sentence': "I relax <span class='blank'></span> the evening.", 'options': ['in', 'at', 'on'], 'pick': 1, 'right': 0,
    'fix': "I relax <b style='color:var(--ok-l)'>in</b> the evening.",
    'explain': 'Saatte <b>at</b>, günde <b>on</b>, günün bölümünde <b>in</b>.', 'scene': 'scene_daily', 'cover': 'Yanlış yaz,<br><em>Goof açıklasın</em>'},
    cap(["LINGOOF'ta yanlış yapmak serbest: Goof nedenini hemen Türkçe açıklıyor 💜",
         "“at the evening” mı “in the evening” mı? Saatte at, günde on, günün bölümünde in.",
         "", "Hata yap. Düzelt. Devam et. A1'den C1'e, ilk dersler ücretsiz: link profilde 📲"], 'urun'), 'Uygulamada: in the evening')

reel((36, '2026-12-03', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r06-vs-veda', 'template': 'vs', 'hook': 'Türk usulü<br>vs <em>native</em>',
    'rounds': [{'ctx': '‘Görüşürüz’ derken', 'tr': 'We will see!', 'na': 'See you!'},
               {'ctx': '‘Kendine iyi bak’', 'tr': 'Look at yourself!', 'na': 'Take care!'},
               {'ctx': '‘Sağ ol’ derken', 'tr': 'Be alive!', 'na': 'Thanks!'}],
    'cover': 'Vedalaşırken<br><em>Türk usulü</em>'},
    cap(["“Görüşürüz” → We will see? 😅 Türk usulü vs native vedalaşma",
         "See you! · Take care! · Thanks!",
         "", "Hangisini sen de söylüyordun? Yorumlara yaz, arkadaşına gönder 👇"], 'komik'), 'Vedalaşma vs')

reel((72, '2026-12-04', '19:30', None), {
    'id': 'r07-pov-bill', 'template': 'pov', 'hook': "POV: Londra'da<br><em>hesap isteyeceksin</em>",
    'them_name': 'GARSON', 'them_avatar': 'char_role_c', 'them': 'Anything else?', 'wrong': 'No. Give me the account.', 'right': 'No, thanks. Could we get the bill?',
    'wrong_tag': 'KELİMESİ KELİMESİNE',
    'explain': 'Hesap <b>account</b> değil: <b>the bill</b> (İngiltere), <b>the check</b> (ABD).', 'cover': 'Hesabı<br><em>nasıl istersin?</em>'},
    cap(["Restoranda hesabı isterken “account” deme 🙈 Doğrusu: Could we get the bill?",
         "İngiltere'de the bill, Amerika'da the check.",
         "", "Yurt dışına gidecek arkadaşına gönder 📌"], 'yurtdisi', P_YURT), 'Hesap lütfen')

reel((40, '2026-12-05', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r08-hata-mistake', 'template': 'hata', 'hook': 'Hata yaparken<br><em>hata yapma.</em>',
    'wrong': 'I did a mistake.', 'fix': 'I made a mistake.',
    'explain': 'Hata yapmak: <b>make a mistake</b>. <b>do</b> değil.', 'cover': 'Hata yaparken<br><em>hata yapma</em>'},
    cap(["“I did a mistake” değil, “I made a mistake” 😅",
         "Hata, karar ve plan make ile kurulur: make a mistake, make a decision, make a plan.",
         "", "Bunu bilmeyen kaldıysa gönder 👇"], 'hata'), 'Make a mistake')

reel((46, '2026-12-06', '19:30', None), {
    'id': 'r09-nasil-gecmisolsun', 'template': 'nasil',
    'hook': "‘Geçmiş olsun’<br><em>nasıl denir?</em>", 'literal': 'Let it be past!',
    'options': [{'en': 'Get well soon!', 'tr': 'Hasta birine'},
                {'en': 'Hope you feel better!', 'tr': 'Mesajla yazarken'},
                {'en': 'Sorry to hear that!', 'tr': 'Kötü bir habere'}],
    'cover': "‘Geçmiş olsun’<br><em>nasıl denir?</em>"},
    cap(["“Geçmiş olsun” İngilizcede “Let it be past” değil 🤒",
         "Hasta birine: Get well soon! · Mesajda: Hope you feel better! · Kötü bir habere: Sorry to hear that!",
         "", "Kaydet 📌 Sıradaki ifadeyi yorumlarda sen seç."], 'nasil'), 'Geçmiş olsun')

reel((60, '2026-12-07', '19:30', None), {
    'id': 'r10-pov-alright', 'template': 'pov', 'hook': "POV: İngiliz<br><em>arkadaşın soruyor</em>",
    'them_name': 'ALEX · İNGİLİZ', 'them_avatar': 'char_alex', 'them': 'You alright?', 'wrong': "No, I'm not sick!", 'right': 'Yeah, good thanks! You?',
    'wrong_tag': 'YANLIŞ ANLADI',
    'explain': "İngiltere'de <b>You alright?</b> sadece selam, hasta mısın demek değil.", 'cover': '“You alright?”<br><em>deyince</em>'},
    cap(["İngiltere'de biri “You alright?” derse hasta olup olmadığını sormuyor 😄",
         "Bu sadece bir selam. Cevap: Yeah, good thanks! You?",
         "", "İngiltere'ye gidecek arkadaşına gönder 👇"], 'yurtdisi'), 'You alright')

reel((38, '2026-12-08', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r11-quiz-salt', 'template': 'quiz', 'hook': 'Hangisi<br><em>daha kibar?</em>', 'goof_size': 250,
    'options': ['Give me the salt.', 'Could you pass the salt?'], 'answer': 1,
    'explain': 'Emir sert duyulur. <b>Could you…?</b> kibar bir ricadır.', 'cover': 'Hangisi<br><em>kibar?</em>'},
    cap(["Sofrada “Give me the salt” dersen kaba duyulursun 🧂",
         "Kibar rica: Could you pass the salt?",
         "", "3 saniyede bildin mi? Cevabını yorumlara yaz 👇"], 'gramer', P_HATA), 'Kibar rica')

reel((74, '2026-12-09', '19:30', None), {
    'id': 'r12-hata-age', 'template': 'hata', 'hook': 'Yaşını<br><em>yanlış söyleme.</em>',
    'wrong': 'I have 25 years old.', 'fix': 'I am 25 years old.',
    'explain': "Yaş <b>be</b> ile söylenir: <b>I'm 25.</b>", 'cover': '“I have 25”<br><em>deme</em>'},
    cap(["Yaşını söylerken “I have 25 years” deme 🙅",
         "İngilizcede yaş be ile söylenir: I'm 25 ya da I'm 25 years old.",
         "", "Arkadaşını etiketle, o da öğrensin 👇"], 'hata'), 'Yaş söyleme')

reel((42, '2026-12-10', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r13-vs-sasirma', 'template': 'vs', 'hook': 'Şaşırınca<br><em>ne dersin?</em>',
    'rounds': [{'ctx': '‘Hadi ya!’ derken', 'tr': 'Come on ya!', 'na': 'No way!'},
               {'ctx': '‘Yok artık!’ derken', 'tr': 'No more!', 'na': "You're kidding!"},
               {'ctx': '‘Aynen!’ derken', 'tr': 'Same same!', 'na': 'Totally!'}],
    'cover': 'Şaşırınca<br><em>ne dersin?</em>'},
    cap(["“Hadi ya!” → Come on ya? 😂 Şaşırınca native nasıl der?",
         "No way! · You're kidding! · Totally!",
         "", "Sen en çok hangisini kullanıyorsun? Yorumlara yaz 👇"], 'komik'), 'Şaşırma vs')

reel((54, '2026-12-11', '19:30', None), {
    'id': 'r14-nasil-elinesaglik', 'template': 'nasil',
    'hook': "‘Eline sağlık’<br><em>nasıl denir?</em>", 'literal': 'Health to your hands!',
    'options': [{'en': 'This is delicious!', 'tr': 'Yemeği yapana'},
                {'en': "You're a great cook!", 'tr': 'İltifat ederken'},
                {'en': 'Thanks for dinner!', 'tr': 'Davet edene'}],
    'cover': "‘Eline sağlık’<br><em>nasıl denir?</em>"},
    cap(["“Eline sağlık” → Health to your hands? 😅 İngilizcede böyle bir kalıp yok.",
         "Yerine: This is delicious! · You're a great cook! · Thanks for dinner!",
         "", "Kaydet 📌 Yemeğe davet eden arkadaşına gönder."], 'nasil', P_GENEL), 'Eline sağlık')

reel((66, '2026-12-12', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r15-pov-blessyou', 'template': 'pov', 'hook': 'POV: Derste<br><em>biri hapşırdı</em>',
    'them_name': 'NINA · SINIF ARKADAŞIN', 'them_avatar': 'char_nina', 'them': 'Achoo!', 'wrong': 'Live long!', 'right': 'Bless you!',
    'wrong_tag': 'KELİMESİ KELİMESİNE',
    'explain': '‘Çok yaşa’nın karşılığı <b>Bless you!</b> Cevabı: <b>Thanks!</b>', 'cover': '‘Çok yaşa’<br><em>nasıl denir?</em>'},
    cap(["Biri hapşırınca “Live long!” deme 🤧 Doğrusu: Bless you!",
         "Sana söylenirse cevabı: Thanks!",
         "", "Bunu bilmeyen arkadaşına gönder 😅"], 'pov'), 'Bless you')

reel((64, '2026-12-13', '19:30', None), {
    'id': 'r16-urun-drinks', 'template': 'urun', 'hook': 'Hata yaptın mı?<br><em>Goof yakalar.</em>',
    'sentence': "She <span class='blank'></span> coffee every morning.", 'options': ['drink', 'drinks'], 'pick': 0, 'right': 1,
    'fix': "She <b style='color:var(--ok-l)'>drinks</b> coffee every morning.", 'verdict': 'Az kaldı!',
    'explain': '<b>he/she/it</b> ile fiil <b>-s</b> alır.', 'scene': 'scene_university',
    'cover': 'Hata yaptın mı?<br><em>Goof yakalar</em>'},
    cap(["“She drink” mi “she drinks” mi? LINGOOF'ta yanlış yapınca Goof hemen yakalıyor ☕",
         "he/she/it ile geniş zamanda fiile -s eklenir: She drinks coffee every morning.",
         "", "Her şık için Türkçe açıklama, Goof'la sesli prova. Ücretsiz indir, link profilde 📲"], 'urun'), 'Uygulamada: drinks')

reel((68, '2026-12-14', '19:30', None), {
    'id': 'r17-hata-light', 'template': 'hata', 'hook': 'Işığı<br><em>açamıyorsun.</em>',
    'wrong': 'Can you open the light?', 'fix': 'Can you turn on the light?',
    'explain': 'Işık ve cihazlarda <b>turn on / turn off</b> denir.', 'cover': '“Open the light”<br><em>deme</em>'},
    cap(["“Open the light” deme 💡 Doğrusu: Can you turn on the light?",
         "Işık, televizyon, telefon: turn on / turn off.",
         "", "Sen de “open the light” diyor muydun? Dürüst ol 👇"], 'hata', P_HATA), 'Turn on the light')

reel((70, '2026-12-15', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r18-quiz-latte', 'template': 'quiz', 'hook': 'Kafede hangisi<br><em>daha doğal?</em>',
    'options': ['I want a latte.', 'Can I get a latte?'], 'answer': 1,
    'explain': '<b>I want</b> talepkâr duyulur. Siparişte <b>Can I get…?</b> de.', 'cover': 'Kafede<br><em>hangisi?</em>'},
    cap(["Kafede “I want a latte” mı “Can I get a latte?” mı? ☕",
         "I want… talepkâr duyulur. Doğal sipariş: Can I get…?",
         "", "Cevabını yorumlara yaz, sonra izle 👇"], 'yurtdisi'), 'Kafede sipariş')

reel((56, '2026-12-16', '19:30', None), {
    'id': 'r19-nasil-afiyet', 'template': 'nasil',
    'hook': "‘Afiyet olsun’<br><em>nasıl denir?</em>", 'literal': 'Be healthy!',
    'options': [{'en': 'Enjoy your meal!', 'tr': 'Garson ya da ev sahibi'},
                {'en': 'Enjoy!', 'tr': 'Kısa ve samimi'},
                {'en': 'Dig in!', 'tr': 'Yemeğe başlarken'}],
    'cover': "‘Afiyet olsun’<br><em>nasıl denir?</em>"},
    cap(["“Afiyet olsun” → Be healthy? 🍝 İngilizcede böyle denir:",
         "Enjoy your meal! · Enjoy! · Dig in!",
         "", "Kaydet 📌 Bir sonraki ifadeyi yorumlarda sen iste."], 'nasil'), 'Afiyet olsun')

reel((34, '2026-12-17', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r20-hata-explain', 'template': 'hata', 'hook': '3 saniyede<br><em>hatayı bul.</em>',
    'wrong': 'Can you explain me this?', 'fix': 'Can you explain this to me?',
    'explain': '<b>explain</b> kişiyi <b>to</b> ile alır: <b>explain it to me</b>.', 'cover': '“Explain me”<br><em>deme</em>'},
    cap(["“Can you explain me this?” yanlış 🙅 Doğrusu: Can you explain this to me?",
         "explain kişiyi to ile alır: explain it to me.",
         "", "3 saniyede buldun mu? Yorumlara yaz 👇"], 'hata'), 'Explain to me')

reel((50, '2026-12-18', '19:30', None), {
    'id': 'r21-pov-meeting', 'template': 'pov', 'hook': 'POV: Toplantıda<br><em>anlamadın</em>',
    'them_name': 'MÜDÜRÜN', 'them_avatar': 'char_role_a', 'them': 'Does that make sense?', 'wrong': 'Repeat please!', 'right': 'Sorry, could you go over that again?',
    'wrong_tag': 'KABA DUYULUR',
    'explain': '<b>Repeat!</b> emir gibi duyulur. Kibar rica: <b>Could you…?</b>', 'cover': 'Anlamayınca<br><em>ne dersin?</em>'},
    cap(["Toplantıda anlamadın: “Repeat please!” deme 😬",
         "Kibar ve doğal: Sorry, could you go over that again?",
         "", "İş yerinde İngilizce konuşan arkadaşına gönder 📌"], 'pov', P_GENEL), 'Toplantıda anlamadın')

reel((48, '2026-12-19', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r22-vs-telefon', 'template': 'vs', 'hook': 'Telefonda<br><em>Türk usulü</em>',
    'rounds': [{'ctx': 'Telefonu açınca', 'tr': 'Yes, please?', 'na': 'Hello?'},
               {'ctx': 'Kim aradı?', 'tr': 'Who are you?', 'na': "Who's calling, please?"},
               {'ctx': 'Kapatırken', 'tr': 'Okay okay, bye bye bye!', 'na': 'Talk soon. Bye!'}],
    'cover': 'Telefonda<br><em>Türk usulü</em>'},
    cap(["Telefonda Türk usulü vs native 📞 Kapatırken 5 kere bye demek bizden 😂",
         "Hello? · Who's calling, please? · Talk soon. Bye!",
         "", "Hangisi sensin? Yorumlara yaz 👇"], 'komik'), 'Telefon vs')

reel((78, '2026-12-20', '19:30', None), {
    'id': 'r23-nasil-kusura', 'template': 'nasil',
    'hook': "‘Kusura bakma’<br><em>nasıl denir?</em>", 'literal': "Don't look at the fault!",
    'options': [{'en': 'Sorry about that!', 'tr': 'Küçük bir aksilikte'},
                {'en': 'My bad!', 'tr': 'Arkadaşlar arasında'},
                {'en': 'I apologize.', 'tr': 'Resmî ortamda'}],
    'cover': "‘Kusura bakma’<br><em>nasıl denir?</em>"},
    cap(["“Kusura bakma” → Don't look at the fault? 😅",
         "Duruma göre: Sorry about that! · My bad! · I apologize.",
         "", "Kaydet 📌 Hangi ifadeyi merak ediyorsun? Yorumlara yaz."], 'nasil', P_GENEL), 'Kusura bakma')

reel((86, '2026-12-21', '19:30', None), {
    'id': 'r24-hata-works', 'template': 'hata', 'hook': 'Bu hatayı<br><em>herkes yapar.</em>',
    'wrong': 'She work in a bank.', 'fix': 'She works in a bank.',
    'explain': '<b>he/she/it</b> ile geniş zamanda fiile <b>-s</b> gelir.', 'cover': 'She work?<br><em>She works!</em>'},
    cap(["“She work in a bank” mı “She works in a bank” mı? 🏦",
         "he/she/it ile geniş zamanda fiile -s eklenir: she works, he lives, it rains.",
         "", "Bu hatayı hâlâ yapan arkadaşına gönder 😅"], 'hata', P_HATA), 'She works')

reel((62, '2026-12-22', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r25-quiz-discuss', 'template': 'quiz', 'hook': 'Hangisi<br><em>doğru?</em>',
    'options': ['We discussed it.', 'We discussed about it.'], 'answer': 0,
    'explain': '<b>discuss</b> ile <b>about</b> kullanılmaz: <b>discuss the plan</b>.', 'cover': 'Discuss<br><em>about?</em>'},
    cap(["“We discussed about it” yanlış 🙅 Doğrusu: We discussed it.",
         "discuss zaten “hakkında konuşmak” demek; about almaz. (talk about ise doğru!)",
         "", "A mı B mi? Yorumlara yaz 👇"], 'gramer'), 'Discuss about')

reel((92, '2026-12-23', '19:30', None), {
    'id': 'r26-pov-exam', 'template': 'pov', 'hook': 'POV: Arkadaşın<br><em>sınavı geçti</em>',
    'them_name': 'SOFIA · ERASMUS', 'them_avatar': 'char_sofia', 'them': 'I passed my exam!!', 'wrong': 'Congratulations. You are very successful.',
    'right': 'No way! Well done, you!', 'wrong_tag': 'ÇOK RESMİ',
    'explain': '<b>You are very successful</b> çok resmî. Sohbette: <b>Well done!</b>', 'cover': 'Tebrik<br><em>böyle edilir</em>'},
    cap(["Arkadaşın sınavı geçti: “You are very successful” deme, çok resmî duyulur 🎉",
         "Sohbette: No way! Well done, you! · Congrats!",
         "", "Sınavdan çıkan arkadaşına gönder 👇"], 'pov'), 'Tebrik')

reel((80, '2026-12-24', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r27-hata-people', 'template': 'hata', 'hook': 'Bu hatayı<br><em>fark et.</em>', 'goof_size': 360,
    'wrong': 'People is very friendly here.', 'fix': 'People are very friendly here.',
    'explain': '<b>people</b> çoğuldur: <b>people are</b>, <b>is</b> değil.', 'cover': '“People is”<br><em>deme</em>'},
    cap(["“People is” değil, “people are” 🙌",
         "people zaten çoğul: People are very friendly here.",
         "", "Fark ettin mi? Yorumlara yaz 👇"], 'hata'), 'People are')

reel((82, '2026-12-25', '19:30', None), {
    'id': 'r28-nasil-hayirli', 'template': 'nasil',
    'hook': "‘Hayırlı olsun’<br><em>nasıl denir?</em>", 'literal': 'Let it be charity!',
    'options': [{'en': 'Congrats!', 'tr': 'Yeni ev, iş, araba'},
                {'en': 'Enjoy your new place!', 'tr': 'Yeni eve taşınana'},
                {'en': 'All the best!', 'tr': 'Yeni bir başlangıca'}],
    'cover': "‘Hayırlı olsun’<br><em>nasıl denir?</em>"},
    cap(["“Hayırlı olsun” → Let it be charity? 😂",
         "Yerine: Congrats! · Enjoy your new place! · All the best!",
         "", "Kaydet 📌 Yeni eve taşınan arkadaşına gönder."], 'nasil', P_GENEL), 'Hayırlı olsun')

reel((84, '2026-12-26', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r29-vs-nezaket', 'template': 'vs', 'hook': 'Nezaket<br><em>Türk usulü</em>',
    'rounds': [{'ctx': '‘Rica ederim’ derken', 'tr': 'I request!', 'na': "You're welcome!"},
               {'ctx': '‘Bol şans’ derken', 'tr': 'Plenty luck!', 'na': 'Good luck!'},
               {'ctx': '‘Boş ver’ derken', 'tr': 'Give empty!', 'na': 'Never mind!'}],
    'cover': '‘Rica ederim’<br><em>≠ I request</em>'},
    cap(["“Rica ederim” → I request? 😂 Türk usulü vs native nezaket",
         "You're welcome! · Good luck! · Never mind!",
         "", "En çok hangisi güldürdü? Yorumlara yaz 👇"], 'komik'), 'Nezaket vs')

reel((44, '2026-12-27', '19:30', None), {
    'id': 'r30-urun-waiting', 'template': 'urun', 'hook': 'Hata yap.<br><em>Goof düzeltsin.</em>',
    'sentence': "I'm waiting <span class='blank'></span> the bus.", 'options': ['to', 'for', 'at'], 'pick': 0, 'right': 1,
    'fix': "I'm waiting <b style='color:var(--ok-l)'>for</b> the bus.",
    'explain': 'Birini ya da bir şeyi beklerken <b>wait for</b> denir.', 'scene': 'scene_travel',
    'features': ['Her hata Türkçe açıklanır', "Goof'la sesli prova", 'Seyahat ve yurt dışı yolları'],
    'cover': 'Hata yap,<br><em>Goof düzeltsin</em>'},
    cap(["“I'm waiting the bus” mı “waiting for the bus” mı? 🚌 LINGOOF'ta Goof farkı hemen açıklıyor.",
         "Beklerken wait for: I'm waiting for you.",
         "", "Seyahat, Erasmus+ ve yurt dışında yaşam yolları LINGOOF'ta. Ücretsiz indir, link profilde 📲"], 'urun'),
    'Uygulamada: waiting for')

reel((88, '2026-12-28', '19:30', None), {
    'id': 'r31-hata-depends', 'template': 'hata', 'hook': 'Sen de böyle<br><em>diyor musun?</em>',
    'wrong': 'It depends of the weather.', 'fix': 'It depends on the weather.',
    'explain': '<b>depend</b> ile <b>on</b> kullanılır: <b>It depends on…</b>', 'cover': '“Depends of”<br><em>deme</em>'},
    cap(["“It depends of” değil, “It depends on” ⛅",
         "depend her zaman on ile kullanılır: It depends on you.",
         "", "Sen de böyle diyor muydun? Yorumlara yaz 👇"], 'hata', P_HATA), 'Depends on')

reel((76, '2026-12-29', '20:30', 'SS_PERFORMANCE'), {
    'id': 'r32-pov-bakarim', 'template': 'pov', 'hook': 'POV: Partiye<br><em>çağrıldın</em>',
    'them_name': 'LEO · EV ARKADAŞIN', 'them_avatar': 'char_leo', 'them': 'Are you coming tonight?', 'wrong': 'Maybe. I will look.',
    'right': "Maybe! I'll see how I feel.", 'wrong_tag': 'KELİMESİ KELİMESİNE',
    'explain': "‘Bakarım’ <b>I will look</b> değil: <b>I'll see</b> ya da <b>maybe</b>.", 'cover': '‘Bakarım’<br><em>nasıl denir?</em>'},
    cap(["“Bakarım” → I will look? 👀 Doğrusu: I'll see!",
         "Partiye gelecek misin? Maybe! I'll see how I feel.",
         "", "Hep “bakarım” deyip gelmeyen arkadaşına gönder 😂"], 'pov'), 'Bakarım')

reel((94, '2026-12-31', '19:30', None), {
    'id': 'r33-nasil-iyiseneler', 'template': 'nasil',
    'hook': "‘İyi seneler’<br><em>nasıl denir?</em>", 'literal': 'Good years!',
    'options': [{'en': 'Happy New Year!', 'tr': 'Gece yarısı'},
                {'en': 'All the best in 2027!', 'tr': 'Mesajla yazarken'},
                {'en': "Here's to a great year!", 'tr': 'Kadeh kaldırırken'}],
    'cta': 'Kaydet, bu gece lazım', 'cover': "‘İyi seneler’<br><em>nasıl denir?</em>"},
    cap(["“İyi seneler” → Good years? 🎆 Yılbaşı gecesi İngilizce böyle denir:",
         "Happy New Year! · All the best in 2027! · Here's to a great year!",
         "", "Mutlu yıllar 💜 2027'de İngilizceyle ne yapmak istiyorsun? Yorumlara yaz."], 'yeniyil', P_GENEL), 'İyi seneler')

# ---------- Carousel ----------
C = []


def car(slot, item, caption, title, alts=None):
    C.append({'slot': slot, 'item': item, 'caption': caption, 'title': title})


def items(*rows):
    out = []
    for r in rows:
        d = {'when': r[0], 'en': r[1], 'tr': r[2]}
        if len(r) > 3 and r[3]:
            d['reply' if r[3].startswith('R:') else 'tip'] = r[3][2:].strip()
        out.append(d)
    return out


car((27, '2026-11-28', '12:30', None), {
    'id': 'c01-inonat', 'kicker': 'ZAMAN EDATLARI', 'hook': 'in, on, at:<br><em>bir kere öğren,</em> bitsin',
    'promise': 'Saat, gün, ay… Hangisi nerede? 5 örnekte.',
    'items': items(('SAATTE: AT', 'The class starts at 9.', "Ders 9'da başlıyor.", 'T: Saatler ve <b>night</b>: <b>at 9</b>, <b>at night</b>.'),
                   ('GÜNDE: ON', 'See you on Monday!', 'Pazartesi görüşürüz!', 'T: Günler ve tarihler: <b>on Monday</b>, <b>on 5 May</b>.'),
                   ('AYDA, YILDA: IN', 'I was born in 1999.', "1999'da doğdum.", 'T: Ay, yıl, mevsim: <b>in May</b>, <b>in 2027</b>, <b>in winter</b>.'),
                   ('GÜNÜN BÖLÜMÜ: IN', 'I study in the evening.', 'Akşamları ders çalışırım.', 'T: <b>in the morning</b>, <b>in the evening</b>; ama <b>at night</b>!'),
                   ('ÖZEL GÜN: ON', "What do you do on New Year's Eve?", 'Yılbaşı gecesi ne yapıyorsun?', 'T: Belirli bir gün: <b>on my birthday</b>.')),
    'quiz': {'q': 'Doğru olanı seç:', 'options': ['at the evening', 'in the evening', 'on the evening'], 'answer': 1,
             'why': 'Günün bölümlerinde <b>in</b>: <b>in the evening</b>. İstisna: <b>at night</b>.'},
    'recap_title': 'in · on · at özeti', 'save': 'Kaydet:<br><em>bir daha karıştırma.</em>',
    'send': "Hep ‘at the morning’ diyen arkadaşına gönder.", 'ask': 'En çok hangisini karıştırıyorsun?'},
    cap(["in, on, at: zaman edatlarını bir kere öğren, bitsin ⏰",
         "Saatte at, günde on, ay ve yılda in. Günün bölümlerinde in, ama at night!",
         "", "Kaydet 📌 Sonda mini test var, cevabını yorumlara yaz."], 'gramer', P_HATA), 'in on at zaman')

car((29, '2026-12-01', '12:30', None), {
    'id': 'c02-erasmus', 'kicker': 'ERASMUS · İLK HAFTA', 'hook': "Erasmus'ta ilk hafta:<br><em>bu 5 cümle</em> seni kurtarır",
    'promise': 'Kampüste, yurtta ve kafede ilk günden lazım olacak.',
    'items': items(('KAMPÜSTE', 'Where do I get my student card?', 'Öğrenci kartımı nereden alırım?', 'R: At the international office!'),
                   ('DERSTE, KAFEDE', 'Is this seat taken?', 'Bu koltuk boş mu?', 'R: No, go ahead!'),
                   ('ANLAMADIĞINDA', 'Sorry, could you say that again?', 'Pardon, tekrar söyler misin?', 'T: <b>What?</b> kaba kaçabilir. <b>Sorry?</b> de olur.'),
                   ('YURTTA', 'How does the laundry work here?', 'Çamaşırhane nasıl çalışıyor?', 'R: You need tokens from reception.'),
                   ('ARKADAŞ EDİNİRKEN', 'Wanna grab a coffee later?', 'Sonra kahve içelim mi?', 'R: Sounds good! Around five?')),
    'quiz': {'q': 'Hocayı anlamadın.<br>Hangisini dersin?', 'options': ['What?', 'Sorry, could you say that again?', 'Repeat!'], 'answer': 1,
             'why': '<b>What?</b> ve <b>Repeat!</b> kaba duyulur. Kibar ve doğal olan bu.'},
    'save': 'Kaydet:<br><em>ilk hafta lazım.</em>', 'send': "Erasmus'a gidecek arkadaşına gönder.", 'ask': 'İlk hafta seni en çok ne zorladı?'},
    cap(["Erasmus'a ya da yurt dışına gidiyorsan kaydet 📌 İlk hafta bu 5 cümle seni kurtarır.",
         "Kampüs, ders, yurt ve yeni arkadaşlar için hazır kalıplar; sonda mini test var.",
         "", "Erasmus'a gidecek arkadaşına gönder 💜"], 'yurtdisi', P_YURT), 'Erasmus ilk hafta')

car((35, '2026-12-03', '12:30', None), {
    'id': 'c03-havalimani', 'kicker': 'HAVALİMANINDA', 'hook': 'Havalimanında<br><em>bu 5 cümle</em> yeter',
    'promise': "Check-in'den bagaja kadar, gerçek cümleler.",
    'items': items(('CHECK-IN', 'Is this the line for check-in?', 'Check-in sırası bu mu?', 'R: Yes, it is. Next, please!'),
                   ('KOLTUK', 'Could I have a window seat?', 'Cam kenarı alabilir miyim?', 'R: Sure, 14A is free.'),
                   ('BAGAJ', 'How many bags can I check in?', 'Kaç bavul verebilirim?', 'R: One bag, up to 23 kilos.'),
                   ('KAPI', 'Which gate is my flight?', 'Uçağım hangi kapıdan?', 'T: Biniş kapısı <b>gate</b>; <b>door</b> değil.'),
                   ('BAGAJ GELMEDİ', "My bag didn't arrive.", 'Bavulum gelmedi.', "R: Let's fill in a form.")),
    'quiz': {'q': 'Uçağa biniş kapısı:', 'options': ['door', 'gate', 'port'], 'answer': 1,
             'why': 'Havalimanında biniş kapısına <b>gate</b> denir.'},
    'save': 'Kaydet:<br><em>tatilde lazım.</em>', 'send': 'Yurt dışına uçacak arkadaşına gönder.', 'ask': 'Havalimanında en son neyi sordun?'},
    cap(["Havalimanında İngilizce: check-in'den kayıp bavula 5 cümle ✈️",
         "Window seat, gate, check in… Hepsi cevaplarıyla.",
         "", "Kaydet 📌 Yurt dışına uçacak arkadaşına gönder."], 'yurtdisi'), 'Havalimanı')

car((31, '2026-12-05', '12:30', None), {
    'id': 'c04-yalanci', 'kicker': 'YALANCI KELİMELER', 'hook': 'Bu 5 kelime<br><em>sandığın</em> anlamda değil',
    'promise': 'Türkçeye benziyor ama anlamı başka.',
    'items': items(('SYMPATHETIC', 'She was very sympathetic.', 'Çok anlayışlıydı. (Sempatik değil!)', 'T: Sempatik için: <b>likeable</b>, <b>nice</b>.'),
                   ('AGENDA', "What's on the agenda?", 'Gündemde ne var? (Ajanda değil!)', 'T: Ajanda için: <b>planner</b>.'),
                   ('ACTUALLY', "Actually, I'm from Izmir.", 'Aslında İzmirliyim. (Aktüel değil!)', 'T: Şu anda için: <b>currently</b>.'),
                   ('SENSIBLE', "That's a sensible plan.", 'Mantıklı bir plan. (Hassas değil!)', 'T: Hassas için: <b>sensitive</b>.'),
                   ('CONDITION', 'The car is in good condition.', 'Araba iyi durumda. (Kondisyon değil!)', 'T: Kondisyon için: <b>fitness</b>.')),
    'quiz': {'q': 'Sempatik birini anlatıyorsun:', 'options': ["He's sympathetic.", "He's likeable.", "He's sensible."], 'answer': 1,
             'why': '<b>sympathetic</b> anlayışlı demek. Sempatik için <b>likeable</b>.'},
    'save': 'Kaydet:<br><em>tuzağa düşme.</em>', 'send': "‘Sympathetic’ diyen arkadaşına gönder.", 'ask': 'Başka hangi yalancı kelimeyi biliyorsun?'},
    cap(["Yalancı kelimeler: sympathetic sempatik değil, agenda ajanda değil 🤥",
         "Türkçeye benzeyen ama bambaşka anlama gelen 5 kelime.",
         "", "Kaydet 📌 Başka hangi yalancı kelimeyi biliyorsun? Yorumlara yaz."], 'yalanci'), 'Yalancı kelimeler')

car((39, '2026-12-08', '12:30', None), {
    'id': 'c05-smalltalk', 'kicker': 'SMALL TALK', 'hook': 'Sohbeti<br><em>tıkanmadan</em> sürdür',
    'promise': '5 soru ve doğal cevapları.',
    'items': items(('SELAMLAŞIRKEN', "How's it going?", 'Nasıl gidiyor?', 'R: Not bad! You?'),
                   ('HAFTA SONU', 'Any plans for the weekend?', 'Hafta sonu için plan var mı?', 'R: Nothing much, just relaxing.'),
                   ('İŞ, OKUL', 'What do you do?', 'Ne iş yapıyorsun?', "R: I'm a student. I study law."),
                   ('MEMLEKET', 'Where are you from?', 'Nerelisin?', "R: I'm from Türkiye, from Bursa."),
                   ('KAPATIRKEN', 'It was nice chatting with you!', 'Seninle sohbet etmek güzeldi!', 'R: You too! See you around.')),
    'quiz': {'q': '‘What do you do?’ ne sorar?', 'options': ['Şu an ne yapıyorsun?', 'Ne iş yapıyorsun?', 'Ne yapmak istersin?'], 'answer': 1,
             'why': '<b>What do you do?</b> mesleği sorar. Şu an için: <b>What are you doing?</b>'},
    'save': 'Kaydet:<br><em>sohbette lazım.</em>', 'send': 'Yabancı arkadaşı olan birine gönder.', 'ask': "Small talk'ta en çok nerede tıkanıyorsun?"},
    cap(["Small talk'ta tıkanma: 5 soru ve doğal cevapları 💬",
         "How's it going? · Any plans for the weekend? · What do you do?",
         "", "Kaydet 📌 Sonda mini test var: What do you do? ne sorar?"], 'pov', P_GENEL), 'Small talk')

car((41, '2026-12-10', '12:30', None), {
    'id': 'c06-otel', 'kicker': 'OTELDE', 'hook': 'Otelde<br><em>bu 5 cümle</em> yeter',
    'promise': 'Girişten çıkışa, kibar ve doğal.',
    'items': items(('GİRİŞ', 'I have a reservation under Yılmaz.', 'Yılmaz adına rezervasyonum var.', 'R: Welcome! Can I see your ID?'),
                   ('KAHVALTI', 'What time is breakfast?', 'Kahvaltı saat kaçta?', 'R: From 7 to 10, on the ground floor.'),
                   ('WI-FI', "What's the Wi-Fi password?", 'Wi-Fi şifresi ne?', "R: It's on your key card."),
                   ('SORUN', "The air conditioning isn't working.", 'Klima çalışmıyor.', "R: Sorry! We'll send someone up."),
                   ('ÇIKIŞ', 'Could I leave my bags here?', 'Çantalarımı burada bırakabilir miyim?', 'R: Of course, until 6 pm.')),
    'quiz': {'q': 'Otelden ayrılırken:', 'options': ['I want to go out.', "I'd like to check out.", 'I am leaving the hotel now.'], 'answer': 1,
             'why': 'Otelden çıkış yapmak <b>check out</b>. Giriş: <b>check in</b>.'},
    'save': 'Kaydet:<br><em>tatilde lazım.</em>', 'send': 'Tatile çıkacak arkadaşına gönder.', 'ask': 'Otelde en son ne istedin?'},
    cap(["Otelde İngilizce: girişten çıkışa 5 cümle 🏨",
         "Rezervasyon, kahvaltı, Wi-Fi, arıza ve çıkış; hepsi cevaplarıyla.",
         "", "Kaydet 📌 Tatile çıkacak arkadaşına gönder."], 'yurtdisi', P_YURT), 'Otel')

car((43, '2026-12-12', '12:30', None), {
    'id': 'c07-phrasal', 'kicker': 'PHRASAL VERBS', 'hook': 'Her gün duyacağın<br><em>5 phrasal verb</em>',
    'promise': 'Dizilerde, işte, sohbette.',
    'items': items(('FIGURE OUT', "I can't figure it out.", 'Bir türlü çözemiyorum.', 'T: <b>figure out</b> = anlamak, çözmek.'),
                   ('RUN OUT OF', 'We ran out of milk.', 'Sütümüz bitti.', 'T: <b>run out of</b> = bir şey bitmek.'),
                   ('LOOK FORWARD TO', "I'm looking forward to it!", 'Dört gözle bekliyorum!', 'T: Ardından <b>-ing</b>: <b>looking forward to seeing you</b>.'),
                   ('PUT OFF', "Don't put it off!", 'Erteleme!', 'T: <b>put off</b> = ertelemek.'),
                   ('CATCH UP', "Let's catch up soon!", 'Yakında görüşüp hasret giderelim!', 'T: <b>catch up</b> = hasret gidermek.')),
    'quiz': {'q': '‘Benzinimiz bitti’:', 'options': ['We ran out of gas.', 'We finished of gas.', 'We put off gas.'], 'answer': 0,
             'why': 'Bir şey bitince <b>run out of</b>: <b>We ran out of gas.</b>'},
    'save': 'Kaydet:<br><em>dizide yakala.</em>', 'send': 'Dizi izleyen arkadaşına gönder.', 'ask': 'En çok hangisini duyuyorsun?'},
    cap(["Her gün duyacağın 5 phrasal verb: figure out, run out of, look forward to, put off, catch up 🎬",
         "Hepsi örnek cümleyle, sonda mini test.",
         "", "Kaydet 📌 Dizi izleyen arkadaşına gönder."], 'gramer'), 'Phrasal verbs')

car((53, '2026-12-15', '12:30', None), {
    'id': 'c08-hatalar', 'kicker': 'EN SIK 5 HATA', 'hook': 'Türklerin<br><em>en sık</em> yaptığı<br>5 hata',
    'promise': 'Doğrusu ve kısa nedeni, tek yerde.',
    'items': items(('AGREE', 'I agree with you.', '“I am agree” değil.', 'T: <b>agree</b> fiil; önüne <b>am</b> gelmez.'),
                   ('YAŞ', "I'm 25 years old.", '“I have 25 years” değil.', 'T: Yaş <b>be</b> ile söylenir.'),
                   ('HATA YAPMAK', 'I made a mistake.', '“I did a mistake” değil.', 'T: Hata: <b>make a mistake</b>.'),
                   ('IŞIK', 'Can you turn on the light?', '“Open the light” değil.', 'T: Cihazlar: <b>turn on / off</b>.'),
                   ('BEKLEMEK', "I'm waiting for you.", "“I'm waiting you” değil.", 'T: Beklerken <b>wait for</b>.')),
    'quiz': {'q': 'Hangisi doğru?', 'options': ['I am agree.', 'I agree.', 'I am agreeing.'], 'answer': 1,
             'why': '<b>agree</b> zaten fiil: <b>I agree.</b>'},
    'save': 'Kaydet:<br><em>bir daha yapma.</em>', 'send': 'Bu hataları yapan arkadaşına gönder.', 'ask': 'Sen hangisini yapıyordun?'},
    cap(["Türklerin en sık yaptığı 5 İngilizce hata ve doğruları ✅",
         "I am agree · I have 25 years · I did a mistake · open the light · waiting you",
         "", "Kaydet 📌 Sen hangisini yapıyordun? Yorumlara yaz."], 'hata', P_HATA), 'En sık 5 hata')

car((57, '2026-12-17', '12:30', None), {
    'id': 'c09-telefon', 'kicker': 'TELEFONDA', 'hook': 'Telefonda<br><em>panik yapma:</em><br>5 kalıp',
    'promise': 'Arayan da sen ol, aranan da.',
    'items': items(('TANITIRKEN', 'Hi, this is Ece.', 'Merhaba, ben Ece.', 'T: Telefonda <b>I am Ece</b> değil, <b>this is Ece</b>.'),
                   ('BİRİNİ İSTERKEN', 'Could I speak to Mark, please?', "Mark'la görüşebilir miyim?", 'R: Speaking!'),
                   ('SES KESİLİNCE', "Sorry, you're breaking up.", 'Pardon, sesin kesiliyor.', 'R: Let me call you back.'),
                   ('MEŞGULKEN', 'Can I call you back?', 'Seni sonra arayabilir miyim?', 'R: Sure, no problem.'),
                   ('ADRES', 'Could you text me the address?', 'Adresi mesaj atar mısın?', 'R: Sending it now!')),
    'quiz': {'q': "Telefonda ‘Is this Ece?’ diye sordular:", 'options': ['Yes, I am Ece.', 'Speaking!', 'Ece is me.'], 'answer': 1,
             'why': "Telefonda ‘benim’ demenin doğal yolu: <b>Speaking!</b>"},
    'save': 'Kaydet:<br><em>telefonda lazım.</em>', 'send': 'Telefonda konuşmaktan çekinen arkadaşına gönder.', 'ask': 'Telefonda İngilizce konuşmak seni geriyor mu?'},
    cap(["Telefonda İngilizce: panik yapma, bu 5 kalıp yeter 📞",
         "this is Ece · Speaking! · you're breaking up · call you back",
         "", "Kaydet 📌 Telefonda konuşmaktan çekinen arkadaşına gönder."], 'yurtdisi', P_GENEL), 'Telefon')

car((59, '2026-12-19', '12:30', None), {
    'id': 'c10-doktor', 'kicker': 'DOKTORDA', 'hook': 'Yurt dışında<br><em>hastalanırsan</em><br>5 cümle',
    'promise': 'Belirtini anlat, ilacını sor.',
    'items': items(('ATEŞ', "I've had a fever since yesterday.", 'Dünden beri ateşim var.', 'T: Süreden bahsederken <b>since yesterday</b>.'),
                   ('BOĞAZ', 'My throat hurts.', 'Boğazım ağrıyor.', 'R: Let me take a look.'),
                   ('ALERJİ', "I'm allergic to penicillin.", 'Penisiline alerjim var.', 'T: <b>allergic to</b> + madde.'),
                   ('REÇETE', 'Do I need a prescription?', 'Reçete gerekiyor mu?', "R: Yes, I'll write you one."),
                   ('İLAÇ', 'How often should I take it?', 'Ne sıklıkla almalıyım?', 'R: Twice a day, after meals.')),
    'quiz': {'q': "‘Başım ağrıyor’:", 'options': ['I have a headache.', 'My head is aching me.', 'I have head pain.'], 'answer': 0,
             'why': 'Doğal olan: <b>I have a headache.</b>'},
    'save': 'Kaydet:<br><em>umarım lazım olmaz.</em>', 'send': 'Yurt dışında yaşayan arkadaşına gönder.', 'ask': 'Yurt dışında hiç doktora gittin mi?'},
    cap(["Yurt dışında hastalanırsan doktorda İngilizce: 5 cümle 🩺",
         "Ateş, boğaz ağrısı, alerji, reçete ve ilaç; cevaplarıyla.",
         "", "Kaydet 📌 Yurt dışında yaşayan arkadaşına gönder."], 'yurtdisi'), 'Doktor')

car((69, '2026-12-22', '12:30', None), {
    'id': 'c11-ulasim', 'kicker': 'ULAŞIM', 'hook': 'Otobüste, trende:<br><em>5 kurtarıcı cümle</em>',
    'promise': 'Bilet al, yolunu sor, aktarma yap.',
    'items': items(('OTOBÜS', 'Does this bus go to the city centre?', 'Bu otobüs şehir merkezine gidiyor mu?', "R: Yes, it's the fourth stop."),
                   ('BİLET', 'A return ticket to Oxford, please.', "Oxford'a gidiş-dönüş bilet lütfen.", 'T: Gidiş-dönüş: <b>return</b> (İng.), <b>round trip</b> (ABD).'),
                   ('PERON', 'Which platform is it?', 'Hangi peron?', 'R: Platform 2, in five minutes.'),
                   ('AKTARMA', 'Where do I change for Camden?', 'Camden için nerede aktarma yaparım?', 'T: Aktarma yapmak: <b>change</b>.'),
                   ('İNERKEN', 'Could you tell me when to get off?', 'Ne zaman ineceğimi söyler misiniz?', "R: Sure, I'll let you know.")),
    'quiz': {'q': 'Gidiş-dönüş bilet (İngiltere):', 'options': ['two-way ticket', 'return ticket', 'back ticket'], 'answer': 1,
             'why': "İngiltere'de <b>return ticket</b>, ABD'de <b>round-trip ticket</b>."},
    'save': 'Kaydet:<br><em>yolda lazım.</em>', 'send': 'Yurt dışına gidecek arkadaşına gönder.', 'ask': 'En çok hangi şehirde kayboldun?'},
    cap(["Otobüste, trende İngilizce: bilet, peron, aktarma 🚆",
         "return ticket · Which platform? · Where do I change?",
         "", "Kaydet 📌 Yurt dışına gidecek arkadaşına gönder."], 'yurtdisi', P_YURT), 'Ulaşım')

car((71, '2026-12-24', '12:30', None), {
    'id': 'c12-restoran', 'kicker': 'RESTORANDA', 'hook': 'Restoranda<br><em>bu 5 cümle</em> yeter',
    'promise': 'Masa iste, sipariş ver, hesabı öde.',
    'items': items(('GİRİŞ', 'A table for two, please.', 'İki kişilik masa lütfen.', 'R: Right this way!'),
                   ('ÖNERİ', 'What do you recommend?', 'Ne önerirsiniz?', 'R: The fish is great today.'),
                   ('SİPARİŞ', 'Can I get the pasta, please?', 'Makarnayı alabilir miyim?', 'T: <b>I want…</b> sert duyulur; <b>Can I get…?</b> doğal.'),
                   ('ALERJİ', 'Does this have nuts in it?', 'Bunda fındık-fıstık var mı?', "R: No, it's nut-free."),
                   ('HESAP', 'Could we get the bill, please?', 'Hesabı alabilir miyiz?', 'T: Hesap: <b>the bill</b> (İng.), <b>the check</b> (ABD).')),
    'quiz': {'q': 'Hesabı isterken:', 'options': ['Give me the account.', 'Could we get the bill?', 'We want to pay money.'], 'answer': 1,
             'why': 'Hesap <b>account</b> değil. Kibarı: <b>Could we get the bill?</b>'},
    'save': 'Kaydet:<br><em>yemekte lazım.</em>', 'send': 'Yemek arkadaşına gönder.', 'ask': 'Yurt dışında en sevdiğin yemek neydi?'},
    cap(["Restoranda İngilizce: masa, sipariş, alerji ve hesap 🍽️",
         "A table for two · Can I get…? · Could we get the bill?",
         "", "Kaydet 📌 Yemek arkadaşına gönder."], 'yurtdisi'), 'Restoran')

car((81, '2026-12-26', '12:30', None), {
    'id': 'c13-yeniyilmesaj', 'kicker': 'YENİ YIL', 'hook': 'Yeni yıl mesajını<br><em>İngilizce</em> yaz',
    'promise': 'Arkadaşa, hocaya, iş yerine: hazır kalıplar.',
    'items': items(('ARKADAŞA', 'Happy New Year! Love you guys!', 'Mutlu yıllar! Sizi seviyorum!', 'T: Gruba seslenirken <b>you guys</b>.'),
                   ('HERKESE', 'Wishing you all the best in 2027!', "2027'de her şeyin en iyisini dilerim!", 'T: <b>Wishing you…</b> hem samimi hem resmî.'),
                   ('HOCANA', 'Thank you for everything this year.', 'Bu yıl her şey için teşekkürler.', 'R: Happy New Year to you too!'),
                   ('İŞ YERİNE', 'Wishing you a successful new year.', 'Başarılı bir yeni yıl dilerim.', 'T: Resmî ortam için ideal.'),
                   ('KADEH KALDIRIRKEN', "Here's to a great year!", 'Harika bir yıla!', 'T: <b>Here\'s to…</b> = …a (kadeh kaldırırken).')),
    'quiz': {'q': 'Hocana yazıyorsun:', 'options': ['Happy New Year, bro!', 'Wishing you a wonderful new year!', 'New year, new me!'], 'answer': 1,
             'why': 'Resmî ve sıcak: <b>Wishing you a wonderful new year!</b>'},
    'save': "Kaydet:<br><em>31 Aralık'ta lazım.</em>", 'send': 'Mesajını İngilizce yazacak arkadaşına gönder.', 'ask': 'Bu yıl kime İngilizce mesaj atacaksın?'},
    cap(["Yeni yıl mesajını İngilizce yaz: arkadaşa, hocaya, iş yerine 🎆",
         "Wishing you all the best in 2027! · Here's to a great year!",
         "", "Kaydet 📌 31 Aralık'ta lazım olacak."], 'yeniyil'), 'Yeni yıl mesajı')

car((91, '2026-12-29', '12:30', None), {
    'id': 'c14-hedef', 'kicker': 'YENİ YIL HEDEFLERİ', 'hook': '2027 hedefini<br><em>İngilizce</em> söyle',
    'promise': '5 kalıp, kendi hedefinle doldur.',
    'items': items(('PLAN', "This year, I'm going to learn English.", 'Bu yıl İngilizce öğreneceğim.', "T: Kararlı plan: <b>I'm going to…</b>"),
                   ('BAŞLAMAK', 'I want to start working out.', 'Spora başlamak istiyorum.', 'T: <b>start</b> + <b>-ing</b> ya da <b>to</b>: ikisi de olur.'),
                   ('BIRAKMAK', "I'm going to quit sugar.", 'Şekeri bırakacağım.', 'T: Bırakmak: <b>quit</b>, <b>give up</b>.'),
                   ('HEDEF', 'My goal is to read 12 books.', 'Hedefim 12 kitap okumak.', "R: That's a great goal!"),
                   ('DENEMEK', "I'll try to be more patient.", 'Daha sabırlı olmaya çalışacağım.', 'T: <b>try to</b> + fiil.')),
    'quiz': {'q': "‘Sigarayı bırakacağım’:", 'options': ["I'm going to quit smoking.", "I'm going to leave smoke.", 'I will stop to smoke.'], 'answer': 0,
             'why': '<b>quit smoking</b> doğru. <b>stop to smoke</b> = sigara içmek için durmak!'},
    'save': 'Kaydet:<br><em>yıl boyu bak.</em>', 'send': 'Hedefini birlikte takip edeceğin arkadaşına gönder.', 'ask': '2027 hedefini İngilizce yaz!'},
    cap(["2027 hedefini İngilizce söyle: 5 kalıp 🎯",
         "I'm going to… · I want to start… · My goal is to…",
         "", "Yorumlara 2027 hedefini İngilizce yaz, Goof düzeltsin 👇"], 'yeniyil', P_GENEL), 'Yeni yıl hedefleri')

car((93, '2026-12-31', '12:30', None), {
    'id': 'c15-yilozeti', 'kicker': '2026 ÖZETİ', 'hook': 'Bu yıl öğrendiğin<br><em>5 altın kalıp</em>',
    'promise': "Aralık'ın en kullanışlı cümleleri tek yerde.",
    'items': items(('SELAM', "What's up?", 'Ne var ne yok?', 'R: Not much! You?'),
                   ('SİPARİŞ', 'Can I get a latte, please?', 'Bir latte alabilir miyim?', 'T: <b>I want</b> yerine <b>Can I get…?</b>'),
                   ('HESAP', 'Could we get the bill?', 'Hesabı alabilir miyiz?', 'T: <b>account</b> değil, <b>bill</b>.'),
                   ('BAKARIM', "I'll see how I feel.", 'Bakarım, duruma göre.', 'T: <b>I will look</b> değil!'),
                   ('VEDA', 'Take care! See you!', 'Kendine iyi bak! Görüşürüz!', 'R: You too!')),
    'quiz': {'q': "‘What's up?’ sorusuna cevap:", 'options': ["I'm fine, thank you.", 'Not much! You?', "Yes, what's up."], 'answer': 1,
             'why': "<b>What's up?</b> hâl sormaz; cevabı: <b>Not much!</b>"},
    'save': "Kaydet:<br><em>2027'ye hazır ol.</em>", 'send': 'Birlikte İngilizce çalıştığın arkadaşına gönder.', 'ask': "2027'de İngilizceyle ne yapmak istiyorsun?"},
    cap(["Bu yıl öğrendiğin 5 altın kalıp 🏆 Mutlu yıllar!",
         "What's up? · Can I get…? · Could we get the bill? · I'll see · Take care!",
         "", "Kaydet 📌 2027'de İngilizceyle ne yapmak istiyorsun? Yorumlara yaz."], 'yeniyil', P_GENEL), 'Yılın 5 kalıbı')


def main():
    plan, posts = [], []
    for r in R:
        it = dict(r['item'], kind='reels')
        plan.append(it)
        n_old, d, t, trial = r['slot']
        posts.append({'id': it['id'], 'replaces': n_old, 'date': d, 'time': t, 'kind': 'reels', 'trial': trial,
                      'title': r['title'], 'caption': r['caption']})
    for c in C:
        it = dict(c['item'], kind='carousel')
        plan.append(it)
        n_old, d, t, _ = c['slot']
        alts = ([f"Kapak: {plain(it['hook'])}"] + [f"{x['en']} ({x['tr']})" for x in it['items']]
                + ([f"Mini test: {plain(it['quiz']['q'])}", f"Cevap: {it['quiz']['options'][it['quiz']['answer']]}"] if it.get('quiz') else [])
                + ['Özet: ' + ' · '.join(x['en'] for x in it['items']), 'Kaydet, gönder, yorum yap'])
        posts.append({'id': it['id'], 'replaces': n_old, 'date': d, 'time': t, 'kind': 'carousel', 'trial': None,
                      'title': c['title'], 'caption': c['caption'], 'alt_texts': alts})
    (HERE / 'aralik.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding='utf-8')
    (HERE / 'aralik_posts.json').write_text(json.dumps(posts, ensure_ascii=False, indent=1), encoding='utf-8')
    slots = [(p['date'], p['time']) for p in posts]
    assert len(slots) == len(set(slots)), 'aynı slota iki gönderi'
    for p in posts:
        tags = re.findall(r'#\w*[^\W\d_]\w*', p['caption'])
        assert len(tags) <= 5, (p['id'], tags)
        assert len(p['caption']) <= 2200, p['id']
    print(len(R), 'reels,', len(C), 'carousel')


if __name__ == '__main__':
    main()
