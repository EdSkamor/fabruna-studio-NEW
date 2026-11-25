"""Wywołania narzędzi zewnętrznych przez podproces: git, pytest, mutmut, detect-secrets."""

from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

LIMIT_PYTEST_S = 1800
LIMIT_MUTACJI_S = 3600
# Sędzia wyłącza dyrektywy „pragma: allowlist secret”: fałszywy alarm zatwierdza się
# wyłącznie w .secrets.baseline, czyli zmianą typu „zasady”.
FILTR_DYREKTYW = "detect_secrets.filters.allowlist.is_line_allowlisted"
ZNAKI_POSTEPU = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


class BrakNarzedzia(Exception):
    """Wymagane narzędzie nie jest dostępne; krok kończy się wynikiem negatywnym."""


class BladUzycia(Exception):
    """Zły argument albo stan repozytorium, którego nie da się ocenić (kod wyjścia 2)."""


@dataclass
class Przebieg:
    """Jedno uruchomienie pytest: kod wyjścia, wynik każdego testu i tekst wyjścia."""

    kod: int
    wyniki: dict[str, str]
    wyjscie: str


def ogon(tekst: str, ile: int = 10) -> list[str]:
    """Ostatnie niepuste wiersze wyjścia narzędzia, bez wierszy paska postępu."""
    wiersze = [w.strip() for w in re.split(r"[\r\n]+", tekst)]
    return [w for w in wiersze if w and w[0] not in ZNAKI_POSTEPU][-ile:]


def git(korzen: Path, *argumenty: str) -> str:
    if shutil.which("git") is None:
        raise BrakNarzedzia("git")
    proces = subprocess.run(
        ["git", *argumenty], cwd=korzen, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if proces.returncode != 0:
        raise BladUzycia(f"git {' '.join(argumenty)}: {proces.stderr.strip() or proces.returncode}")
    return proces.stdout


def wymagaj(pakiet: str) -> None:
    """Brak narzędzia to wynik negatywny kroku, nigdy ciche pominięcie."""
    if importlib.util.find_spec(pakiet) is None:
        raise BrakNarzedzia(pakiet)


def modul(nazwa: str, argumenty: list[str], katalog: Path, limit_s: int) -> subprocess.CompletedProcess[str]:
    """Uruchamia `python -m nazwa` tym samym interpreterem co sędzia."""
    wymagaj(nazwa.split(".")[0])
    return subprocess.run(
        # -I: bez katalogu bieżącego na ścieżce importu, bez site użytkownika i zmiennych PYTHON*,
        # więc pliki podrzucone przez testy (sitecustomize, usercustomize) nie wpływają na kolejne przebiegi.
        [sys.executable, "-I", "-m", nazwa, *argumenty],
        cwd=katalog,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=limit_s,
    )


def uruchom_pytest(korzen: Path, cele: list[str]) -> Przebieg:
    """Uruchamia pytest i czyta wynik każdego testu z raportu JUnit."""
    with tempfile.TemporaryDirectory(prefix="sedzia-junit-") as tymczasowy:
        raport = Path(tymczasowy) / "junit.xml"
        argumenty = [*cele, "-q", "-p", "no:cacheprovider", f"--junitxml={raport}"]
        proces = modul("pytest", argumenty, korzen, LIMIT_PYTEST_S)
        try:
            przypadki = list(ET.parse(raport).iter("testcase"))
        except (OSError, ET.ParseError):
            przypadki = []
    wyniki: dict[str, str] = {}
    for przypadek in przypadki:
        znaczniki = {element.tag for element in przypadek}
        stan = next((s for s, z in (("error", "error"), ("failed", "failure"), ("skipped", "skipped")) if z in znaczniki), "passed")
        wyniki[f"{przypadek.get('classname')}::{przypadek.get('name')}"] = stan
    return Przebieg(proces.returncode, wyniki, proces.stdout + proces.stderr)


def zbierz_testy(korzen: Path, cel: str) -> tuple[int, list[str], str]:
    """Kod wyjścia `pytest --collect-only`, identyfikatory zebranych testów i tekst wyjścia."""
    proces = modul("pytest", [cel, "--collect-only", "-q", "-p", "no:cacheprovider"], korzen, LIMIT_PYTEST_S)
    testy = [w.strip() for w in proces.stdout.splitlines() if w.startswith(cel) and "::" in w]
    return proces.returncode, testy, proces.stdout + proces.stderr


def nazwa_testu(identyfikator: str) -> str:
    """Nazwa funkcji testu małymi literami, bez ścieżki, klasy i parametrów."""
    return identyfikator.split("::")[-1].split("[")[0].lower()


def skanuj_sekrety(korzen: Path, pliki: list[str]) -> tuple[bool, list[str]]:
    """Czy skan jest czysty oraz znaleziska „plik:wiersz — rodzaj” (treści sekretu nie wypisuje)."""
    znaleziska: list[str] = []
    czysto = True
    with tempfile.TemporaryDirectory(prefix="sedzia-sekrety-") as tymczasowy:
        # Narzędzie potrafi nadpisać plik wzorca, więc dostaje kopię; repozytorium zostaje nietknięte.
        wzorzec = shutil.copyfile(korzen / ".secrets.baseline", Path(tymczasowy) / "wzorzec.json")
        for poczatek in range(0, len(pliki), 200):
            argumenty = ["--baseline", str(wzorzec), "--disable-filter", FILTR_DYREKTYW, *pliki[poczatek : poczatek + 200]]
            proces = modul("detect_secrets.pre_commit_hook", argumenty, korzen, LIMIT_PYTEST_S)
            wyjscie = proces.stdout + proces.stderr
            rodzaj = "?"
            for wiersz in wyjscie.splitlines():
                if wiersz.startswith("Secret Type:"):
                    rodzaj = wiersz.split(":", 1)[1].strip()
                elif wiersz.startswith("Location:"):
                    znaleziska.append(f"{wiersz.split(':', 1)[1].strip()} — {rodzaj}")
            if proces.returncode != 0:
                czysto = False
                if proces.returncode != 1:
                    znaleziska.append(f"detect-secrets zakończył się kodem {proces.returncode}: {' | '.join(ogon(wyjscie, 3))}")
    return czysto, znaleziska
