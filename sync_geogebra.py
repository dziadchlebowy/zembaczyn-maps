#!/usr/bin/env python3
"""Pobiera projekt z GeoGebry, wyciąga z niego geogebra.xml i zapisuje go obok index.html.

Użycie:  python sync_geogebra.py [ID_PROJEKTU]
Zmienne: GGB_ID (domyślnie ywqqqkgs), GGB_BASES (opcjonalnie, adresy do testów, rozdzielone spacją)
Kod wyjścia: 0 = plik zaktualizowany lub bez zmian, 1 = nie udało się pobrać.
"""
import io, json, os, sys, urllib.request, zipfile

GGB_ID = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get('GGB_ID', 'ywqqqkgs')).strip()
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'geogebra.xml')
UA = {'User-Agent': 'Mozilla/5.0 (compatible; zembaczyn-sync/1.0)'}


def get(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def xml_from_ggb(blob):
    if not zipfile.is_zipfile(io.BytesIO(blob)):
        return None
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if 'geogebra.xml' not in z.namelist():
            return None
        xml = z.read('geogebra.xml')
    return xml if b'<construction' in xml else None


def candidates():
    bases = os.environ.get('GGB_BASES', '').split()
    if bases:  # tryb testowy
        yield from (b.format(id=GGB_ID) for b in bases)
        return
    # 1) bezpośrednie pobranie pliku .ggb
    yield f'https://www.geogebra.org/material/download/format/file/id/{GGB_ID}'
    # 2) przez API: szukamy w odpowiedzi adresu pliku
    try:
        meta = json.loads(get(f'https://api.geogebra.org/v1.0/materials/{GGB_ID}?scope=extended'))
    except Exception as e:
        print(f'  API: {e}')
        return
    def walk(o):
        if isinstance(o, dict):
            for v in o.values(): yield from walk(v)
        elif isinstance(o, list):
            for v in o: yield from walk(v)
        elif isinstance(o, str) and o.startswith('http') and ('.ggb' in o or 'download' in o):
            yield o
    yield from walk(meta)


def main():
    print(f'Projekt GeoGebry: {GGB_ID}')
    xml = None
    for url in candidates():
        print(f'Próbuję: {url}')
        try:
            xml = xml_from_ggb(get(url))
        except Exception as e:
            print(f'  błąd: {e}')
            continue
        if xml:
            print('  OK – znaleziono geogebra.xml')
            break
        print('  to nie jest poprawny plik .ggb')
    if not xml:
        print('NIE UDAŁO SIĘ pobrać projektu. Sprawdź, czy jest publiczny/opublikowany i czy ID jest poprawne.')
        return 1
    old = open(OUT, 'rb').read() if os.path.exists(OUT) else None
    if old == xml:
        print('geogebra.xml bez zmian.')
        return 0
    open(OUT, 'wb').write(xml)
    print(f'Zapisano {OUT} ({len(xml)} B).')
    return 0


if __name__ == '__main__':
    sys.exit(main())
