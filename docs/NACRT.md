# Aperture Studio – načrt

Stanje: **osnutek, čaka na potrditev** (21. 9. 2026). Koda se začne pisati šele po potrditvi.

---

## 0. Predpogoji (manjka pred 1. fazo)

| Kaj | Stanje | Ukrep |
|---|---|---|
| Docker (Compose) | ni nameščen | Docker Desktop ali OrbStack (lažji na Macu) |
| Node / npx | ni nameščen | `brew install node`: rabi ga samo Playwright MCP plugin, projekt sam je brez Nodea |
| Python 3.13 | na gostitelju 3.9 | aplikacija teče v Dockerju; za orodja na gostitelju `uv python install 3.13` |
| Plugini | vsi nameščeni | Playwright MCP se ne poveže, dokler ni Nodea |

---

## 1. Odločitve, ki jih potrjuješ

| # | Odločitev | Predlog | Zakaj |
|---|---|---|---|
| 1 | Tailwind v4 | **`django-tailwind-cli`** (samostojni Tailwind binarni program) | Brez Nodea, npm in `node_modules`. Paket prenese en binarni program, konfiguracija v4 je v CSS (`@theme`), zato `tailwind.config.js` ni potreben. `django-tailwind` zahteva Node + npm + posebno „theme“ aplikacijo. |
| 2 | JS knjižnice | pripete ESM datoteke v `static/vendor/` + `<script type="importmap">`, brez bundlerja | Brez gradbenega koraka za JS. Vsaka stran naloži samo tisto, kar rabi (galerija: PhotoSwipe + GSAP; javne strani: Lenis). |
| 3 | Obdelava slik | **libvips (pyvips)** + **exiftool** v Celery workerju | Pri datotekah s 40–60 MP je libvips nekajkrat hitrejši od Pillowa in porabi desetino RAM-a. exiftool odstrani GPS brez izgube kakovosti (brez ponovnega kodiranja). |
| 4 | Formati izpeljank | **AVIF + JPEG** (WebP izbirno v nastavitvah) | AVIF je podprt v >93 % brskalnikov, JPEG pokrije ostalo. WebP bi dodal ~50 % prostora in obdelave za skoraj nič dodatnih uporabnikov. |
| 5 | Nalaganje | lasten **razsekan upload prek Djanga** (8 MB kosi, 3 datoteke vzporedno, nadaljevanje po prekinitvi) | Enaka koda deluje z lokalnim diskom (dev) in R2 (prod). Neposreden upload v R2 (presigned multipart) je kasnejša optimizacija. |
| 6 | Dostop do datotek | izpeljanke (web velikosti) na **neugibnih UUID ključih** prek CDN; **originali, ZIP, računi in računi za stroške samo prek podpisanih URL-jev** (10 min) | Podpisani URL-ji za vsako sličico bi onemogočili CDN predpomnjenje in upočasnili galerije s 500 fotografijami. Ključ izpeljanke je enako zaupen kot povezava do galerije. |
| 7 | Najemnik (tenant) | model **`Studio`** (1 lastnik zdaj, člani ekipe kasneje), vsi modeli imajo `studio` FK | Kasnejši asistenti ali drugi fotografi ne zahtevajo migracije podatkov. |
| 8 | Fotografija ↔ galerija | fotografija pripada **eni** galeriji; posnetek ima lahko več galerij (npr. „predogled“ in „končna“) | Enostavno in hitro. Pri predogledu pomeni podvojen upload, kar je sprejemljivo. |
| 9 | Placeholderji | LQIP (24 px WebP kot data-URI, ~400 B) + prevladujoča barva + svetlost na fotografijo | Brez JS dekodiranja (blurhash ga zahteva). Svetlost določi, ali steklo nad fotografijo potrebuje zatemnitev. |
| 10 | Format datuma | **`21. 9. 2026`** (`j. n. Y`, brez vodilnih ničel, po pravopisu) | Če želiš `21. 09. 2026`, je to ena vrstica. |
| 11 | Registracija | odprta, z obvezno potrditvijo e-pošte, izklopljiva z env spremenljivko | Multi-tenant od začetka pomeni, da se lahko prijavijo tudi drugi fotografi. |
| 12 | Python / Postgres | Python **3.13**, Django **5.2 LTS**, PostgreSQL **17**, Redis 7 | 5.2 je zadnja LTS iz serije 5.x (podpora do 4/2028). |

---

## 2. Arhitektura

```
 brskalnik (HTMX, Alpine, FullCalendar, PhotoSwipe, GSAP, ApexCharts)
     │ HTML / JSON / chunki                       │ <picture srcset>
     ▼                                            ▼
 ┌──────────────────┐                   ┌─────────────────────────┐
 │ web: Django 5.2  │ ─ presigned 302 ─►│ zasebna shramba         │
 │ gunicorn/runserv │                   │ originali, ZIP, prejemki│
 └──┬─────────┬─────┘                   ├─────────────────────────┤
    │SQL      │enqueue                  │ shramba izpeljank (CDN) │
    ▼         ▼                         │ UUID ključi, brez list. │
 ┌────────┐ ┌───────┐   ┌──────────────┐└─────────▲───────────────┘
 │Postgres│ │ Redis │◄──┤ worker       ├──────────┘
 └────────┘ └───────┘   │ (vips, exif, │   dev: oboje lokalni disk
                        │  zip, e-pošta│   prod: Cloudflare R2
                        ├──────────────┤
                        │ beat (cron)  │ ponavljajoči stroški, čiščenje
                        └──────────────┘
 mailpit (dev): lovi vso e-pošto, UI na :8025
```

**Docker Compose storitve:** `web`, `db`, `redis`, `worker`, `beat`, `mailpit`, `tailwind` (watch).
`beat` rabimo za ponavljajoče stroške, `mailpit` pa za preverjanje e-pošte (potrditev računa, ZIP pripravljen, povpraševanje) brez pravega SMTP-ja.

**Celery vrste:** `default` (e-pošta, drobno), `images` (obdelava fotografij), `zips` (arhivi). Tako dolg ZIP ne blokira obdelave novih fotografij.

---

## 3. Django aplikacije

| Aplikacija | Vsebina |
|---|---|
| `core` | `Studio` (najemnik), `TenantModel`, middleware `request.studio`, mešanice za CBV, template tagi (`eur`, datumi), nadzorna plošča, stran stilov `/stil/` |
| `accounts` | lasten `User` (prijava z e-pošto, brez uporabniškega imena), allauth adapterji, registracija ustvari `Studio` |
| `clients` | stranke (CRM), profil s časovnico |
| `shoots` | fotografiranja, paketi, lokacije, statusni tok |
| `scheduling` | dogodki, API za FullCalendar, ICS vir (ne `calendar`, da ne povozi Pythonove knjižnice) |
| `photos` | `Photo`, `UploadSession`, obdelava slik, shramba, podpisani URL-ji |
| `galleries` | galerije, sekcije, teme, dostop, obiskovalci, priljubljene, komentarji, prenosi, analitika |
| `portfolio` | javni portfolio, kategorije, zgodbe, povpraševanja |
| `finance` | prihodki, stroški, kategorije, ponavljajoči stroški, računi (PDF), nadzorna plošča, CSV |

---

## 4. Podatkovni model

Vsi modeli razen `User` dedujejo `TenantModel` (`studio` FK, `created_at`, `updated_at`, manager `.for_studio(studio)`).
Denar: `DecimalField(12, 2)`, valuta EUR kot konstanta (brez django-money).

**core / accounts**
- `User`: email (unikaten, login), ime, jezik vmesnika.
- `Studio`: owner (1:1 User), name, slug (za `/p/<slug>/`), kontakt, naslov, logo, davčna št., IBAN, `vat_registered`, `default_vat_rate` (22 %), `ics_token`, privzete nastavitve galerij (rok veljavnosti, odstrani GPS, vodni žig: slika, prosojnost, položaj, velikost).

**clients**
- `Client`: ime, priimek, podjetje, email, telefon, naslov, davčna št., opombe, vir (portfolio, priporočilo, Instagram, drugo). Indeks `(studio, email)`.

**shoots**
- `Location`: ime, naslov, povezava na zemljevid, opombe.
- `Package`: ime, opis, cena, trajanje, št. fotografij, `delivery_days`, aktiven, vrstni red.
- `Shoot`: client, package?, location?, naslov, **status** (`inquiry → confirmed → shot → editing → delivered → paid`, poleg tega `cancelled` izven toka), cena (privzeto iz paketa), opombe, `status_changed_at`.
  Izračunano: plačano (vsota prihodkov) in odprto.

**scheduling**
- `Event`: kind (`shoot`, `meeting`, `editing_deadline`, `delivery_deadline`, `personal`), naslov, start, end, `all_day`, shoot?, client?, location?, opombe, `is_tentative` (povpraševanja). Indeks `(studio, start)`.
  Ob potrditvi posnetka z datumom se samodejno ustvarita roka za obdelavo in dostavo (iz `Package.delivery_days`).

**photos**
- `Photo`: gallery, section?, uuid, `original` (zasebna shramba), izvirno ime, velikost, sha256, širina, višina, `taken_at`, `exif` (JSONB: aparat, objektiv, goriščnica, zaslonka, čas, ISO; GPS se nikoli ne shrani), status (`pending/processing/ready/failed`), napaka, **`renditions` (JSONB manifest)**, `rendition_version`, `lqip`, `dominant_color`, `luminance`, `position`.
  Manifest v JSONB pomeni, da se `srcset` zgradi brez dodatnih poizvedb (brez N+1).
- `UploadSession`: gallery, uuid, ime datoteke, velikost, prejeti bajti, status, pot do začasne datoteke, rok.

**galleries**
- `Gallery`: shoot?, client?, naslov, `token` (32 B, urlsafe, unikaten, zamenljiv), `password_hash`, `password_version`, `expires_at`, `is_published`, tema, postavitev, `cover_photo`, datum dogodka, uvodno besedilo, `allow_downloads`, `download_size` (`web/original/both`), `allow_favorites`, `allow_comments`, `watermark`, `strip_gps`, jezik.
- `GallerySection`: naslov, opis, `position`.
- `GalleryVisitor`: gallery, `key` (piškotek), ime, email, prvi in zadnji obisk.
- `Favorite`: visitor, photo (unikatno skupaj).
- `PhotoComment`: visitor, photo? (prazno pomeni komentar na galerijo), besedilo, `read_at`.
- `DownloadRequest`: gallery, visitor, velikost, status, datoteka (zasebno), bajti, `fingerprint` (ponovna uporaba istega ZIP-a), email, `expires_at`.
- `GalleryEvent` (analitika): gallery, visitor?, kind (`view`, `photo_view`, `download_photo`, `download_zip`, `favorite`, `comment`), photo?, `ua_family`, `ip_hash` (dnevno menjana sol, GDPR). Indeks `(gallery, kind, created_at)`.

**portfolio**
- `Portfolio` (1:1 Studio): objavljen, naslov, o meni, portret, kontakti, družbena omrežja, tema, SEO opis.
- `PortfolioCategory`: ime, slug, opis, naslovna fotografija, `position`.
- `PortfolioStory`: category, izvorna galerija?, naslov, slug, uvod, naslovna fotografija, objavljena, `position`; fotografije prek `PortfolioStoryPhoto` (story, photo, position).
- `Inquiry`: ime, email, telefon, želeni datum, vrsta ali paket, sporočilo, `ip_hash`; povezave na ustvarjeno stranko, posnetek in dogodek.
  Oddaja povpraševanja ustvari ali najde `Client` (po emailu), ustvari `Shoot(status=inquiry)` in `Event(kind=shoot, is_tentative=True)`, fotografu pošlje obvestilo, stranki pa samodejni odgovor.

**finance**
- `ExpenseCategory`: ime, slug, barva, `position`. Ob ustvarjenju studia se napolnijo: oprema, programska oprema in naročnine, potni stroški, marketing, ostalo.
- `Expense`: datum, znesek, DDV (izbirno), kategorija, dobavitelj, opis, `receipt` (zasebno), `recurring?`, `period`. Unikatno `(recurring, period)`, zato generator ne more ustvariti dvojnikov.
- `RecurringExpense`: ime, dobavitelj, znesek, kategorija, interval (`monthly/yearly`), `start_date`, `end_date?`, aktiven.
- `Income`: datum, znesek, opis, client?, shoot?, invoice?, način (nakazilo, gotovina, kartica, drugo).
  **Predlogi prihodkov** so poizvedba, ne tabela: plačani posnetki, pri katerih je vsota prihodkov manjša od cene. Klik ustvari prihodek.
- `Invoice`: številka (unikatna na studio, dodeljena s `select_for_update` na `InvoiceSequence(studio, year)`), client, shoot?, datumi izdaje, opravljene storitve in zapadlosti, `vat_rate`, opombe, status (`draft/issued/paid`), shranjen PDF ob izdaji.
- `InvoiceLine`: opis, količina, cena, `position`.

---

## 5. Varnost in multi-tenancy

- **Izolacija:** `StudioScopedMixin` filtrira `get_queryset()` po `request.studio` in ob shranjevanju nastavi `studio`. Tuji objekti vrnejo **404** (ne 403), da se ne razkrije njihov obstoj.
  **Vsa `ModelChoiceField` polja v obrazcih so omejena na studio.** To je najpogostejša luknja (npr. izbira tuje stranke v obrazcu posnetka).
- **Dostop do galerije:** samo prek `token`. Neobjavljena galerija vrne 404. Potekla prikaže lepo stran s kontaktom fotografa. Geslo je zgoščeno z Argon2. Odklep je shranjen v seji in vezan na `password_version`, zato menjava gesla takoj odjavi vse obiskovalce. Omejitev poskusov: 5 na minuto in 30 na uro na IP + galerijo (django-ratelimit, Redis), nato 429.
- **Glave na straneh galerij:** `Referrer-Policy: same-origin` (skrivni žeton ne uhaja prek Referer glave na zunanje strani), `X-Robots-Tag: noindex` in `<meta robots noindex>`.
- **Datoteke:** originali, ZIP-i, prejemki in računi so samo v zasebni shrambi. View preveri pravice in vrne 302 na presigned URL (10 min, `Content-Disposition: attachment` z izvirnim imenom). V dev okolju enako prek `TimestampSigner` in `FileResponse`.
- **Upload:** omejitev velikosti (100 MB/datoteko), preverjanje z dejanskim dekodiranjem (ne po končnici), meja slikovnih pik (zaščita pred „decompression bomb“), shranjevanje pod UUID imeni.
- **CSRF** povsod: HTMX pošlje `X-CSRFToken` prek `hx-headers` na `<body>`, `fetch` pomočnik ga doda sam.
- **CSP** (django-csp) z nonce vrednostmi. Uporabimo Alpine **CSP build** (komponente prek `Alpine.data`, brez `eval`) in `htmx.config.allowEval = false`.
- **Povpraševalni obrazec:** rate limit, skrito polje (honeypot) in časovna kontrola. Cloudflare Turnstile po potrebi kasneje.
- **allauth:** obvezna potrditev e-pošte, vgrajene omejitve poskusov, Google OAuth (Client ID vneseš v `.env`).
- Produkcijske `SECURE_*` nastavitve, skrivnosti samo v `.env` (v `.gitignore`).

---

## 6. Cevovod za fotografije

1. **Upload:** Alpine uploader (povleci in spusti ter izbira map) razreže datoteko na 8 MB kose in pošilja 3 datoteke vzporedno. Prikazuje napredek za vsako datoteko in skupno, neuspel kos poskusi 3-krat. Strežnik zna povedati, koliko bajtov je že prejel, zato je nadaljevanje mogoče.
2. **Ob zaključku:** preveri velikost, premakne v `originals/<studio>/<gallery>/<uuid>.<ext>`, ustvari `Photo(pending)` in doda nalogo v vrsto `images`.
3. **`process_photo`:**
   - exiftool prebere metapodatke in jih očisti v JSON. Če je `strip_gps` vklopljen, odstrani GPS in XMP geotag iz originala brez izgube kakovosti.
   - libvips samodejno zasuka sliko po EXIF usmeritvi in jo **pretvori v sRGB** (fotografi pogosto delajo v Adobe RGB ali ProPhoto; brez pretvorbe so izpeljanke v brskalniku izprane).
   - Izdela velikosti **480 / 960 / 1600 / 2400** (lightbox na retina zaslonih), rahlo izostri po pomanjšanju, iz izpeljank odstrani metapodatke (ohrani avtorja, avtorske pravice in sRGB ICC), po potrebi doda vodni žig. Original se ne spreminja, razen odstranitve GPS.
   - Izračuna LQIP, prevladujočo barvo in povprečno svetlost ter zapiše manifest.
4. **Napredek za fotografa:** HTMX na 2 s osveži stanje („312 od 480 pripravljenih“).
5. **Ključi izpeljank:** `r/<photo-uuid>/<version>/<w>.<fmt>`. Nova verzija (npr. sprememba vodnega žiga) dobi nove ključe, zato CDN nikoli ne vrne stare slike.
6. **ZIP (`zips`):** `fingerprint` je sestavljen iz ID-jev fotografij, verzije in velikosti. Če ZIP z istim odtisom že obstaja, se uporabi znova. Datoteke se pretočijo v ZIP64 brez stiskanja (JPEG se ne stisne dodatno), znotraj so mape po sekcijah z izvirnimi imeni. Obiskovalec dobi e-pošto s povezavo, ki velja 7 dni, beat nato ZIP pobriše.
7. **Beat:** ponavljajoči stroški (vsak dan ob 3:00, dohiti zamujene mesece, pravilno obravnava 31. v mesecu), čiščenje ZIP-ov in opuščenih uploadov (na uro).

**Tveganje:** kodiranje AVIF je počasno (1–2 s na veliko velikost). Blažimo ga z več procesi workerja in nastavljivimi formati. V 1. fazi test preveri, da ima Docker slika (Debian trixie) AVIF enkoder. Rezerva je Pillow z vgrajenim AVIF.

---

## 7. Design system

### Koncept: „temnica in svetlomiza“
Vmesnik je **nevtralno siv brez barvnega odtenka**. To ni estetska odločitev: vsak barvni odtenek v okolici spremeni zaznavo barv na fotografiji. Zato Lightroom in standard ISO 3664 za ocenjevanje slik uporabljata nevtralno sivo okolico. Temni način je siva okolica za ocenjevanje fotografij (ne črna), svetli pa osvetljena svetlomiza.

**Kaj sem v prvem osnutku zavrgel in zakaj:** rdeč „safelight“ poudarek na skoraj črni podlagi, kremasto „foto papir“ podlago za svetli način in monospace pisavo za EXIF podatke. Vse tri so generični privzeti izbori, ki se pojavijo pri vsakem podobnem briefu. Obarvan vmesnik bi poleg tega kvaril presojo barv fotografij.

### Barve (izhodišče, na strani stilov jih preverim za AA kontrast)
| Žeton | Temni | Svetli |
|---|---|---|
| okolica (`--surround`) | `#262626` | `#E9E9E9` |
| površina (`--surface`) | `#303030` | `#FAFAFA` |
| črta (`--line`) | `#414141` | `#D2D2D2` |
| besedilo (`--ink`) | `#EDEDED` | `#1C1C1C` |
| drugotno (`--ink-2`) | `#A6A6A6` | `#5C5C5C` |

- **Poudarek v aplikaciji ni barva, ampak svetlost:** fokus je bel obroč z odmikom, aktivno stanje je svetlejša površina.
- **Poudarek galerije se vzame iz fotografije:** prevladujoča barva naslovne fotografije, samodejno popravljena na AA kontrast, obarva ♥ in glavni gumb. Vsaka galerija je zato malo drugačna, vmesnik pa ne tekmuje s fotografijami.
- **Barve vrst dogodkov** so iz polj **ColorChecker Classic** (fotografova referenčna tablica): umirjene, naravne, med seboj ločljive. Npr. fotografiranje = oranžno rumena, sestanek = modro nebo, obdelava = modri cvet, dostava = zmerno rdeča, osebno = listje.

### Tipografija
- **Naslovna pisava: Bodoni Moda** (variabilna, z osjo za optično velikost, torej prave display reze za velike naslove galerij). Izhaja iz besednjaka modnih in poročnih foto revij. Na nevtralni sivi podlagi, brez krem barve in brez toplega poudarka, deluje kot revija, ne kot predloga.
- **UI pisava: Hanken Grotesk** (kandidat; na strani stilov preverim tabelarične številke in č, š, ž, ć, đ, sicer Public Sans).
- Številke v financah, EXIF in časih: UI pisava s `font-variant-numeric: tabular-nums`, ne monospace.
- Lestvica velikosti po razmerju 1,25 (UI) in 1,5 (display). Besedilo največ ~70 znakov na vrstico. Brez VELIKIH ČRK za oznake.
- Pisave so gostovane lokalno (woff2, podmnožici latin in latin-ext).

### Liquid Glass na spletu
- **Dve različici po HIG:**
  - *regular* za navigacijo, stranske vrstice, popoverje in modalna okna: blur ~24 px, saturate 170 %, prosojnost ~72 %;
  - *clear* samo za kontrole nad fotografijami (orodna vrstica galerije, lightbox): bolj prozorna. **Zatemnitev 35 % se doda samodejno, kadar je fotografija pod njo svetla** (svetlost je shranjena pri vsaki fotografiji).
- Zgoraj je spekularni rob (`inset 0 1px 0` bel z nizko prosojnostjo), senca ima dve plasti (bližnjo ostro in daljno mehko). **Radiji so koncentrični:** notranji = zunanji − odmik.
- **Pravila:** steklo samo na kontrolah in plavajočih plasteh, nikoli na vsebini ali daljšem besedilu, nikoli steklo na steklu.
- **Lom svetlobe** (SVG `feDisplacementMap`) samo na navigacijski vrstici in glavnem plavajočem gumbu, samo v Chromiumu (razred `.has-refraction`). Drugje ostane samo blur.
- **Rezervne različice:** `@supports not (backdrop-filter)` in `prefers-reduced-transparency: reduce` dasta neprosojno površino, `prefers-contrast: more` pa neprosojno površino z 1 px robom.
- Na strani stilov je steklo prikazano nad svetlo, temno in razgibano fotografijo, da preverim kontrast v najslabšem primeru.

### Postavitev
- **Aplikacija:**
  - na namizju plavajoča steklena navigacija levo (ozek pas, ki se razširi);
  - na telefonu plavajoča spodnja vrstica z zavihki (doseg palca), ki se razširi v meni;
  - vsebina je poravnana levo, obrazci in besedilo so ozki, tabele in koledar široki.
- **Galerija za stranke** (glavni izdelek; tukaj je ves pogum, drugje je vmesnik tih):
  - naslovna fotografija čez cel zaslon (`100svh`) z naslovom v Bodoni Moda spodaj levo;
  - ob drsenju se naslovnica umakne mreži (**edini orkestriran trenutek** z GSAP);
  - nato poravnana mreža z ozkimi razmiki, zgrajena s CSS `flex-grow` = razmerje stranic, brez JS in brez premikanja postavitve.
- **Teme galerij** (tokeni + postavitev + tipografija):
  1. **Temnica**: siva okolica, poravnana mreža, ozki razmiki.
  2. **Svetlomiza**: svetla, fotografije kot odtisi s tankim robom in širokimi robovi.
  3. **Fotoknjiga**: ena fotografija ali par v vrsti, veliko praznega prostora, velika tipografija (za poroke in reportaže).
  4. **Kontaktna kopija**: gosta mreža s **številkami sličic**, namenjena izbiranju. Številke tukaj niso okras: stranka napiše „všeč mi je 34“.

### Gibanje
- **View Transitions:**
  - med stranmi aplikacije in iz portfolija v zgodbo, kjer se naslovnica preoblikuje v glavno fotografijo zgodbe;
  - HTMX zamenjave vsebine z `transition:true`.
- **PhotoSwipe:** povečava iz sličice v celozaslonski pogled, podpira tipkovnico in potege.
- **GSAP ScrollTrigger:** razkritje galerije in pripovedovanje zgodbe v portfoliju (pripete sekcije). **Lenis** samo na javnih straneh; ustavi se, ko je odprt lightbox.
- **Mikro-interakcije:**
  - stekleni gumb se ob pritisku rahlo stisne, odsev se premakne;
  - navigacija se preoblikuje v meni;
  - števci na finančni plošči se animirajo.
- Trajanje 150–400 ms, nič ne blokira vnosa. `prefers-reduced-motion` izklopi GSAP, Lenis in View Transitions.

### Komponente (django-cotton, `templates/cotton/`)
`glass.panel`, `glass.bar`, `button` (primary, glass, quiet, danger), `field` (label, napaka, pomoč), `select`, `segmented`, `modal`, `sheet` (mobilno), `popover`, `badge.status`, `photo` (`<picture>` + srcset + LQIP + razmerje), `stat` (števec), `empty`, `icon` (Lucide SVG sprite, 1,5 px črta), `toast`.

---

## 8. Jezik in lokalizacija

- `LANGUAGE_CODE = "sl"`, `LANGUAGES = [sl, en]` (angleščina skrita, dokler ni prevedena), `LocaleMiddleware`, `TIME_ZONE = "Europe/Ljubljana"`, `USE_TZ = True`.
- Nizi v kodi so angleški (`gettext`), slovenščina je v `locale/sl/LC_MESSAGES/django.po`. To je standardni Djangov postopek, ki omogoča kasnejšo angleščino brez prepisovanja kode.
- **Slovenščina ima 4 množinske oblike** (1 fotografija, 2 fotografiji, 3 fotografije, 5 fotografij), zato povsod uporabljamo `ngettext` oziroma `{% blocktranslate count %}`.
- `FORMAT_MODULE_PATH`: datum `j. n. Y`, datum in čas `j. n. Y, H:i`, `FIRST_DAY_OF_WEEK = 1`, decimalna vejica, pika za tisočice. Filter `|eur` izpiše `1.234,56 €`.
- **CSV za slovenski Excel:** ločilo `;`, decimalna vejica, UTF-8 BOM, da se šumniki pravilno prikažejo.
- FullCalendar (`locale: sl`, `firstDay: 1`), ApexCharts in PhotoSwipe dobijo slovenske nize.
- URL poti so slovenske (`/koledar/`, `/stranke/`, `/g/<token>/`, `/p/<slug>/`). Jezik galerije se nastavi na galerijo, kar pride prav za tuje poročne pare, ko bo dodana angleščina.

---

## 9. Struktura map

```
aperture_studio/
├── compose.yaml
├── Dockerfile                  # python:3.13-slim-trixie + libvips, exiftool, pango (WeasyPrint), gettext
├── .env.example
├── pyproject.toml              # uv, ruff, pytest
├── uv.lock
├── manage.py
├── README.md
├── docs/NACRT.md
├── config/
│   ├── settings/{base,dev,test,prod}.py
│   ├── formats/sl/formats.py
│   ├── urls.py  celery.py  wsgi.py  asgi.py
├── apps/
│   ├── core/  accounts/  clients/  shoots/  scheduling/
│   ├── photos/  galleries/  portfolio/  finance/
│   │   └── (vsaka: models.py, views.py, urls.py, forms.py, admin.py,
│   │        services.py, tasks.py, templates/<app>/, tests/)
├── templates/
│   ├── base.html
│   ├── layouts/{app,public,gallery,auth}.html
│   └── cotton/                 # komponente design systema
├── static/
│   ├── css/src/{app.css,tokens.css,glass.css,themes/*.css}
│   ├── js/{glass,uploader,calendar,gallery,portfolio,counters,csrf}.js
│   ├── vendor/                 # pripete ESM knjižnice + manifest s SHA-384
│   └── fonts/
├── locale/sl/LC_MESSAGES/
└── seed/                       # predpomnjene demo fotografije (v .gitignore)
```

Ime aplikacije je v eni konstanti `APP_NAME` (settings, privzeto „Aperture Studio“, lahko iz `.env`), v predloge pride prek context processorja.

---

## 10. Testi in kakovost

- **Orodja:** pytest-django, factory_boy, pytest-xdist, testna baza Postgres v Compose (`docker compose run --rm web pytest`), ruff (lint in format).
- **Izolacija najemnikov:** en parametriziran test gre čez vse URL-je s parametri in preveri, da uporabnik studia B za objekte studia A dobi 404. Posebej testiram, da obrazci ne ponujajo tujih strank in lokacij.
- **Dostop do galerije:** pravilen in napačen žeton, neobjavljena in potekla galerija, geslo, menjava gesla razveljavi sejo, rate limit vrne 429, original samo kadar je dovoljen, potek podpisanega URL-ja.
- **Cevovod:** testna JPEG slika z GPS, Adobe RGB in usmeritvijo 6. Pričakovano: izpeljanka je v sRGB in pravilno zasukana, GPS ni ne v originalu ne v izpeljankah, AVIF enkoder obstaja.
- **Finance:**
  - ponavljajoči stroški: dvakratni zagon ne ustvari dvojnikov, zamujeni meseci se dohitijo, 31. 1. se preslika v 28. 2.;
  - zaporedne številke računov ob hkratnem izdajanju;
  - predlogi prihodkov.
- **ICS:** veljaven vir, časovni pas, zamenjava žetona razveljavi star URL.
- **N+1:** `django_assert_max_num_queries` na seznamih in galerijah (plus django-zeal v dev, če je vzdrževan).
- **Playwright:** posnetki zaslona pri 390×844 (telefon) in 1440×900, temni in svetli način, po vsaki fazi. Preverim jih glede na smernice oblikovanja (tudi s skillom `apple-design`). Če Node ne bo na voljo, je rezerva Python Playwright, ki ima vgrajen driver.
- **Seed:** `manage.py seed_demo` se razširi v vsaki fazi:
  - demo fotograf, stranke s slovenskimi imeni (Faker `sl_SI`) in lokacije (Ljubljana, Bled, Piran, Logarska dolina);
  - paketi, posnetki čez 12 mesecev, galerije in stroški (vključno z ponavljajočimi naročninami);
  - fotografije s picsum.photos (licenca Unsplash) gredo skozi pravi cevovod; brez interneta se uporabijo generirane.

---

## 11. Faze

Po vsaki fazi: testi in ruff, Playwright posnetki novih strani, kritičen pregled, popravki, povzetek, nato **čakam na tvoj „naprej“**. Vsaka faza ima svojo git vejo (`faza-1-skelet` …), ki jo po potrditvi združim v `main`.

**Faza 1: skelet in design system**
- git, uv, Dockerfile, Compose (7 storitev), nastavitve in env, Celery, `User` + `Studio` + registracija (email + Google), plasti za najemnike, i18n in formati.
- Postavitve strani, tokeni, `glass.css`, cotton komponente, pripete JS knjižnice + importmap.
- **Stran stilov `/stil/`** (samo DEBUG ali osebje), oblikovani prijava in registracija.
- Testna infrastruktura in orodje za test izolacije, README (osnova), `.env.example`, `seed_demo` (uporabnik in studio).
- *Posnetki:* stran stilov (temno in svetlo, telefon in namizje), steklo nad tremi vrstami fotografij, prijava.

**Faza 2: stranke, fotografiranja, koledar**
- Stranke: CRUD, profil s časovnico (posnetki, galerije, plačila), iskanje s HTMX.
- Lokacije, paketi, posnetki s statusnim tokom.
- FullCalendar: mesec, teden, dan, seznam; premikanje in raztezanje (PATCH); ustvarjanje z izbiro obsega; stekleni popover; barve po vrsti; poskusni dogodki črtkani.
- Samodejni roki za obdelavo in dostavo, ICS vir, nadzorna plošča z gradnikom „naslednjih 7 dni“.

**Faza 3a: upload in urejanje galerij (stran fotografa)**
- Razsekan upload in uploader, zasebna shramba, `process_photo`, manifest, LQIP, svetlost, stanje obdelave.
- Urejevalnik galerije: sekcije (razvrščanje z vlečenjem), naslovnica, nastavitve (geslo, rok, tema, prenosi, vodni žig), deljenje (kopiraj povezavo, pošlji stranki po e-pošti).

**Faza 3b: galerija za stranke (glavni izdelek, največ oblikovalskega dela)**
- 4 teme, naslovnica, poravnana mreža, masonry in postavitev fotoknjige, PhotoSwipe, globoka povezava na posamezno fotografijo.
- Priljubljene in komentarji (obiskovalec vpiše ime in email ob prvem ♥).
- Prenos posamezne fotografije in ZIP v ozadju z e-poštnim obvestilom; strani za geslo in potek.
- Analitika za fotografa: ogledi, izbori po obiskovalcu, prenosi, **izvoz imen datotek za filter v Lightroomu**.
- View Transitions, GSAP razkritje.
- Najbolj temeljit pregled posnetkov na telefonu.

**Faza 4: javni portfolio in povpraševanja**
- `/p/<slug>/`: kategorije, zgodbe iz izbranih fotografij galerij, o meni, Lenis in pripovedovanje z drsenjem.
- Povpraševalni obrazec ustvari stranko, posnetek (povpraševanje), poskusni dogodek in e-pošto.

**Faza 5: finance**
- Prihodki (s predlogi iz plačanih posnetkov), stroški z računi za stroške, kategorije, ponavljajoči stroški (beat).
- Plošča z ApexCharts: mesečno prihodki proti stroškom, dobiček, kategorije, primerjava z lanskim letom, najboljše stranke, animirani števci.
- Filtri, CSV, račun v PDF (WeasyPrint, nastavljiv DDV).

**Faza 6: dodelava**
- Revizija dostopnosti (axe prek Playwrighta, tipkovnica, fokus, kontrast na steklu), dodelava gibanja.
- Zmogljivost (Lighthouse na galeriji na telefonu).
- `security-review` in `code-review`, polni testi, končni README (R2, Google OAuth, SMTP, produkcija).

---

## 12. Delitev dela

- **Sam (Claude):** arhitektura, plast najemnikov, dostop do galerij, podpisani URL-ji, upload in jedro cevovoda, design system in komponente, galerija za stranke, pregled vsega dela delavca.
- **Delavec (Antigravity):** CRUD obrazci, viewi in predloge po vzorcu, ko prvi primer obstaja; admin; factoryji; testi po mojem seznamu primerov; `seed_demo`; README in dokumentacija; izpolnjevanje `.po` prevodov.
- Pred vsako nalogo delavca ustvarim vejo, po njej pregledam `git diff`.

---

## 13. Izven obsega in tveganja

- **Davčno potrjevanje računov (FURS)** za gotovinska in kartična plačila ni vključeno. Račun je generičen, kot zahteva specifikacija.
- Neposreden upload v R2, člani ekipe, lastne domene za portfolio in spletna plačila so možni kasneje.
- RAW datoteke se ne obdelujejo (sprejmemo JPEG, PNG, TIFF, HEIC, WebP); fotografi dostavljajo JPEG.
- Hitrost AVIF: glej razdelek 6.
- FullCalendar: v 2. fazi preverim, ali je v7 stabilen; sicer v6.
