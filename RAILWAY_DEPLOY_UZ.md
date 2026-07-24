# VideoGrabberBot'ni Railway'ga deploy qilish (o'zbekcha qo'llanma)

Bu bot Python (aiogram + yt-dlp) bilan yozilgan, doimiy ishlab turadigan Telegram bot.
U sizning asosiy saytingiz (Vercel/Next.js) bilan hech qanday aloqasi yo'q — mutlaqo
alohida, o'z-o'zicha ishlaydigan xizmat sifatida deploy qilinadi.

## 1-qadam: Kerakli ma'lumotlarni oling

1. **Telegram bot yarating**: Telegram'da [@BotFather](https://t.me/BotFather) bilan
   suhbatlashing, `/newbot` buyrug'ini yuboring, bot nomini bering — sizga **token**
   beriladi (masalan `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`). Buni saqlab qo'ying.
2. **O'z Telegram ID'ingizni bilib oling**: [@userinfobot](https://t.me/userinfobot)ga
   `/start` yuboring — sizga sonli ID beradi (masalan `123456789`). Bu — bot admini
   bo'lasiz degani (invite havolalarini yaratish, foydalanuvchilarni tasdiqlash huquqi).

## 2-qadam: Railway'da hisob oching

1. https://railway.app ga kiring, GitHub yoki email orqali ro'yxatdan o'ting.
2. Yangi loyiha yarating: **New Project**.

## 3-qadam: Railway CLI orqali deploy qilish (eng oson yo'l)

GitHub'ga yuklashning hojati yo'q — kompyuteringizdagi papkani to'g'ridan-to'g'ri
Railway'ga yuklaysiz.

1. Railway CLI'ni o'rnating (Node.js kerak):
   ```bash
   npm i -g @railway/cli
   ```
2. Ushbu zip fayldagi papkani ochib, terminal orqali o'sha papkaga kiring:
   ```bash
   cd VideoGrabberBot-deploy
   ```
3. Railway'ga kiring va loyihani bog'lang:
   ```bash
   railway login
   railway init
   ```
   (So'ralganda 2-qadamda yaratgan loyihani tanlang, yoki yangisini yarating.)
4. Muhit o'zgaruvchilarini (environment variables) sozlang:
   ```bash
   railway variables --set "TELEGRAM_TOKEN=1-qadamda_olgan_token" --set "ADMIN_USER_ID=1-qadamda_olgan_ID"
   ```
5. Deploy qiling:
   ```bash
   railway up
   ```
   Bu `Dockerfile`'ni o'qib, konteynerni qurib, ishga tushiradi.

## 4-qadam: Doimiy xotira (Volume) qo'shish — MUHIM

Bot foydalanuvchilar ro'yxati, invite kodlari va vaqtinchalik fayllarni
`/app/data` papkasida saqlaydi. Agar Volume qo'shmasangiz, har safar bot qayta
ishga tushganda (deploy, restart) bu ma'lumotlar **yo'qoladi**.

1. Railway dashboard'da loyihangizni oching → xizmatingizni (service) tanlang.
2. **Settings → Volumes → New Volume**.
3. **Mount path**: `/app/data`
4. Saqlang — Railway xizmatni avtomatik qayta ishga tushiradi.

## 5-qadam: Tarmoq (Networking) sozlamasi

Bu bot HTTP so'rovlarini kutmaydi (u faqat Telegram bilan gaplashadi), shuning
uchun **"Generate Domain" tugmasini bosmang** — kerak emas. Agar Railway ogohlantirish
chiqarsa ("no exposed ports"), buni e'tiborsiz qoldiring — bot baribir ishlayveradi.

## 6-qadam: Tekshirish

1. Railway dashboard'da **Deployments → View Logs** oching.
2. `Bot has been started successfully` va `Starting bot polling...` yozuvlarini
   ko'rishingiz kerak.
3. Telegram'da botingizga `/start` yuboring — javob berishi kerak.
4. YouTube havolasini yuboring, format tanlang, faylni kuting.

## Muhim cheklovlar (loyihaning o'zida ham yozilgan)

- **Telegram Bot API 50MB fayl chegarasi bor** — undan katta videolarni past
  sifatda (SD/HD) yuklab olish kerak bo'ladi.
- **Mualliflik huquqi**: bu vosita shaxsiy/ta'lim maqsadlari uchun mo'ljallangan
  (loyihaning o'z README'sida ham shunday deyilgan) — YouTube'ning foydalanish
  shartlariga rioya qiling, tijorat maqsadida ommaviy foydalanmang.
- Narx: Railway'ning Hobby tarifida oyiga $5 bepul kredit bor — bitta doimiy
  ishlaydigan kichik bot uchun odatda shu kredit yetadi, lekin ko'p video yuklab
  olinsa (CPU/tarmoq sarfi oshadi) oshib ketishi mumkin — Railway dashboard'da
  **Usage** bo'limidan kuzatib turing.

## Keyinchalik: Supabase bilan almashtirish (ixtiyoriy)

Hozircha bot o'z ichidagi SQLite bazasidan foydalanadi (Volume orqali saqlanadi —
bu yetarli va oddiy). Agar kelajakda buni sizning mavjud Supabase Postgres bazangizga
ko'chirishni xohlasangiz (masalan statistikani boshqa joydan ham ko'rish uchun),
`bot/utils/db.py` faylini Supabase'ga ulanadigan qilib qayta yozish mumkin — buni
alohida so'rasangiz amalga oshirib beraman.
