# VideoGrabberBot'ni Oracle Cloud "Always Free" VPS'ga deploy qilish

Bu qo'llanma botni **butunlay bepul, muddatsiz** ishlaydigan Oracle Cloud
virtual serverga (VPS) joylashtirish uchun. Railway'dan farqli o'laroq, bu
yerda peak-hour cheklovlari yoki sleep muammosi yo'q — server doim yoqilgan
turadi.

Repo'dagi `Dockerfile` va `docker-compose.yml` allaqachon shu ish uchun
tayyor — hech qanday kod o'zgartirish shart emas.

## 1-qadam: Oracle Cloud hisob yaratish

1. https://signup.oraclecloud.com ga kiring, ro'yxatdan o'ting.
2. Karta ma'lumotlarini so'raydi (tasdiqlash uchun), lekin **Always Free**
   resurslardan foydalanilganda pul yechilmaydi.
3. Ro'yxatdan o'tishda **Home Region**ni tanlaysiz — buni keyin o'zgartirib
   bo'lmaydi, shuning uchun o'zingizga yaqinroq regionni tanlang (masalan
   Singapur — `ap-singapore-1`).

## 2-qadam: Always Free VM yaratish

1. Oracle Cloud Console'da: **Compute → Instances → Create Instance**.
2. **Image and shape**:
   - Image: **Canonical Ubuntu 22.04** (yoki 24.04)
   - Shape: **Change Shape** tugmasini bosing → **Ampere → VM.Standard.A1.Flex**
     tanlang → OCPU: 1-2, Memory: 6-12 GB (bularning hammasi Always Free
     doirasida, pul yechilmaydi).
     - Agar A1 mavjud bo'lmasa (ba'zi regionlarda navbat bo'ladi), **AMD-based
       VM.Standard.E2.1.Micro** shape'ni tanlang — bu ham doim bepul, faqat
       resurs ozroq (1 OCPU, 1GB RAM), lekin bitta Telegram bot uchun yetarli.
3. **Networking**: default VCN qoldiring.
4. **Add SSH keys**: "Generate a key pair for me" tanlang va **Private Key**ni
   yuklab oling (masalan `oracle_key.pem`) — bu bilan serverga kirasiz.
5. **Create** tugmasini bosing, VM bir necha daqiqada tayyor bo'ladi.
6. Instance sahifasidan **Public IP address**ni yozib oling.

## 3-qadam: Serverga ulanish

```bash
chmod 600 oracle_key.pem
ssh -i oracle_key.pem ubuntu@SIZNING_PUBLIC_IP
```

## 4-qadam: Docker o'rnatish

```bash
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
```

Docker doim avtomatik ishga tushishini tekshiring (odatda default'dan yoqilgan):

```bash
sudo systemctl enable docker
```

## 5-qadam: Repo'ni serverga olib kelish

```bash
sudo apt install -y git
git clone https://github.com/UsmanSNT/YoutubeBot.git
cd YoutubeBot
```

## 6-qadam: Muhit o'zgaruvchilarini sozlash

```bash
cp .env.example .env
nano .env
```

`.env` faylida quyidagilarni to'ldiring:

```
TELEGRAM_TOKEN=BotFather_dan_olgan_token
ADMIN_USER_ID=userinfobot_dan_olgan_ID
LOG_LEVEL=INFO
```

Saqlang (`Ctrl+O`, `Enter`, `Ctrl+X`).

## 7-qadam: Botni ishga tushirish

```bash
docker compose up -d --build
```

Bu buyruq `Dockerfile`ni o'qib image quradi, konteynerni ishga tushiradi,
`bot_data` va `bot_logs` nomli doimiy volume'lar yaratadi (server qayta
yuklansa ham ma'lumotlar yo'qolmaydi) va `restart: unless-stopped` tufayli
server restart bo'lganda bot avtomatik qayta ishga tushadi.

## 8-qadam: Tekshirish

```bash
docker compose logs -f
```

`Bot has been started successfully` va `Starting bot polling...` yozuvlarini
ko'rishingiz kerak (`Ctrl+C` bilan log kuzatishdan chiqasiz, bot ishlashda
davom etadi). Telegram'da botga `/start` yuboring — javob berishi kerak.

## Tarmoq (Networking) haqida

Bot HTTP so'rov kutmaydi (faqat Telegram bilan polling orqali gaplashadi),
shuning uchun Oracle Cloud'da **hech qanday port ochish yoki Security List
o'zgartirish shart emas**.

## Botni yangilash (kod o'zgarganda)

```bash
cd YoutubeBot
git pull
docker compose up -d --build
```

## Foydali buyruqlar

```bash
docker compose ps              # Bot holatini ko'rish
docker compose logs -f         # Loglarni kuzatish
docker compose restart         # Botni qayta ishga tushirish
docker compose down            # Botni to'xtatish
```
