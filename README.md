# Analog-Portfolio – Einrichtung

## 1. Supabase vorbereiten

**Tabelle anlegen** (Supabase → SQL Editor → New query → ausführen):

```sql
create table public.photos (
  id           bigint generated always as identity primary key,
  title        text not null,
  storage_path text not null,   -- Dateiname im Bucket, z. B. 'abendlicht.jpg'
  film         text,            -- z. B. 'Kodak Portra 400'
  camera       text,            -- z. B. 'Leica M6'
  format       text,            -- z. B. '35 mm' oder '120'
  year         int,
  location     text,
  sort         int default 0,   -- kleinere Zahl = weiter vorne
  created_at   timestamptz default now()
);

alter table public.photos enable row level security;

-- Besucher dürfen lesen, aber nicht schreiben:
create policy "Fotos sind öffentlich lesbar"
  on public.photos for select
  using (true);
```

**Bucket anlegen:** Storage → New bucket → Name `photos` → **Public bucket** aktivieren.
Dann deine Scans hochladen (JPG, am besten ca. 2000 px lange Kante, unter 1 MB pro Bild).

**Fotos eintragen:** Table Editor → `photos` → Insert row. Bei `storage_path` kommt der
Dateiname aus dem Bucket (z. B. `abendlicht.jpg`).

## 2. Zugangsdaten einsetzen

Supabase → Project Settings → API. Kopiere die **Project URL** und den **anon public** Key
in den Block `CONFIG` oben im Script von `index.html`.

Der anon-Key darf öffentlich im Code stehen, weil die Row-Level-Security-Regel nur Lesen erlaubt.
Den `service_role`-Key trägst du niemals in die Seite ein.

## 3. Auf GitHub veröffentlichen

1. Neues Repository anlegen und `index.html` hochladen.
2. Repository → Settings → Pages → Branch `main`, Ordner `/ (root)` → Save.
3. Nach ca. einer Minute ist die Seite unter `https://DEIN-NAME.github.io/REPO-NAME/` erreichbar.

## 4. Anpassen

- Name, Texte, Kameras, E-Mail und Instagram direkt im HTML ändern.
- Farben stehen oben im CSS unter `:root`.
- Als deutsche Website brauchst du eine `impressum.html` und eine `datenschutz.html`
  (die Links im Footer zeigen bereits darauf).
