#!/usr/bin/env python3
"""Eingangstüren für analogewelt.com erzeugen.

Für jede Ansicht (Bildstrecken, Leuchttisch, Über mich) und jede Bildstrecke aus dem Admin entsteht eine
Kopie von index.html mit eigenem Titel, eigener Beschreibung und eigenem Vorschaubild, z. B. andalusien.html.
GitHub Pages liefert sie unter https://analogewelt.com/andalusien aus. Ein kleines Skript in der Kopie
(window.TUER) sagt der Seite, was sie aufschlagen soll. Dazu wird sitemap.xml neu geschrieben.

Läuft automatisch über .github/workflows/tueren.yml (täglich und nach jeder Änderung an index.html);
von Hand: python3 tools/tueren.py
"""
import html, json, os, re, sys, unicodedata, urllib.request

WURZEL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEITE = "https://analogewelt.com"
SB_URL = "https://owbbsnujnkhyyqvagtai.supabase.co"
SB_KEY = "sb_publishable_29TK9hJ-e8e4eW9rp_eA8A__EHL2Kga"   # öffentlicher Schlüssel (steht auch in index.html)
BUCKET = "photos"
LISTE = os.path.join(WURZEL, "tools", "tueren.json")       # welche Türen zuletzt erzeugt wurden (zum Aufräumen)
GESCHUETZT = {"index", "404", "admin", "passwort", "impressum", "datenschutz", "vorschau"}

ANSICHTEN = [
    ("bildstrecken", "Bildstrecken – Analoge Welt", "Bildstrecken in analoger Fotografie: Menschen, Städte, Landschaften und Reisen – auf Film fotografiert und von Hand entwickelt."),
    ("leuchttisch", "Leuchttisch – Analoge Welt", "Meine liebsten Bilder auf dem Leuchttisch: analoge Fotografie auf 35 mm und Mittelformat, schwarzweiß und in Farbe."),
    ("ueber-mich", "Über mich – Analoge Welt", "Wer hinter Analoge Welt steckt: A.T. Fichter, analoge Fotografie seit über zehn Jahren – Kameras, Filme und Kontakt."),
]


def holen(pfad):
    req = urllib.request.Request(f"{SB_URL}/rest/v1/{pfad}", headers={"apikey": SB_KEY})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def kurzname(text):
    t = text.lower().replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def kuerzen(text, n=155):
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= n:
        return text
    return text[: n - 1].rsplit(" ", 1)[0].rstrip(",;:–-") + " …"


def bild_url(pfad, breite=1200):
    teile = "/".join(urllib.request.quote(x) for x in pfad.split("/"))
    return f"{SB_URL}/storage/v1/render/image/public/{BUCKET}/{teile}?width={breite}&height={breite * 3}&resize=contain&quality=80"


def setze(s, muster, ersatz):
    neu, n = re.subn(muster, ersatz, s, count=1)
    if n != 1:
        sys.exit(f"Stelle nicht gefunden: {muster}")
    return neu


def tuer_seite(vorlage, slug, titel, beschreibung, tuer, bild=None):
    a = lambda x: html.escape(x, quote=True)
    url = f"{SEITE}/{slug}"
    s = vorlage
    s = setze(s, r"<title>[^<]*</title>", f"<title>{a(titel)}</title>")
    s = setze(s, r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{a(beschreibung)}">')
    s = setze(s, r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{url}">')
    s = setze(s, r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{a(titel)}">')
    s = setze(s, r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{a(beschreibung)}">')
    s = setze(s, r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{url}">')
    if bild:
        s = setze(s, r'<meta property="og:image" content="[^"]*">', f'<meta property="og:image" content="{a(bild)}">')
        s = setze(s, r'<meta name="twitter:image" content="[^"]*">', f'<meta name="twitter:image" content="{a(bild)}">')
        s = re.sub(r'\s*<meta property="og:image:(width|height|alt)" content="[^"]*">', "", s)
    marke = "<!-- Eingangstür, erzeugt von tools/tueren.py – nicht von Hand bearbeiten -->"
    s = setze(s, r'<meta charset="utf-8">', f'<meta charset="utf-8">\n{marke}\n<script>window.TUER={json.dumps(tuer, ensure_ascii=False)}</script>')
    return s


def main():
    vorlage = open(os.path.join(WURZEL, "index.html"), encoding="utf-8").read()
    projekte = holen("projects?select=id,title,text_de,kind,sort&order=sort.asc")
    fotos = holen("photos?select=storage_path,strecke_id,sort&order=sort.asc,created_at.desc")
    tueren = []   # (slug, titel, beschreibung, tuer, bild)
    for slug, titel, text in ANSICHTEN:
        tueren.append((slug, titel, text, {"v": slug}, None))
    vergeben = set(GESCHUETZT) | {t[0] for t in tueren}
    for p in projekte:
        if (p.get("kind") or "projekt") != "bildstrecke" or not p.get("title"):
            continue
        slug = kurzname(p["title"])
        if not slug or slug in vergeben:
            print(f"übersprungen (Name schon vergeben): {p['title']}")
            continue
        vergeben.add(slug)
        erstes = next((f["storage_path"] for f in fotos if f.get("strecke_id") == p["id"] and f.get("storage_path")), None)
        text = kuerzen(p.get("text_de")) or f"{p['title']} – eine Bildstrecke in analoger Fotografie von A.T. Fichter."
        tueren.append((slug, f"{p['title']} – Bildstrecke | Analoge Welt", text, {"v": "bildstrecken", "id": p["id"]}, bild_url(erstes) if erstes else None))

    for slug, titel, text, tuer, bild in tueren:
        with open(os.path.join(WURZEL, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(tuer_seite(vorlage, slug, titel, text, tuer, bild))

    # Türen, deren Bildstrecke es nicht mehr gibt, entfernen (nur solche, die dieses Skript selbst angelegt hat)
    alt = json.load(open(LISTE)) if os.path.exists(LISTE) else []
    neu = [t[0] for t in tueren]
    for slug in alt:
        pfad = os.path.join(WURZEL, slug + ".html")
        if slug not in neu and slug not in GESCHUETZT and os.path.exists(pfad) and "erzeugt von tools/tueren.py" in open(pfad, encoding="utf-8").read(2000):
            os.remove(pfad)
            print(f"entfernt: {slug}.html")
    json.dump(neu, open(LISTE, "w"), indent=1)

    # ohne Datum, damit der tägliche Lauf nur dann etwas ändert, wenn sich wirklich etwas geändert hat
    zeilen = [f"  <url><loc>{SEITE}/</loc><changefreq>monthly</changefreq><priority>1.0</priority></url>"]
    zeilen += [f"  <url><loc>{SEITE}/{s}</loc><changefreq>monthly</changefreq><priority>0.8</priority></url>" for s in neu]
    zeilen += [f"  <url><loc>{SEITE}/{s}.html</loc><priority>0.2</priority></url>" for s in ("impressum", "datenschutz")]
    with open(os.path.join(WURZEL, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(zeilen) + "\n</urlset>\n")
    print("Türen:", ", ".join(neu))


if __name__ == "__main__":
    main()
