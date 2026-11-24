"""Sędzia pętli inżynierskiej: wydaje wyrok dla gałęzi i zapisuje go w wyrok.json.

Kody wyjścia: 0 — wyrok pozytywny, 1 — wyrok negatywny, 2 — błąd użycia albo błąd wewnętrzny.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import traceback
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

from .kroki import NEGATYWNY, POZYTYWNY, Kontekst, Krok, plik_zlecenia, wykonaj
from .narzedzia import BladUzycia, BrakNarzedzia, git
from .sciezki import rozpoznaj_galaz, zmienione

ZNAK = {POZYTYWNY: "[+]", NEGATYWNY: "[-]"}


def _numer(tekst: str) -> str:
    if not re.fullmatch(r"\d{4}", tekst):
        raise argparse.ArgumentTypeError("numer zlecenia to cztery cyfry, na przykład 0001")
    return tekst


def _parser() -> argparse.ArgumentParser:
    wyrok = argparse.ArgumentParser(add_help=False)
    wyrok.add_argument("--wyrok", default="wyrok.json", help="plik wyroku (domyślnie wyrok.json w katalogu repozytorium)")
    zlecenie = argparse.ArgumentParser(add_help=False)
    zlecenie.add_argument("--zlecenie", required=True, type=_numer, metavar="NNNN", help="numer zlecenia")
    baza = argparse.ArgumentParser(add_help=False)
    baza.add_argument("--baza", required=True, metavar="REF", help="gałąź albo commit, względem którego liczone są zmiany")
    prog = argparse.ArgumentParser(add_help=False)
    prog.add_argument("--prog-mutacji", type=float, default=70.0, metavar="PROCENT", help="minimalny wynik mutacyjny (domyślnie 70)")

    parser = argparse.ArgumentParser(prog="python -m sedzia", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    tryby = parser.add_subparsers(dest="tryb", required=True, metavar="TRYB")
    tryby.add_parser("testy", parents=[zlecenie, baza, wyrok], help="gałąź testy/NNNN-opis: autor testów oddał testy, kodu jeszcze nie ma")
    tryby.add_parser("kod", parents=[zlecenie, baza, prog, wyrok], help="gałąź kod/NNNN-opis: wykonawca oddał kod")
    tryby.add_parser("zasady", parents=[baza, wyrok], help="gałąź zasady/opis: zmiana sędziego, testów, zleceń, dokumentacji")
    calosc = tryby.add_parser("calosc", parents=[prog, wyrok], help="stan całego repozytorium (main, przebieg nocny)")
    calosc.add_argument("--mutacje", action="store_true", help="dodatkowo testy mutacyjne całego src/")
    galaz = tryby.add_parser("galaz", parents=[prog, wyrok], help="tryb i numer zlecenia wyznaczone z nazwy gałęzi (dla CI)")
    galaz.add_argument("nazwa", help="nazwa gałęzi, na przykład kod/0001-narzedzie-rejestrow albo main")
    galaz.add_argument("--baza", metavar="REF", help="wymagana dla każdej gałęzi poza main")
    return parser


def _przygotuj(argumenty: argparse.Namespace) -> tuple[Kontekst, list[Krok]]:
    """Buduje kontekst wyroku; druga wartość to kroki rozstrzygnięte już na wstępie (nieznany rodzaj gałęzi)."""
    korzen = Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    plik = korzen / argumenty.wyrok
    plik.unlink(missing_ok=True)  # stary wyrok nie może uchodzić za wynik tego przebiegu
    k = Kontekst(
        korzen=korzen,
        tryb=argumenty.tryb,
        plik_wyroku=plik,
        zlecenie=getattr(argumenty, "zlecenie", None),
        baza=getattr(argumenty, "baza", None),
        prog=getattr(argumenty, "prog_mutacji", 70.0),
        z_mutacjami=getattr(argumenty, "mutacje", False),
    )
    lokalna = git(korzen, "rev-parse", "--abbrev-ref", "HEAD").strip()
    k.galaz = None if lokalna == "HEAD" else lokalna
    if argumenty.tryb == "galaz":
        k.galaz = argumenty.nazwa
        rozpoznana = rozpoznaj_galaz(argumenty.nazwa)
        if rozpoznana is None:
            opis = f"gałąź „{argumenty.nazwa}” nie pasuje do żadnego rodzaju: testy/NNNN-opis, kod/NNNN-opis, zasady/opis"
            return k, [Krok("rodzaj_galezi", NEGATYWNY, opis)]
        k.tryb, k.zlecenie = rozpoznana
    if k.tryb != "calosc":
        if not k.baza or k.baza.startswith("-"):
            raise BladUzycia("podaj --baza REF (gałąź albo commit)")
        k.baza_commit = git(korzen, "merge-base", k.baza, "HEAD").strip()
        k.zmiany = zmienione(korzen, k.baza)
    if k.zlecenie:
        plik_zlecenia(k)
    return k, []


def _wersje() -> dict[str, str]:
    wersje = {"python": sys.version.split()[0]}
    for pakiet in ("pytest", "mutmut", "detect-secrets"):
        try:
            wersje[pakiet] = metadata.version(pakiet)
        except metadata.PackageNotFoundError:
            wersje[pakiet] = "brak"
    return wersje


def _oglos(k: Kontekst, kroki: list[Krok], czas_s: float) -> bool:
    """Zapisuje wyrok.json, wypisuje podsumowanie i zwraca, czy wyrok jest pozytywny."""
    pozytywny = bool(kroki) and all(krok.wynik == POZYTYWNY for krok in kroki)
    try:
        head = git(k.korzen, "rev-parse", "HEAD").strip()
        czyste = not git(k.korzen, "status", "--porcelain").strip()
    except (BladUzycia, BrakNarzedzia):
        head, czyste = None, None
    wyrok = {
        "wyrok": POZYTYWNY if pozytywny else NEGATYWNY,
        "tryb": k.tryb,
        "zlecenie": k.zlecenie,
        "baza": k.baza,
        "baza_commit": k.baza_commit,
        "head": head,
        "drzewo_czyste": czyste,
        "galaz": k.galaz,
        "narzedzia": _wersje(),
        "czas_s": round(czas_s, 1),
        "kroki": [asdict(krok) for krok in kroki],
    }
    k.plik_wyroku.write_text(json.dumps(wyrok, ensure_ascii=False, indent=2) + "\n", "utf-8")
    drzewo = "czyste" if czyste else "ze zmianami niezatwierdzonymi"
    print(f"Sędzia — tryb: {k.tryb}, zlecenie: {k.zlecenie or '—'}, baza: {k.baza or '—'}, gałąź: {k.galaz or 'HEAD odłączony'}, drzewo robocze: {drzewo}")
    for krok in kroki:
        print(f"  {ZNAK.get(krok.wynik, '[ ]')} {krok.nazwa} — {krok.opis}")
        for wiersz in krok.szczegoly:
            print(f"        {wiersz}")
    print(f"WYROK: {'POZYTYWNY' if pozytywny else 'NEGATYWNY'} (czas {czas_s:.0f} s, zapis: {k.plik_wyroku})")
    return pozytywny


def main(argv: list[str] | None = None) -> int:
    for strumien in (sys.stdout, sys.stderr):
        strumien.reconfigure(encoding="utf-8", errors="replace")
    argumenty = _parser().parse_args(argv)
    start = time.monotonic()
    try:
        try:
            k, kroki = _przygotuj(argumenty)
        except BrakNarzedzia as blad:
            k = Kontekst(korzen=Path.cwd(), tryb=argumenty.tryb, plik_wyroku=Path.cwd() / argumenty.wyrok)
            kroki = [Krok("narzedzia", NEGATYWNY, f"brak wymaganego narzędzia: {blad}")]
        pozytywny = _oglos(k, kroki or wykonaj(k), time.monotonic() - start)
    except BladUzycia as blad:
        print(f"Błąd użycia: {blad}", file=sys.stderr)
        return 2
    except Exception:  # noqa: BLE001 — każdy nieprzewidziany błąd to kod 2, nigdy wyrok pozytywny
        print("Błąd wewnętrzny sędziego:", file=sys.stderr)
        traceback.print_exc()
        return 2
    return 0 if pozytywny else 1


if __name__ == "__main__":
    sys.exit(main())
