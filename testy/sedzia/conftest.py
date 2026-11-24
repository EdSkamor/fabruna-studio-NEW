"""Narzędzia testów sędziego: tymczasowe repozytorium git z kopią sędziego i minimalnym projektem."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[2]

ZLECENIE = """\
# Zlecenie 0001 — liczenie (dane fikcyjne do testów sędziego)

## Kryteria odbioru

- **K01 — suma.** Funkcja `suma` zwraca sumę listy liczb; dla pustej listy zero.
- **K02 — średnia.** Funkcja `srednia` zwraca średnią; dla pustej listy zgłasza błąd.
"""


def _srodowisko() -> dict[str, str]:
    """Git niezależny od ustawień użytkownika i od zmiennych odziedziczonych po zewnętrznym repozytorium."""
    srodowisko = {nazwa: wartosc for nazwa, wartosc in os.environ.items() if not nazwa.startswith("GIT_")}
    srodowisko.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_SYSTEM=os.devnull,
        GIT_AUTHOR_NAME="Test sędziego",
        GIT_AUTHOR_EMAIL="test@example.invalid",
        GIT_COMMITTER_NAME="Test sędziego",
        GIT_COMMITTER_EMAIL="test@example.invalid",
    )
    return srodowisko


@dataclass
class Wynik:
    """Wynik uruchomienia sędziego: kod wyjścia, treść wyrok.json (albo None) i tekst wyjścia."""

    kod: int
    wyrok: dict | None
    wyjscie: str

    @property
    def kroki(self) -> dict[str, str]:
        return {krok["nazwa"]: krok["wynik"] for krok in self.wyrok["kroki"]}

    def krok(self, nazwa: str) -> dict:
        return next(krok for krok in self.wyrok["kroki"] if krok["nazwa"] == nazwa)


class Repo:
    """Tymczasowe repozytorium: zapis plików, commity, gałęzie i uruchomienie sędziego podprocesem."""

    def __init__(self, katalog: Path) -> None:
        self.katalog = katalog
        self.srodowisko = _srodowisko()

    def git(self, *argumenty: str) -> bytes:
        proces = subprocess.run(["git", *argumenty], cwd=self.katalog, env=self.srodowisko, check=True, capture_output=True)
        return proces.stdout

    def zapisz(self, sciezka: str, tresc: str = "") -> None:
        plik = self.katalog / sciezka
        plik.parent.mkdir(parents=True, exist_ok=True)
        plik.write_text(tresc, "utf-8")

    def dopisz(self, sciezka: str, tresc: str) -> None:
        plik = self.katalog / sciezka
        self.zapisz(sciezka, (plik.read_text("utf-8") if plik.is_file() else "") + tresc)

    def zatwierdz(self, opis: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", opis)

    def galaz(self, nazwa: str) -> None:
        self.git("switch", "-q", "-c", nazwa)

    def sedzia(self, *argumenty: str, python: str = sys.executable, opcje: tuple[str, ...] = (), srodowisko: dict | None = None) -> Wynik:
        proces = subprocess.run(
            [python, *opcje, "-m", "sedzia", *argumenty],
            cwd=self.katalog,
            env={**self.srodowisko, **(srodowisko or {})},
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=900,
        )
        plik = self.katalog / "wyrok.json"  # sędzia sam usuwa stary wyrok na początku przebiegu
        wyrok = json.loads(plik.read_text("utf-8")) if plik.is_file() else None
        return Wynik(proces.returncode, wyrok, proces.stdout + proces.stderr)


@pytest.fixture(scope="session")
def wzorzec(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Repozytorium wzorcowe: sędzia i konfiguracja skopiowane z tego repozytorium oraz minimalny projekt."""
    katalog = tmp_path_factory.mktemp("wzorzec") / "repo"
    shutil.copytree(KORZEN / "sedzia", katalog / "sedzia", ignore=shutil.ignore_patterns("__pycache__"))
    for nazwa in ("pyproject.toml", ".gitignore", ".secrets.baseline", "testy/conftest.py"):
        (katalog / nazwa).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KORZEN / nazwa, katalog / nazwa)
    repo = Repo(katalog)
    repo.zapisz("src/fabruna/__init__.py")
    repo.zapisz("src/fabruna/stare.py", "def podwoj(liczba):\n    return 2 * liczba\n")
    repo.zapisz("testy/istniejace/test_stare.py", "def test_podwoj():\n    from fabruna.stare import podwoj\n\n    assert podwoj(2) == 4\n")
    repo.zapisz("testy/sedzia/test_atrapa.py", "def test_atrapa():\n    assert True\n")
    repo.zapisz("zlecenia/0001-liczenie.md", ZLECENIE)
    repo.git("init", "-q", "-b", "main")
    repo.zatwierdz("stan początkowy")
    return katalog


@pytest.fixture
def repo(wzorzec: Path, tmp_path: Path) -> Repo:
    shutil.copytree(wzorzec, tmp_path / "repo")
    return Repo(tmp_path / "repo")
