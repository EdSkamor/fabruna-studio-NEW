"""Pomocnicze fixture testów zlecenia 0003 (zapis wyjścia i stan procesu).

SZKIC AI — do pracy autora.

Kod zlecenia (`fabruna.rejestry`) jest importowany wyłącznie wewnątrz fixture i metod,
żeby plik dał się zebrać bez kodu. Wszystkie dane są fikcyjne.
"""

from __future__ import annotations

import csv
import errno
import io
import os
from pathlib import Path

import pytest

NAGLOWEK_M = [
    "id", "mozliwosc", "obszar", "zrodlo", "data_zrodla", "kotwica", "stare_studio",
    "dowod_stare_studio", "poziom_waznosci", "test_odbioru", "kandydaci", "status", "partia", "uwagi",
]


class Narzedzia:
    """Pliki wejściowe, uruchamianie `main(argv)` w procesie, oczekiwane bajty wyjścia."""

    def __init__(self, katalog: Path, capsys: pytest.CaptureFixture[str]) -> None:
        self.katalog = katalog
        self.capsys = capsys

    @staticmethod
    def wiersz_m(**zmiany: str) -> dict[str, str]:
        wiersz = {
            "id": "M-0001", "mozliwosc": "Codzienne podsumowanie poczty", "obszar": "asystent codzienny",
            "zrodlo": "notatka testowa A", "data_zrodla": "2026-01-15", "kotwica": "", "stare_studio": "nie",
            "dowod_stare_studio": "", "poziom_waznosci": "", "test_odbioru": "", "kandydaci": "",
            "status": "zebrane", "partia": "P1", "uwagi": "",
        }
        wiersz.update(zmiany)
        return wiersz

    def wiersze(self) -> list[dict[str, str]]:
        """Dwa poprawne, różne wiersze (bez ostrzeżeń o powtórzonej treści)."""
        return [
            self.wiersz_m(id="M-0001", mozliwosc="Pierwsza możliwość testowa"),
            self.wiersz_m(id="M-0002", mozliwosc="Druga możliwość testowa"),
        ]

    def zapisz(self, nazwa: str, wiersze: list[dict[str, str]]) -> str:
        bufor = io.StringIO()
        pisarz = csv.writer(bufor, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
        pisarz.writerow(NAGLOWEK_M)
        for wiersz in wiersze:
            pisarz.writerow([wiersz[k] for k in NAGLOWEK_M])
        sciezka = self.katalog / nazwa
        sciezka.parent.mkdir(parents=True, exist_ok=True)
        sciezka.write_bytes(bufor.getvalue().encode("utf-8"))
        return str(sciezka)

    @staticmethod
    def format_wyjscia(wiersze: list[dict[str, str]]) -> bytes:
        def linia(pola: list[str]) -> str:
            return ";".join('"' + p.replace('"', '""') + '"' for p in pola) + "\n"

        return (linia(NAGLOWEK_M) + "".join(linia([w[k] for k in NAGLOWEK_M]) for w in wiersze)).encode("utf-8")

    def uruchom(self, *argv: str) -> tuple[int, str, str]:
        from fabruna.rejestry import main

        self.capsys.readouterr()
        kod = main(list(argv))
        wyjscie = self.capsys.readouterr()
        return kod, wyjscie.out, wyjscie.err

    @staticmethod
    def nazwy(katalog: Path) -> set[str]:
        return {p.name for p in katalog.iterdir()}


class AwariaPodmiany:
    """Zastępca `os.replace`: pierwsza podmiana na ścieżkę o nazwie `nazwa` zgłasza OSError.

    Pozostałe wywołania (także późniejsze z tą samą nazwą, na przykład przy wycofaniu) idą
    do prawdziwego `os.replace`.
    """

    def __init__(self, nazwa: str, prawdziwa) -> None:
        self.nazwa = nazwa
        self.prawdziwa = prawdziwa
        self.zgloszona = False

    def __call__(self, zrodlo, cel, *args, **kwargs):
        if not self.zgloszona and os.path.basename(os.fspath(cel)) == self.nazwa:
            self.zgloszona = True
            raise OSError(errno.EIO, "symulowana awaria podmiany")
        return self.prawdziwa(zrodlo, cel, *args, **kwargs)


@pytest.fixture
def rejestry():
    import fabruna.rejestry as modul

    return modul


@pytest.fixture
def n(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> Narzedzia:
    return Narzedzia(tmp_path, capsys)


@pytest.fixture
def awaria_podmiany(monkeypatch: pytest.MonkeyPatch):
    """Fabryka: `awaria_podmiany("nazwa.csv")` podmienia `os.replace` i zwraca zastępcę."""

    def ustaw(nazwa: str) -> AwariaPodmiany:
        zastepca = AwariaPodmiany(nazwa, os.replace)
        monkeypatch.setattr(os, "replace", zastepca)
        return zastepca

    return ustaw


@pytest.fixture
def umaska():
    """Ustala maskę 0o022 na czas testu i przywraca poprzednią."""
    poprzednia = os.umask(0o022)
    try:
        yield 0o022
    finally:
        os.umask(poprzednia)


@pytest.fixture
def limit_csv():
    """Przywraca `csv.field_size_limit` sprzed testu, niezależnie od tego, co zrobił kod."""
    poprzedni = csv.field_size_limit()
    try:
        yield
    finally:
        csv.field_size_limit(poprzedni)
