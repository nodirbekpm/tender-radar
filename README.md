# Tender Radar — MVP (1-bosqich)

Davlat va tijorat xarid maydonchalaridan tenderlarni avtomatik yig‘adigan,
foydalanuvchi ruxsatlari (per-source permissions) bilan boshqariladigan veb-platforma.

- **Backend:** Django 5 + DRF
- **DB:** PostgreSQL
- **Fon vazifalar:** Celery + Redis (+ celery-beat — soatlik yig‘ish)
- **Frontend:** Django templates + Tailwind CSS (yengil, responsiv)
- **Konteyner:** Docker Compose (bitta buyruq bilan ko‘tariladi)
- **Testlar:** pytest + pytest-django

---

## Tez ishga tushirish (Docker)

```bash
# 1. Konfiguratsiya
cp .env.example .env          # kerak bo‘lsa qiymatlarni o‘zgartiring

# 2. Stack’ni ko‘tarish (web + db + redis + celery worker + beat)
docker compose up --build -d

# 3. Demo ma’lumotni yuklash (manbalar, userlar, ruxsatlar, beat task, tenderlar)
docker compose exec web python manage.py seed_demo
```

Brauzerda oching: **http://localhost:8000**

### Demo loginlar

| Rol    | Login   | Parol        | Ko‘radigan manbalar              |
|--------|---------|--------------|----------------------------------|
| Admin  | `admin` | `admin12345` | Hammasi + admin panel (`/admin/`)|
| Test   | `demo`  | `demo12345`  | **Faqat EIS**                    |

> Admin parolini `DJANGO_SUPERUSER_USERNAME` / `DJANGO_SUPERUSER_PASSWORD`
> env orqali o‘zgartirish mumkin (seeddan oldin).

---

## Ruxsatlar tizimi (asosiy g‘oya)

Har bir foydalanuvchi **faqat o‘ziga ruxsat berilgan manbalarning** tenderlarini
ko‘radi. Bu `sources.UserSourcePermission` (user ↔ source) orqali amalga oshadi.

- Demo user boshida **faqat EIS** ko‘radi.
- Admin yangi manbani yoqish uchun:
  `/admin/` → **Users** → demo userni oching → pastdagi *“Source access”*
  inline’da kerakli manbani qo‘shing (masalan **B2B-Center**). Saqlangach,
  demo user endi o‘sha manbani ham ko‘radi.

Ruxsat tekshiruvi `apps/sources/permissions.py` da bitta joyda — HTML view’lar,
detail sahifa va REST API barchasi shu qoidaga bo‘ysunadi (superuser/staff =
barcha **enabled** manbalar).

---

## Ma’lumot manbalari (plugin/adapter arxitekturasi)

Har bir manba `BaseSource` (`apps/sources/adapters/base.py`) dan meros oladigan
adapter. Registry (`registry.py`) `adapter_key` → adapter klass bog‘laydi.

Klient talab qilgan barcha maydonchalar (EIS yagona reestri bo‘yicha eng sifatli
federal ЭТП lar, 44-FZ va 223-FZ): **EIS, Sberbank-AST, RTS-tender, B2B-Center,
Fabrikant, OTC.ru** — barchasi pipeline’ga ulangan va saytlar bo‘yicha filtrlanadi.

| Manba         | Holat                                           |
|---------------|-------------------------------------------------|
| **EIS** (zakupki.gov.ru) | ✅ Jonli — ochiq RSS eksporti orqali (44-FZ + 223-FZ) |
| Sberbank-AST, RTS-tender, B2B-Center, Fabrikant, OTC.ru | ✅ Ulangan — hozircha real ko‘rinishdagi ma’lumot bilan; har maydoncha uchun jonli endpoint/akkreditatsiya integratsiyasi keyingi qadam (`fetch_live` seam tayyor) |

**Yangi manba qo‘shish:** `BaseSource`’dan klass yozing, `@register` bilan
ro‘yxatdan o‘tkazing, `fetch()` ni implementatsiya qiling. Boshqa hech narsa
o‘zgarmaydi — UI, filtr, ruxsatlar avtomatik qo‘llab-quvvatlaydi.

EIS adapteri RSS’ni tanlaydi, chunki u captcha/login talab qilmaydigan, barqaror
va parslash oson interfeys (HTML scraping’dan ko‘ra ishonchli). Tijorat ЭТП lari
akkreditatsiya/JS talab qiladi — shuning uchun ular `fetch_live` seam bilan
tayyor turadi, demo esa real ko‘rinishdagi ma’lumot bilan to‘liq ishlaydi.

### Hujjatlarni yuklab olish (ТЗ)

Yig‘ish vaqtida tenderda hujjat (ТЗ va h.k.) bo‘lsa, fayl o‘z xotiramizga
(`MEDIA_ROOT`) yuklab olinadi — havola yo‘qolsa ham saqlanib qoladi. Bu
`DOWNLOAD_DOCUMENTS` bilan boshqariladi, `DOCUMENT_MAX_BYTES` limiti bor.
Yuklash best-effort + izolyatsiyalangan: sinsa, faqat `download_error` yoziladi.

> **Offline rejim:** sandbox/konteynerda saytlarga chiqish bo‘lmasa, `seed_demo`
> har bir manba uchun real ko‘rinishdagi namuna tenderlarni yuklaydi — demo hech
> qachon bo‘sh qolmaydi. Tarmoq bo‘lsa EIS jonli RSS fetch birinchi ishlaydi.

> **Til:** UI to‘liq **inglizcha**. Tender mazmuni (sarlavha, mijoz) manba
> tilida (rus) saqlanadi — bu real xarid ma’lumoti.

---

## Barqarorlik

- Har bir tashqi so‘rov `http_get`’da **timeout + eksponensial retry** (tenacity)
  bilan; xatolar bitta `SourceFetchError` tipiga yig‘iladi.
- **Izolyatsiya:** bitta manba sinsa, `collect_from_source` xatoni ushlaydi va
  qolgan manbalar yig‘ilishda davom etadi (`collect_all`).
- To‘liq **logging** (`apps.*` loggerlari): nima yig‘ildi, qayerda xato.
- Dublikatlar yo‘q: `(source, external_id)` bo‘yicha unique + `update_or_create`.

---

## Lokal ishga tushirish (Docker’siz)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# PostgreSQL kerak. .env’da POSTGRES_HOST=localhost qo‘ying.
export DJANGO_SECRET_KEY=dev
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# Celery (alohida terminallarda):
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Testlar

```bash
# Docker bilan:
docker compose exec web pytest

# Lokal (PostgreSQL ishlab turishi kerak):
pytest
```

---

## Loyiha tuzilmasi

```
config/                 # settings, urls, celery, wsgi/asgi
apps/
  accounts/             # auth view’lar + User admin’ga source-access inline
  sources/              # Source, UserSourcePermission, permissions
    adapters/           # base, registry, eis (real), stubs (tijorat), sample_data
  tenders/              # Tender/TenderDocument, services, tasks, views, API
    management/commands/seed_demo.py
  notifications/        # Telegram skeleti (config bilan yoqiladi)
templates/              # base, accounts/login, tenders/{list,detail,dashboard}
tests/                  # pytest: permissions, models, adapters, services, views
docker/                 # entrypoint + wait_for_db
```

## API

`/api/tenders/` — read-only, foydalanuvchining ko‘rinadigan manbalariga
chegaralangan. Filtrlar: `?q=`, `?region=`, `?fz_type=`, `?source=`,
`?price_min=`, `?price_max=`, `?ordering=-published_at`.

## Telegram (opsional)

`.env`: `TELEGRAM_ENABLED=1`, `TELEGRAM_BOT_TOKEN=...`. So‘ng admin’da
foydalanuvchiga **Telegram profile** (chat_id, is_active) qo‘shing. Yuborish
primitivi tayyor (`apps/notifications/services.py`); kim qaysi tenderni oladi —
matching qoidasi keyin kengaytiriladi.
