"""Sprawdzanie i scalanie rejestrów przeglądu (możliwości, kandydaci).

SZKIC AI — do pracy autora.

Konfiguracja formatu (nagłówki, słowniki, reguły pól, opcje CSV i parser
argumentów) jest danymi na poziomie modułu; funkcje niżej tylko je stosują.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import sys
from collections import namedtuple
from dataclasses import dataclass, field

# ---------------------------------------------------------------- format plików

CZYTANIE = {"encoding": "utf-8-sig", "newline": ""}
ZAPIS = {"encoding": "utf-8", "newline": ""}
CSV_CZYTANIE = {"delimiter": ";", "quotechar": '"'}
CSV_ZAPIS = {"delimiter": ";", "quotechar": '"', "quoting": csv.QUOTE_ALL, "lineterminator": "\n"}
TRYB_ZAPISU = "w"

KOLUMNA_PLIKU = "-"
KOLUMNA_ID = "id"
PUSTY = "plik jest pusty, brak nagłówka"
BRAK = "brak wartości w polu wymaganym"
SPOZA_KALENDARZA = "data nie istnieje w kalendarzu"

# ---------------------------------------------------------------- słowniki

OBSZARY = (
    "asystent codzienny", "praca nocna i samodzielna", "pisanie i redakcja", "gra fabularna", "media",
    "kod i gry", "wiedza i notatki", "telefon i nadzór", "bezpieczeństwo i kopie", "sprzęt i system",
    "firma", "dziesiątka", "jakość i testy", "inne",
)
STARE_STUDIO = ("tak", "częściowo", "nie", "nie wiadomo")
STARE_STUDIO_Z_DOWODEM = ("tak", "częściowo")
POZIOMY_WAZNOSCI = ("rdzeń", "pierwszy miesiąc", "później", "odrzucone")
STATUSY = ("zebrane", "scalone", "ocenione")
RODZAJE_KANDYDATA = ("model", "wtyczka", "narzędzie", "system", "metoda", "własny składnik")
DOWODY = ("sprawdzone na PC", "z dokumentacji", "nieznane")
POZIOMY_DOSTEPU = ("tylko Qba", "agent za zgodą", "agent w piaskownicy", "agent z siecią")

# ---------------------------------------------------------------- reguły pól

DATA = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
ID_M = re.compile(r"M-[0-9]{4}")
ID_K = re.compile(r"K-[0-9]{4}")
LISTA_M = re.compile(r"M-[0-9]{4}( *, *M-[0-9]{4})*")
LISTA_K = re.compile(r"K-[0-9]{4}( *, *K-[0-9]{4})*")


def _zawsze(wiersz):
    return True


def _nigdy(wiersz):
    return False


# wymagane: funkcja wiersza mówiąca, czy pole musi być niepuste; od/do: długość w znakach;
# slownik: dozwolone wartości; wzorzec: pełne dopasowanie; data: wartość musi istnieć w kalendarzu.
Regula = namedtuple("Regula", "wymagane od do slownik wzorzec data", defaults=(_nigdy, 0, 10**9, None, None, False))

WYMAGANE = Regula(_zawsze)
DATA_WYMAGANA = Regula(_zawsze, wzorzec=DATA, data=True)

REGULY_M = {
    "id": Regula(_zawsze, wzorzec=ID_M),
    "mozliwosc": Regula(_zawsze, od=10, do=300),
    "obszar": Regula(_zawsze, slownik=OBSZARY),
    "zrodlo": WYMAGANE,
    "data_zrodla": DATA_WYMAGANA,
    "kotwica": Regula(do=120),
    "stare_studio": Regula(_zawsze, slownik=STARE_STUDIO),
    "dowod_stare_studio": Regula(lambda w: w["stare_studio"] in STARE_STUDIO_Z_DOWODEM),
    "poziom_waznosci": Regula(slownik=POZIOMY_WAZNOSCI),
    "kandydaci": Regula(wzorzec=LISTA_K),
    "status": Regula(_zawsze, slownik=STATUSY),
    "partia": WYMAGANE,
}
REGULY_K = {
    "id": Regula(_zawsze, wzorzec=ID_K),
    "nazwa": Regula(_zawsze, od=2, do=120),
    "rodzaj": Regula(_zawsze, slownik=RODZAJE_KANDYDATA),
    "mozliwosci": Regula(wzorzec=LISTA_M),
    "zrodlo": WYMAGANE,
    "data_zrodla": DATA_WYMAGANA,
    "data_werdyktu": Regula(lambda w: w["poprzedni_werdykt"] != "", wzorzec=DATA, data=True),
    "dowod": Regula(slownik=DOWODY),
    "poziom_waznosci": Regula(slownik=POZIOMY_WAZNOSCI),
    "poziom_dostepu": Regula(slownik=POZIOMY_DOSTEPU),
    "status": Regula(_zawsze, slownik=STATUSY),
    "partia": WYMAGANE,
}

# prefiks: początek identyfikatora; klucz: pole porównywane przy ostrzeżeniach o powtórzonej treści;
# reguly_partii: jak reguly, ale z dozwolonym pustym identyfikatorem.
Rodzaj = namedtuple("Rodzaj", "naglowek prefiks klucz reguly reguly_partii")

RODZAJE = {
    "mozliwosci": Rodzaj(
        naglowek=[
            "id", "mozliwosc", "obszar", "zrodlo", "data_zrodla", "kotwica", "stare_studio",
            "dowod_stare_studio", "poziom_waznosci", "test_odbioru", "kandydaci", "status", "partia", "uwagi",
        ],
        prefiks="M-",
        klucz="mozliwosc",
        reguly=REGULY_M,
        reguly_partii={**REGULY_M, "id": Regula(wzorzec=ID_M)},
    ),
    "kandydaci": Rodzaj(
        naglowek=[
            "id", "nazwa", "rodzaj", "mozliwosci", "zrodlo", "data_zrodla", "poprzedni_werdykt", "data_werdyktu",
            "stan_dzis", "koszt", "ryzyko", "dowod", "poziom_waznosci", "poziom_dostepu", "wspolgranie", "werdykt",
            "status", "partia", "uwagi",
        ],
        prefiks="K-",
        klucz="nazwa",
        reguly=REGULY_K,
        reguly_partii={**REGULY_K, "id": Regula(wzorzec=ID_K)},
    ),
}

# ---------------------------------------------------------------- wynik


class Zgloszenie(namedtuple("Zgloszenie", "plik wiersz kolumna opis")):
    """Błąd albo ostrzeżenie; tekstowo `PLIK:WIERSZ: KOLUMNA: opis`."""

    __slots__ = ()

    def __str__(self):
        return f"{self.plik}:{self.wiersz}: {self.kolumna}: {self.opis}"


@dataclass
class Wynik:
    bledy: list = field(default_factory=list)
    ostrzezenia: list = field(default_factory=list)
    wiersze: int = 0

    @property
    def poprawny(self):
        return not self.bledy

    def jako_slownik(self):
        return {
            "poprawny": self.poprawny,
            "wiersze": self.wiersze,
            "bledy": [z._asdict() for z in self.bledy],
            "ostrzezenia": [z._asdict() for z in self.ostrzezenia],
        }


# ---------------------------------------------------------------- sprawdzanie


def _blad_pola(wartosc, regula, wiersz):
    """Opis błędu pola albo None, gdy pole jest poprawne."""
    if not wartosc:
        return BRAK if regula.wymagane(wiersz) else None
    if not regula.od <= len(wartosc) <= regula.do:
        return f"długość {len(wartosc)} znaków, dozwolona od {regula.od} do {regula.do}"
    if regula.slownik and wartosc not in regula.slownik:
        return f"wartość {wartosc!r} spoza słownika {list(regula.slownik)}"
    if regula.wzorzec and not regula.wzorzec.fullmatch(wartosc):
        return f"wartość {wartosc!r} nie pasuje do wzorca {regula.wzorzec.pattern}"
    if regula.data:
        try:
            datetime.date.fromisoformat(wartosc)
        except ValueError:
            return SPOZA_KALENDARZA
    return None


def _wczytaj(sciezka, rodzaj, partia):
    """Czyta i sprawdza jeden plik. Zwraca wynik (bez ostrzeżeń) i listę (plik, numer wiersza, wiersz)."""
    plik = str(sciezka)
    wynik = Wynik()
    pozycje = []
    with open(sciezka, **CZYTANIE) as strumien:
        rekordy = list(csv.reader(strumien, **CSV_CZYTANIE))
    if not rekordy:
        wynik.bledy.append(Zgloszenie(plik, 1, KOLUMNA_PLIKU, PUSTY))
        return wynik, pozycje
    naglowek = rekordy[0]
    wynik.wiersze = len(rekordy) - 1
    if naglowek != rodzaj.naglowek:
        brakujace = [k for k in rodzaj.naglowek if k not in naglowek]
        nadmiarowe = [k for k in naglowek if k not in rodzaj.naglowek]
        opis = f"nagłówek niezgodny ze wzorcem (kolejność albo nazwy); brakujące kolumny {brakujace}, nadmiarowe kolumny {nadmiarowe}"
        wynik.bledy.append(Zgloszenie(plik, 1, KOLUMNA_PLIKU, opis))
        return wynik, pozycje
    reguly = rodzaj.reguly_partii if partia else rodzaj.reguly
    pierwsze = {}
    for numer, pola in enumerate(rekordy[1:], start=2):
        if len(pola) != len(naglowek):
            opis = f"liczba pól {len(pola)} zamiast {len(naglowek)}"
            wynik.bledy.append(Zgloszenie(plik, numer, KOLUMNA_PLIKU, opis))
            continue
        wiersz = dict(zip(naglowek, pola))
        for kolumna, regula in reguly.items():
            opis = _blad_pola(wiersz[kolumna], regula, wiersz)
            if opis:
                wynik.bledy.append(Zgloszenie(plik, numer, kolumna, opis))
        identyfikator = wiersz[KOLUMNA_ID]
        if identyfikator in pierwsze:
            opis = f"powtórzony identyfikator {identyfikator}, pierwsze wystąpienie w wierszu {pierwsze[identyfikator]}"
            wynik.bledy.append(Zgloszenie(plik, numer, KOLUMNA_ID, opis))
        elif identyfikator:
            pierwsze[identyfikator] = numer
        pozycje.append((plik, numer, wiersz))
    return wynik, pozycje


def _ostrzezenia(pozycje, kolumna):
    """Ostrzeżenia o powtórzonej treści pola `kolumna` (małe litery, zwinięte białe znaki, bez końcowej kropki)."""
    widziane = {}
    ostrzezenia = []
    for plik, numer, wiersz in pozycje:
        klucz = tuple(wiersz[kolumna].strip().rstrip(".").casefold().split())
        if klucz in widziane:
            pierwszy_plik, pierwszy_numer = widziane[klucz]
            opis = f"ostrzeżenie — treść powtarza {pierwszy_plik}, wiersz {pierwszy_numer}"
            ostrzezenia.append(Zgloszenie(plik, numer, kolumna, opis))
        else:
            widziane[klucz] = (plik, numer)
    return ostrzezenia


def sprawdz_plik(sciezka, rodzaj, partia=False):
    """Sprawdza jeden plik rejestru. `partia=True` dopuszcza pusty identyfikator."""
    wynik, pozycje = _wczytaj(sciezka, RODZAJE[rodzaj], partia)
    wynik.ostrzezenia = _ostrzezenia(pozycje, RODZAJE[rodzaj].klucz)
    return wynik


def scal_pliki(partie, rodzaj, rejestr=None):
    """Scala istniejący rejestr i partie. Zwraca (wiersze posortowane po identyfikatorze, wynik)."""
    opis_rodzaju = RODZAJE[rodzaj]
    wynik = Wynik()
    po_id = {}
    bez_id = []
    for sciezka in ([rejestr] if rejestr else []) + list(partie):
        czesc, pozycje = _wczytaj(sciezka, opis_rodzaju, True)
        wynik.bledy += czesc.bledy
        for pozycja in pozycje:
            plik, numer, wiersz = pozycja
            identyfikator = wiersz[KOLUMNA_ID]
            if not identyfikator:
                bez_id.append(pozycja)
            elif identyfikator not in po_id:
                po_id[identyfikator] = pozycja
            elif po_id[identyfikator][2] != wiersz:
                pierwszy_plik, pierwszy_numer, _ = po_id[identyfikator]
                opis = f"identyfikator {identyfikator} ma inną treść niż w {pierwszy_plik}, wiersz {pierwszy_numer}"
                wynik.bledy.append(Zgloszenie(plik, numer, KOLUMNA_ID, opis))
    if wynik.bledy:
        return [], wynik
    ostatni = max((int(i.removeprefix(opis_rodzaju.prefiks)) for i in po_id), default=0)
    for pozycja in bez_id:
        ostatni += 1
        pozycja[2][KOLUMNA_ID] = f"{opis_rodzaju.prefiks}{ostatni:04d}"
        po_id[pozycja[2][KOLUMNA_ID]] = pozycja
    kolejne = [po_id[i] for i in sorted(po_id)]
    wynik.ostrzezenia = _ostrzezenia(kolejne, opis_rodzaju.klucz)
    wynik.wiersze = len(kolejne)
    return [pozycja[2] for pozycja in kolejne], wynik


# ---------------------------------------------------------------- wiersz poleceń


def _zakoncz(wynik, argumenty):
    for zgloszenie in wynik.bledy + wynik.ostrzezenia:
        print(zgloszenie, file=sys.stderr)
    if argumenty.json:
        print(json.dumps(wynik.jako_slownik()))
    return 0 if wynik.poprawny else 1


def _sprawdz(argumenty):
    return _zakoncz(sprawdz_plik(argumenty.plik, argumenty.rodzaj, argumenty.partia), argumenty)


def _scal(argumenty):
    wiersze, wynik = scal_pliki(argumenty.partie, argumenty.rodzaj, argumenty.rejestr)
    if wynik.poprawny:
        naglowek = RODZAJE[argumenty.rodzaj].naglowek
        with open(argumenty.wyjscie, TRYB_ZAPISU, **ZAPIS) as strumien:
            pisarz = csv.writer(strumien, **CSV_ZAPIS)
            pisarz.writerow(naglowek)
            pisarz.writerows([w[k] for k in naglowek] for w in wiersze)
    if argumenty.raport:
        with open(argumenty.raport, TRYB_ZAPISU, **ZAPIS) as strumien:
            for zgloszenie in wynik.ostrzezenia:
                print(zgloszenie, file=strumien)
    return _zakoncz(wynik, argumenty)


def main(argv=None):
    """Wejście wiersza poleceń: zwraca kod wyjścia (0, 1, 2) i nigdy nie kończy procesu."""
    try:
        argumenty = PARSER.parse_args(argv)
    except SystemExit as wyjscie:
        return wyjscie.code
    try:
        return argumenty.wykonaj(argumenty)
    except (OSError, UnicodeDecodeError) as blad:
        print(f"błąd wejścia/wyjścia: {blad}", file=sys.stderr)
        return 2


PARSER = argparse.ArgumentParser(prog="python -m fabruna.rejestry", description="Rejestry przeglądu.")
_polecenia = PARSER.add_subparsers(dest="polecenie", required=True)

_parser_sprawdz = _polecenia.add_parser("sprawdz", help="sprawdza jeden plik rejestru")
_parser_sprawdz.add_argument("--rodzaj", required=True, choices=list(RODZAJE))
_parser_sprawdz.add_argument("--partia", action="store_true", help="dopuszcza pusty identyfikator")
_parser_sprawdz.add_argument("--json", action="store_true", help="wynik jako obiekt JSON")
_parser_sprawdz.add_argument("plik")
_parser_sprawdz.set_defaults(wykonaj=_sprawdz)

_parser_scal = _polecenia.add_parser("scal", help="scala partie z istniejącym rejestrem")
_parser_scal.add_argument("--rodzaj", required=True, choices=list(RODZAJE))
_parser_scal.add_argument("--wyjscie", required=True, help="plik wynikowy")
_parser_scal.add_argument("--rejestr", help="istniejący rejestr")
_parser_scal.add_argument("--raport", help="plik tekstowy na ostrzeżenia")
_parser_scal.add_argument("--json", action="store_true", help="wynik jako obiekt JSON")
_parser_scal.add_argument("partie", nargs="*")
_parser_scal.set_defaults(wykonaj=_scal)
