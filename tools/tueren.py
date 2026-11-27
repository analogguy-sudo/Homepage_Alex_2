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
GESCHUETZT = {"index", "404", "admin", "passwort", "impressum", "datenschutz", "bildrechte", "vorschau"}

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


def vorab(s, name, inhalt):
    """Inhalt zwischen <!--name--> und <!--/name--> setzen (Vorab-HTML, das die Seite beim Laden durch ihr eigenes ersetzt)."""
    return setze(s, rf"<!--{name}-->.*?<!--/{name}-->", lambda m: f"<!--{name}-->{inhalt}<!--/{name}-->")


def strecken_links(strecken):
    """Auswahl der Bildstrecken als echte Links – so finden Suchmaschinen jede Bildstrecke auch ohne Sitemap."""
    teile, reise = [], False
    for slug, p in strecken:
        if (p.get("bereich") or "allgemein") != "allgemein" and not reise:
            teile.append('<p class="filters-sub">Reisen &amp; Touren</p>')
            reise = True
        teile.append(f'<a class="chip" href="/{slug}">{html.escape(p["title"])}</a>')
    return "".join(teile)


def strecke_vorab(p, bilder):
    """Titel, Text und Bilder einer Bildstrecke als schlichtes HTML (wird beim Laden durch die gestaltete Strecke ersetzt)."""
    e = lambda x: html.escape(x or "", quote=True)
    teile = [f'<article class="strecke"><div class="strecke-head"><h3>{e(p["title"])}</h3>']
    if p.get("text_de"):
        text = re.sub(r"\s+", " ", p["text_de"]).strip()
        teile.append(f"<p>{e(text)}</p>")
    teile.append("</div>")
    for f in bilder:
        name = f.get("title") or p["title"]
        alt = ", ".join(x for x in (name, f.get("location")) if x)
        unten = " · ".join(x for x in (f.get("location"), f.get("film")) if x)
        teile.append(f'<figure><img src="{e(bild_url(f["storage_path"], 800))}" alt="{e(alt)}" loading="lazy">'
                     f'<figcaption>{e(name)}{(" – " + e(unten)) if unten else ""}</figcaption></figure>')
    teile.append("</article>")
    return "".join(teile)


def tuer_seite(vorlage, slug, titel, beschreibung, tuer, bild=None, galerie=None, vorab_strecke=""):
    a = lambda x: html.escape(x, quote=True)
    url = f"{SEITE}/{slug}"
    s = vorab(vorlage, "strecke", vorab_strecke)
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
    if galerie:   # Bildergalerie für Suchmaschinen (Google-Bildersuche: Titel, Ort, Urheber, Copyright)
        daten = json.dumps(galerie, ensure_ascii=False).replace("</", "<\\/")
        s = setze(s, r"</head>", lambda m: f'<script type="application/ld+json">{daten}</script>\n</head>')   # Funktion statt Text: Backslashes im JSON bleiben unangetastet
    marke = "<!-- Eingangstür, erzeugt von tools/tueren.py – nicht von Hand bearbeiten -->"
    s = setze(s, r'<meta charset="utf-8">', f'<meta charset="utf-8">\n{marke}\n<script>window.TUER={json.dumps(tuer, ensure_ascii=False)}</script>')
    return s


FOTOGRAF = {"@type": "Person", "name": "A.T. Fichter", "url": SEITE + "/"}
# Nutzungsbedingungen der eigenen Fotos: alle Rechte vorbehalten, keine freie Lizenz. Die Seite /bildrechte beschreibt das und nennt
# den Weg für individuelle Anfragen (E-Mail) – deshalb dient sie auch als acquireLicensePage; eine automatische Lizenzvergabe gibt es nicht.
BILDRECHTE = SEITE + "/bildrechte"


def galerie(p, slug, text, bilder):
    """Strukturierte Daten einer Bildstrecke: ImageGallery mit einem ImageObject je Foto."""
    if not bilder:
        return None
    objekte = []
    for f in bilder:
        o = {"@type": "ImageObject", "contentUrl": bild_url(f["storage_path"], 1600), "name": f.get("title") or p["title"],
             "creator": FOTOGRAF, "creditText": "A.T. Fichter", "copyrightNotice": "© A.T. Fichter – Alle Rechte vorbehalten",
             "license": BILDRECHTE, "acquireLicensePage": BILDRECHTE}
        angaben = ", ".join(x for x in (f.get("film"), f.get("camera")) if x)
        if angaben:
            o["caption"] = angaben
        if f.get("location"):
            o["contentLocation"] = {"@type": "Place", "name": f["location"]}
        if f.get("year"):
            o["dateCreated"] = str(f["year"])
        objekte.append(o)
    return {"@context": "https://schema.org", "@type": "ImageGallery", "name": p["title"], "url": f"{SEITE}/{slug}",
            "description": text, "author": FOTOGRAF, "inLanguage": "de", "image": objekte}


def main():
    vorlage = open(os.path.join(WURZEL, "index.html"), encoding="utf-8").read()
    projekte = holen("projects?select=id,title,text_de,kind,bereich,sort&order=sort.asc")
    fotos = holen("photos?select=title,storage_path,strecke_id,location,film,camera,year,sort&order=sort.asc,created_at.desc")
    tueren = []   # (slug, titel, beschreibung, tuer, bild, galerie, vorab)
    for slug, titel, text in ANSICHTEN:
        tueren.append((slug, titel, text, {"v": slug}, None, None, ""))
    strecken = []   # (slug, projekt) – für die Links in der Auswahl
    vergeben = set(GESCHUETZT) | {t[0] for t in tueren}
    for p in projekte:
        if (p.get("kind") or "projekt") != "bildstrecke" or not p.get("title"):
            continue
        slug = kurzname(p["title"])
        if not slug or slug in vergeben:
            print(f"übersprungen (Name schon vergeben): {p['title']}")
            continue
        vergeben.add(slug)
        strecken.append((slug, p))
        eigene = [f for f in fotos if f.get("strecke_id") == p["id"] and f.get("storage_path")]
        erstes = next((f["storage_path"] for f in fotos if f.get("strecke_id") == p["id"] and f.get("storage_path")), None)
        text = kuerzen(p.get("text_de")) or f"{p['title']} – eine Bildstrecke in analoger Fotografie von A.T. Fichter."
        tueren.append((slug, f"{p['title']} – Bildstrecke | Analoge Welt", text, {"v": "bildstrecken", "id": p["id"]}, bild_url(erstes) if erstes else None,
                       galerie(p, slug, text, eigene), strecke_vorab(p, eigene)))

    # die Links stehen auch in index.html selbst (Vorlage und Startseite); nur schreiben, wenn sich etwas ändert
    vorlage = vorab(vorlage, "strecken", strecken_links(strecken))
    start = vorab(vorlage, "strecke", "")
    if start != open(os.path.join(WURZEL, "index.html"), encoding="utf-8").read():
        with open(os.path.join(WURZEL, "index.html"), "w", encoding="utf-8") as f:
            f.write(start)

    for slug, titel, text, tuer, bild, gal, vor in tueren:
        with open(os.path.join(WURZEL, slug + ".html"), "w", encoding="utf-8") as f:
            f.write(tuer_seite(vorlage, slug, titel, text, tuer, bild, gal, vor))

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
    zeilen.append(f"  <url><loc>{BILDRECHTE}</loc><priority>0.3</priority></url>")
    with open(os.path.join(WURZEL, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(zeilen) + "\n</urlset>\n")
    print("Türen:", ", ".join(neu))


if __name__ == "__main__":
    main()
