## Aperture Studio

Aplikacija za upravljanje fotografij in dostavo galerij za poklicne fotografe.

### Zahteve

- **Docker z Docker Compose**: `docker --version` in `docker-compose --version`. Na Macu
  priporočam OrbStack ali Colima (lažje, hitrejše, varčnejše s RAM-om):
  ```bash
  colima start --cpu 6 --memory 8 --vm-type vz --mount-type virtiofs
  ```
- **uv** (Python package manager): Za lokalna orodja (linting, tests) na gostitelju.
  Namestitev:
  ```bash
  brew install uv
  uv python install 3.13
  ```

### Prvi zagon

1. **Preslika `.env`:**
   ```bash
   cp .env.example .env
   ```

2. **Nastavi `DJANGO_SECRET_KEY`:**
   ```bash
   DJANGO_SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
   ```
   V `.env` zamenjaj `change-me-to-a-long-random-string` z generiranim ključem.

3. **Zaženi Docker Compose:**
   ```bash
   docker compose up --build -d
   ```

4. **Zaženi migracije:**
   ```bash
   docker compose exec web python manage.py migrate
   ```

5. **Seed demo podatke:**
   ```bash
   docker compose exec web python manage.py seed_demo
   ```

6. **Dostopi do aplikacije:**
   - **Nadzorna plošča:** http://localhost:8000/
   - **Prijava:** demo@aperture.local, geslo: demo-geslo-2026
   - **Mailpit (e-pošta):** http://localhost:8025/
   - **Stran stilov:** http://localhost:8000/stil/ (samo za osebje)

### Docker Compose storitve

| Storitev | Namenjena |
|----------|-----------|
| **web** | Django aplikacija (gunicorn v produkciji, runserver v razvoju) |
| **db** | PostgreSQL 17 baza podatkov |
| **redis** | Redis cache in message broker za Celery |
| **worker** | Celery worker za asinchrone naloge (obdelava slik, e-pošta) |
| **beat** | Celery beat za ponavljajoče naloge (čiščenje, stroški) |
| **tailwind** | Tailwind CLI za opazovanje CSS sprememb v realnem času |
| **mailpit** | Fake SMTP in webmail UI za razvoj (http://localhost:8025) |

### Testiranje

Zaženi teste (vedno s `config.settings.test`, vsiljeno v `pyproject.toml`):
```bash
docker compose run --rm web pytest
```

Zaženi teste v paralelnih procesih:
```bash
docker compose run --rm web pytest -n auto
```

### Linting in formatiranje

Preveri kod s Ruff:
```bash
docker compose run --rm web ruff check .
```

Formatiraj kod:
```bash
docker compose run --rm web ruff format .
```

Preveri brez sprememb:
```bash
docker compose run --rm web ruff format --check .
```

### Prevodi (i18n)

Ustvari prevajalne datoteke za slovenščino:
```bash
docker compose exec web python manage.py makemessages -l sl --ignore=.venv
```

Kompajiraj prevode:
```bash
docker compose exec web python manage.py compilemessages
```

### Struktura projekta

Glejte `/docs/NACRT.md` za podrobno dokumentacijo. Bistveno:

```
aperture_studio/
├── assets/
│   └── css/app.css          ← Tailwind vhod (@theme direktive)
├── static/
│   ├── css/app.css          ← Tailwind izhod (avtomatski)
│   └── vendor/              ← ESM knjižnice (PhotoSwipe, GSAP, Lenis)
├── apps/
│   ├── core/                ← Nadzorna plošča, nastavitve studioa, template tagi
│   ├── accounts/            ← Prijava z e-pošto, registracija
│   ├── clients/             ← Stranke (CRM)
│   ├── shoots/              ← Fotografiranja in paketi
│   ├── scheduling/          ← Dogodki in FullCalendar API
│   ├── photos/              ← Obdelava slik, shramba, podpisani URL-ji
│   ├── galleries/           ← Galerije, dostop, analitika
│   ├── portfolio/           ← Javni portfolio, povpraševanja
│   └── finance/             ← Prihodki, stroški, računi
├── templates/               ← HTML template-i (django-cotton)
├── config/
│   ├── settings/            ← base.py, dev.py, test.py, prod.py
│   ├── formats/sl/          ← Slovenski format datumov in časa
│   └── urls.py
├── docs/
│   └── NACRT.md             ← Arhitektura in odločitve
├── pyproject.toml           ← Odvisnosti in Ruff konfiguracija
├── compose.yaml             ← Docker Compose storitve
└── README.md                ← Ta datoteka
```

**CSS:** Tailwind vhodna datoteka je `assets/css/app.css`, izhod je `static/css/app.css`.

### Produkcija

Nastavitve za produkcijo so v `config/settings/prod.py`. Glavne spremenljivke `.env`:

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod
STORAGE_BACKEND=s3
S3_ENDPOINT_URL=https://<account>.r2.cloudflarestorage.com
S3_ACCESS_KEY_ID=<key>
S3_SECRET_ACCESS_KEY=<secret>
S3_PRIVATE_BUCKET=aperture-private
S3_PUBLIC_BUCKET=aperture-renditions
S3_PUBLIC_DOMAIN=img.example.com
```

Aplikacija se zaganja kot `gunicorn config.wsgi`, baza in cache/broker sta na zunanjih storitvah
(Render, Heroku Postgres, Redis Cloud).

Podrobnosti v `/docs/NACRT.md`.
