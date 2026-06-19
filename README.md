# Tender Radar — MVP (Stage 1)

A web platform that automatically collects tenders from government and
commercial procurement marketplaces, with per-user, per-source access control.

- **Backend:** Django 5 + DRF
- **DB:** PostgreSQL
- **Background jobs:** Celery + Redis (+ celery-beat — hourly collection)
- **Frontend:** Django templates + Tailwind CSS (lightweight, responsive)
- **Container:** Docker Compose (one command to bring everything up)
- **Tests:** pytest + pytest-django

> **Scope:** this repo is **Stage 1 — collection & parsing only**. Scoring,
> AI document audit and CRM integration are future stages.

---

## Quick start (Docker)

```bash
# 1. Configure
cp .env.example .env          # adjust values if needed

# 2. Bring up the stack (web + db + redis + celery worker + beat)
docker compose up --build -d

# 3. Load demo data (sources, users, permissions, beat task, tenders)
docker compose exec web python manage.py seed_demo
```

Open in the browser: **http://localhost:8000**

> **Important:** Docker containers do **not** route through a host VPN, and
> zakupki.gov.ru only accepts **Russian IPs**. For real live data, see
> [Real data collection](#real-data-collection-host--vpn) below.

### Demo logins

| Role  | Login   | Password     | Visible sources                  |
|-------|---------|--------------|----------------------------------|
| Admin | `admin` | `admin12345` | All + admin panel (`/admin/`)    |
| Test  | `demo`  | `demo12345`  | **EIS only**                     |

> The admin password can be set via the `DJANGO_SUPERUSER_USERNAME` /
> `DJANGO_SUPERUSER_PASSWORD` env vars (before seeding).

---

## Permission system (core idea)

Each user sees tenders **only from the sources they are granted**. This is
implemented via `sources.UserSourcePermission` (user ↔ source).

- The demo user starts with **EIS only**.
- To grant a new source: `/admin/` → **Users** → open the demo user → in the
  *“Source access”* inline at the bottom, add the source (e.g. **B2B-Center**).
  After saving, the demo user can see that source too.

The permission check lives in one place — `apps/sources/permissions.py` — so the
HTML views, the detail page and the REST API all obey the same rule
(superuser/staff = all **enabled** sources).

---

## Data sources (plugin/adapter architecture)

Every source is an adapter subclassing `BaseSource`
(`apps/sources/adapters/base.py`). A registry (`registry.py`) maps
`adapter_key` → adapter class.

All marketplaces the client requested (the highest-quality federal ETPs in the
EIS unified registry, under 44-FZ and 223-FZ): **EIS, Sberbank-AST, RTS-tender,
B2B-Center, Fabrikant, OTC.ru** — all wired into the pipeline and filterable by
site.

| Source        | Status                                          |
|---------------|-------------------------------------------------|
| **EIS** (zakupki.gov.ru) | ✅ Live — real scraping of the search results page (44-FZ + 223-FZ): number, title, customer, initial price (NMC), dates, and real document files from the documents tab |
| Sberbank-AST, RTS-tender, B2B-Center, Fabrikant, OTC.ru | ✅ Wired — currently served with realistic sample data; live per-platform endpoint/accreditation integration is the next step (a `fetch_live` seam is ready) |

**Add a new source:** write a `BaseSource` subclass, register it with
`@register`, implement `fetch()`. Nothing else changes — the UI, filters and
permissions support it automatically.

### How EIS parsing works

EIS is scraped from its **search results page**
(`/epz/order/extendedsearch/results.html`), which returns static HTML cards with
all the real fields (registry number, object/title, customer, initial price,
publish/deadline dates). Each tender is then enriched from its **documents tab**
(`.../view/documents.html`), where real attachments (technical spec, contract
draft, NMC justification) are exposed as `filestore` download links.

Prices follow the Russian format (space = thousands, comma = decimal): a single
comma **or** dot is treated as the decimal separator, so `13 704 946,33` is
stored as `13704946.33` (no 100× errors).

### Document download

When a tender has attachments (technical spec, etc.), the file is downloaded
into our own storage (`MEDIA_ROOT`) so it survives even if the source removes
the link. Controlled by `DOWNLOAD_DOCUMENTS`, bounded by `DOCUMENT_MAX_BYTES`.
Downloads are best-effort and isolated: on failure only `download_error` is
recorded. Files are saved under their real name (from the attachment title).

> **UI language:** the interface is fully **English**. Tender content (title,
> customer) is kept in the source language (Russian) — it's real procurement
> data.

> **Offline mode:** if the machine can't reach the marketplaces, `seed_demo`
> loads realistic sample tenders per source so the demo is never empty. With
> network access, the live EIS scrape runs first.

---

## Reliability

- Every outbound request goes through `http_get` with a **timeout + exponential
  retry** (tenacity); errors collapse into a single `SourceFetchError` type.
- **Isolation:** if one source breaks, `collect_from_source` captures the error
  and the remaining sources keep collecting (`collect_all`).
- Full **logging** (`apps.*` loggers): what was collected, where it failed.
- No duplicates: unique on `(source, external_id)` + `update_or_create`.

---

## Real data collection (host + VPN)

zakupki.gov.ru only accepts **Russian IPs**, and **Docker containers do not
route through a host VPN**. So run the real live collection **on the host**
(with a system-level Russian VPN enabled), Docker-free — zero infrastructure
(SQLite):

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

# Enable a system VPN (OpenVPN, RU). Verify:
#   curl https://zakupki.gov.ru   → should respond

set USE_SQLITE=1
set DJANGO_SECRET_KEY=dev
set DOWNLOAD_DOCUMENTS=1
python manage.py migrate
python manage.py collect --source eis --limit 10   # live real EIS + files
python manage.py runserver
```

Then open http://127.0.0.1:8000 — real tenders with real price/customer/dates
and downloaded technical-spec files. For automatic collection use Celery beat
(below) or schedule `collect`. For production the most reliable option is a
**Russian VPS**: there Docker reaches zakupki.gov.ru directly and everything
runs 24/7.

## Local run (without Docker, PostgreSQL)

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# PostgreSQL required. Set POSTGRES_HOST=localhost in .env.
export DJANGO_SECRET_KEY=dev
python manage.py migrate
python manage.py seed_demo
python manage.py runserver

# Celery (in separate terminals):
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Manual collection

```bash
python manage.py collect                 # all enabled sources
python manage.py collect --source eis --limit 20
```

Staff users can also trigger a run from the dashboard with the **“Scan now”**
button.

## Tests

```bash
# With Docker:
docker compose exec web pytest

# Local (PostgreSQL running), or zero-infra with SQLite:
pytest
USE_SQLITE=1 pytest
```

---

## Project structure

```
config/                 # settings, urls, celery, wsgi/asgi
apps/
  accounts/             # auth views + source-access inline on the User admin
  sources/              # Source, UserSourcePermission, permissions
    adapters/           # base, registry, eis (real), stubs (commercial), sample_data
  tenders/              # Tender/TenderDocument, services, tasks, views, API
    management/commands/ # seed_demo, collect
  notifications/        # Telegram skeleton (enabled via config)
templates/              # base, accounts/login, tenders/{list,detail,dashboard}
tests/                  # pytest: permissions, models, adapters, services, views, documents
docker/                 # entrypoint + wait_for_db
```

## API

`/api/tenders/` — read-only, scoped to the user's visible sources. Filters:
`?q=`, `?region=`, `?fz_type=`, `?source=`, `?price_min=`, `?price_max=`,
`?ordering=-published_at`.

## Telegram (optional)

In `.env`: `TELEGRAM_ENABLED=1`, `TELEGRAM_BOT_TOKEN=...`. Then add a
**Telegram profile** (chat_id, is_active) to a user in the admin. The send
primitive is ready (`apps/notifications/services.py`); the matching rule (who
gets notified about which tender) can be extended later.
