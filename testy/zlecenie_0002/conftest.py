"""Pomocnicze fixture testów zlecenia 0002 (poprawki narzędzia rejestrów).

Kopia pomocników z testów zlecenia 0001 (bez importu między katalogami) uzupełniona
o odczyt drzewa plików i obiektu JSON.

SZKIC AI — do pracy autora.

Kod zlecenia (`fabruna.rejestry`) jest importowany wyłącznie wewnątrz fixture,
żeby plik dał się zebrać bez kodu. Wszystkie dane są fikcyjne.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import pytest

NAGLOWEK_M = [
    "id", "mozliwosc", "obszar", "zrodlo", "data_zrodla", "kotwica", "stare_studio",
    "dowod_stare_studio", "poziom_waznosci", "test_odbioru", "kandydaci", "status", "partia", "uwagi",
]
NAGLOWEK_K = [
    "id", "nazwa", "rodzaj", "mozliwosci", "zrodlo", "data_zrodla", "poprzedni_werdykt", "data_werdyktu",
    "stan_dzis", "koszt", "ryzyko", "dowod", "poziom_waznosci", "poziom_dostepu", "wspolgranie", "werdykt",
    "status", "partia", "uwagi",
]
NAGLOWKI = {"mozliwosci": NAGLOWEK_M, "kandydaci": NAGLOWEK_K}

WZOR_BLEDU = re.compile(r"^(?P<plik>.+):(?P<wiersz>\d+): (?P<kolumna>[^:]+): (?P<opis>.+)$")


class Narzedzia:
    """Budowanie plików wejściowych, uruchamianie `main(argv)` w procesie i odczyt wyników."""

    NAGLOWEK_M = NAGLOWEK_M
    NAGLOWEK_K = NAGLOWEK_K
    WZOR_BLEDU = WZOR_BLEDU

    def __init__(self, katalog: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self.katalog = katalog
        self.capsys = capsys

    # --- wiersze danych -------------------------------------------------------------
    @staticmethod
    def wiersz_m(**zmiany: str) -> dict[str, str]:
        wiersz = {
            "id": "M-0001",
            "mozliwosc": "Codzienne podsumowanie poczty",
            "obszar": "asystent codzienny",
            "zrodlo": "notatka testowa A",
            "data_zrodla": "2026-01-15",
            "kotwica": "",
            "stare_studio": "nie",
            "dowod_stare_studio": "",
            "poziom_waznosci": "",
            "test_odbioru": "",
            "kandydaci": "",
            "status": "zebrane",
            "partia": "P1",
            "uwagi": "",
        }
        nieznane = set(zmiany) - set(wiersz)
        assert not nieznane, f"nieznane kolumny w teście: {nieznane}"
        wiersz.update(zmiany)
        return wiersz

    @staticmethod
    def wiersz_k(**zmiany: str) -> dict[str, str]:
        wiersz = {
            "id": "K-0001",
            "nazwa": "Notatnik",
            "rodzaj": "narzędzie",
            "mozliwosci": "",
            "zrodlo": "notatka testowa B",
            "data_zrodla": "2026-01-15",
            "poprzedni_werdykt": "",
            "data_werdyktu": "",
            "stan_dzis": "",
            "koszt": "",
            "ryzyko": "",
            "dowod": "",
            "poziom_waznosci": "",
            "poziom_dostepu": "",
            "wspolgranie": "",
            "werdykt": "",
            "status": "zebrane",
            "partia": "P1",
            "uwagi": "",
        }
        nieznane = set(zmiany) - set(wiersz)
        assert not nieznane, f"nieznane kolumny w teście: {nieznane}"
        wiersz.update(zmiany)
        return wiersz

    def wiersze_m(self, ile: int, start: int = 1) -> list[dict[str, str]]:
        """`ile` poprawnych, różnych wierszy możliwości o kolejnych identyfikatorach."""
        return [
            self.wiersz_m(id=f"M-{start + i:04d}", mozliwosc=f"Możliwość testowa numer {start + i}")
            for i in range(ile)
        ]

    # --- pliki ------------------------------------------------------------------------
    def zapisz(
        self,
        nazwa: str,
        rodzaj: str,
        wiersze: list[dict[str, str]],
        naglowek: list[str] | None = None,
        bom: bool = False,
    ) -> str:
        """Zapisuje plik wejściowy (cytowanie minimalne, średnik, `\\n`) i zwraca ścieżkę jako tekst."""
        naglowek = NAGLOWKI[rodzaj] if naglowek is None else naglowek
        bufor = io.StringIO()
        pisarz = csv.writer(bufor, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        pisarz.writerow(naglowek)
        for wiersz in wiersze:
            pisarz.writerow([wiersz.get(k, "") for k in naglowek])
        tekst = ("﻿" if bom else "") + bufor.getvalue()
        sciezka = self.katalog / nazwa
        sciezka.write_bytes(tekst.encode("utf-8"))
        return str(sciezka)

    def zapisz_tekst(self, nazwa: str, tekst: str) -> str:
        sciezka = self.katalog / nazwa
        sciezka.write_bytes(tekst.encode("utf-8"))
        return str(sciezka)

    @staticmethod
    def format_wyjscia(rodzaj: str, wiersze: list[dict[str, str]]) -> bytes:
        """Oczekiwane bajty pliku wyjściowego: wszystkie pola w cudzysłowach, `\\n`, bez BOM."""
        naglowek = NAGLOWKI[rodzaj]

        def linia(pola: list[str]) -> str:
            return ";".join('"' + p.replace('"', '""') + '"' for p in pola) + "\n"

        tekst = linia(naglowek) + "".join(linia([w[k] for k in naglowek]) for w in wiersze)
        return tekst.encode("utf-8")

    # --- wiersz poleceń w procesie ------------------------------------------------------
    def uruchom(self, *argv: str) -> tuple[int, str, str]:
        from fabruna.rejestry import main

        self.capsys.readouterr()
        kod = main(list(argv))
        wyjscie = self.capsys.readouterr()
        return kod, wyjscie.out, wyjscie.err

    @staticmethod
    def pary(wynik) -> set[tuple[int, str]]:
        """Zbiór par (wiersz, kolumna) z błędów obiektu wyniku."""
        return {(int(b.wiersz), str(b.kolumna)) for b in wynik.bledy}

    @staticmethod
    def pelny(element) -> str:
        """Błąd albo ostrzeżenie w postaci `PLIK:WIERSZ: KOLUMNA: opis`."""
        return f"{element.plik}:{element.wiersz}: {element.kolumna}: {element.opis}"

    def linie_bledow(self, stderr: str) -> list[re.Match[str]]:
        linie = [linia for linia in stderr.splitlines() if linia.strip()]
        dopasowania = [WZOR_BLEDU.match(linia) for linia in linie]
        assert all(dopasowania), f"wiersze stderr poza formatem PLIK:WIERSZ: KOLUMNA: opis: {linie}"
        return dopasowania  # type: ignore[return-value]

    # --- dodatki zlecenia 0002 ------------------------------------------------------------
    def drzewo(self) -> dict[str, bytes]:
        """Wszystkie pliki pod katalogiem testu (ścieżka względna -> bajty); katalogi jako wpis z None."""
        wynik: dict[str, bytes] = {}
        for sciezka in sorted(self.katalog.rglob("*")):
            klucz = str(sciezka.relative_to(self.katalog))
            wynik[klucz] = sciezka.read_bytes() if sciezka.is_file() else None  # type: ignore[assignment]
        return wynik

    @staticmethod
    def jeden_json(stdout: str) -> dict:
        """Standardowe wyjście musi być dokładnie jednym obiektem JSON o polach z interfejsu."""
        obiekt = json.loads(stdout)
        assert isinstance(obiekt, dict)
        assert {"poprawny", "wiersze", "bledy", "ostrzezenia"} <= set(obiekt)
        return obiekt

    @staticmethod
    def klucze(wynik) -> list[tuple[str, int, str]]:
        """Lista trójek (plik, wiersz, kolumna) z błędów obiektu wyniku (z powtórzeniami)."""
        return [(str(b.plik), int(b.wiersz), str(b.kolumna)) for b in wynik.bledy]


@pytest.fixture
def rejestry():
    import fabruna.rejestry as modul

    return modul


@pytest.fixture
def n(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Narzedzia:
    return Narzedzia(tmp_path, capsys)
