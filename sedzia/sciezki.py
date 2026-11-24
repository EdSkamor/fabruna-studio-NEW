"""Ochrona ścieżek: co wolno zmienić na gałęzi danego rodzaju."""

from __future__ import annotations

import re
from pathlib import Path

from .narzedzia import git

_OPIS = r"[a-z0-9][a-z0-9-]*"
WZORCE_GALEZI = {
    "testy": rf"testy/(\d{{4}})-{_OPIS}",
    "kod": rf"kod/(\d{{4}})-{_OPIS}",
    "zasady": rf"zasady/{_OPIS}",
}
KATALOGI_ZASAD = ("sedzia/", "testy/", ".github/", "dokumentacja/", "zlecenia/")
PLIKI_ZASAD = ("AGENTS.md", "pyproject.toml", "README.md", ".gitignore", ".secrets.baseline")
DOZWOLONE = {
    "testy": "tylko nowe pliki w testy/zlecenie_{zlecenie}/",
    "kod": "tylko src/",
    "zasady": "sedzia/, testy/, .github/, dokumentacja/, zlecenia/, AGENTS.md, pyproject.toml, README.md, "
    ".gitignore, .secrets.baseline oraz puste src/**/__init__.py",
}


def rozpoznaj_galaz(nazwa: str) -> tuple[str, str | None] | None:
    """Tryb sędziego i numer zlecenia z nazwy gałęzi; `main` to tryb „calosc”; None — nazwa spoza konwencji."""
    if nazwa == "main":
        return "calosc", None
    for tryb, wzorzec in WZORCE_GALEZI.items():
        dopasowanie = re.fullmatch(wzorzec, nazwa)
        if dopasowanie:
            return tryb, (dopasowanie.group(1) if dopasowanie.groups() else None)
    return None


def zmienione(korzen: Path, baza: str) -> dict[str, list[str]]:
    """Ścieżka → źródła zmiany: commity względem bazy, zmiany niezatwierdzone, pliki nieśledzone."""
    zrodla = (
        ("commit", ("diff", "--name-only", "--no-renames", "-z", f"{baza}...HEAD")),
        ("zmiana niezatwierdzona", ("diff", "--name-only", "--no-renames", "-z", "HEAD")),
        ("plik nieśledzony", ("ls-files", "--others", "--exclude-standard", "-z")),
    )
    wynik: dict[str, list[str]] = {}
    for etykieta, polecenie in zrodla:
        for sciezka in git(korzen, *polecenie).split("\0"):
            if sciezka:
                wynik.setdefault(sciezka, []).append(etykieta)
    return dict(sorted(wynik.items()))


def naruszenie(tryb: str, zlecenie: str | None, sciezka: str, korzen: Path, pliki_bazy: set[str]) -> str | None:
    """Powód, dla którego zmiana tej ścieżki jest niedozwolona w danym trybie, albo None."""
    if tryb == "testy":
        if not sciezka.startswith(f"testy/zlecenie_{zlecenie}/"):
            return f"poza testy/zlecenie_{zlecenie}/"
        if sciezka in pliki_bazy:
            return "zmiana albo usunięcie istniejącego pliku testów (wymaga zmiany typu „zasady”)"
        return None
    if tryb == "kod":
        return None if sciezka.startswith("src/") else "poza src/"
    if sciezka.startswith(KATALOGI_ZASAD) or sciezka in PLIKI_ZASAD:
        return None
    plik = korzen / sciezka
    if sciezka.startswith("src/") and plik.name == "__init__.py" and plik.is_file() and not plik.read_bytes().strip():
        return None  # pusty znacznik pakietu nie wnosi kodu, więc nie omija bramek trybu „kod”
    return "poza ścieżkami zasad (kod wchodzi wyłącznie gałęzią kod/NNNN-opis)"
