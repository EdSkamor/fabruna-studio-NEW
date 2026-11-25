"""Testy mutacyjne w piaskownicy: mutmut dostaje kopię src/ i testy/ oraz konfigurację od sędziego."""

from __future__ import annotations

import ast
import glob
import json
import re
import shutil
import tempfile
import tomllib
from pathlib import Path

from .narzedzia import LIMIT_MUTACJI_S, BladUzycia, modul, ogon

ILE_ROZNIC = 40  # tylu niezabitym mutantom sędzia dołącza różnicę względem oryginału
# Kod, który wyłącza mutacje albo rozpoznaje, że jest testowany lub mutowany, mógłby zawyżyć wynik.
ZAKAZANE_W_KODZIE = re.compile(r"pragma:\s*no mutate|MUTANT_UNDER_TEST|mutmut|PYTEST_CURRENT_TEST|\bpytest\b")


def wynik_mutacyjny(statystyki: dict[str, int]) -> float | None:
    """Wynik w procentach: (zabite + przekroczony czas) / (wszystkie − pominięte).

    Mutant bez testu, ocalały i podejrzany liczą się do mianownika, czyli obniżają wynik.
    None oznacza brak mutantów do oceny.
    """
    oceniane = statystyki["total"] - statystyki["skipped"]
    if oceniane <= 0:
        return None
    return 100.0 * (statystyki["killed"] + statystyki["timeout"]) / oceniane


def ma_funkcje(katalog: Path) -> bool:
    """Czy w katalogu jest choć jedna funkcja — mutmut mutuje wyłącznie ciała funkcji."""
    for plik in katalog.rglob("*.py"):
        try:
            drzewo = ast.parse(plik.read_bytes(), filename=str(plik))
        except (SyntaxError, ValueError):
            return True  # nie zgadujemy: niech mutmut sam zgłosi błąd
        if any(isinstance(wezel, (ast.FunctionDef, ast.AsyncFunctionDef)) for wezel in ast.walk(drzewo)):
            return True
    return False


def _odwolania(korzen: Path, pliki: list[str]) -> list[str]:
    """Miejsca, w których mutowany kod wyłącza mutacje albo odwołuje się do narzędzi sędziego."""
    miejsca = []
    for sciezka in pliki:
        tekst = (korzen / sciezka).read_text("utf-8", errors="replace")
        miejsca += [f"{sciezka}:{nr}" for nr, wiersz in enumerate(tekst.splitlines(), 1) if ZAKAZANE_W_KODZIE.search(wiersz)]
    return miejsca


def _toml(tabele: dict[str, dict]) -> str:
    """Zapis płaskich tabel TOML (napisy, liczby, wartości logiczne i listy mają tę samą postać co w JSON)."""
    wiersze = []
    for nazwa, pola in tabele.items():
        wiersze.append(f"[{nazwa}]")
        for klucz, wartosc in pola.items():
            if isinstance(wartosc, dict):
                raise BladUzycia(f"pyproject.toml: [{nazwa}] {klucz} — sędzia nie obsługuje zagnieżdżonych tabel")
            wiersze.append(f"{klucz} = {json.dumps(wartosc, ensure_ascii=False)}")
        wiersze.append("")
    return "\n".join(wiersze)


def mutuj(korzen: Path, pliki: list[str] | None, testy: str, prog: float, pyproject: str | None = None) -> tuple[bool, str, dict, list[str]]:
    """Mutuje podane pliki (None = całe src/) i sprawdza je testami `testy`; zwraca (dobrze, opis, liczby, szczegóły)."""
    mutowane = pliki if pliki is not None else [p.relative_to(korzen).as_posix() for p in sorted((korzen / "src").rglob("*.py"))]
    odwolania = _odwolania(korzen, mutowane)
    if odwolania:
        opis = "mutowany kod wyłącza mutacje („pragma: no mutate”) albo odwołuje się do pytest lub mutmut — niedozwolone"
        return False, opis, {"niedozwolone_odwolania": len(odwolania)}, odwolania

    tekst = pyproject if pyproject is not None else (korzen / "pyproject.toml").read_text("utf-8")
    narzedzia = tomllib.loads(tekst).get("tool", {})
    ustawienia = {
        **narzedzia.get("mutmut", {}),
        "source_paths": ["src"],
        "also_copy": ["testy"],
        "pytest_add_cli_args_test_selection": [testy],
    }
    ustawienia.pop("only_mutate", None)
    if pliki is not None:
        ustawienia["only_mutate"] = [glob.escape(p) for p in pliki]
    konfiguracja = _toml({"tool.pytest.ini_options": narzedzia.get("pytest", {}).get("ini_options", {}), "tool.mutmut": ustawienia})

    def pomin(katalog: str, nazwy: list[str]) -> list[str]:
        # testy/sedzia sprawdzają sędziego, nie kod z src/ — do piaskownicy nie trafiają
        return [n for n in nazwy if n == "__pycache__" or (n == "sedzia" and Path(katalog) == korzen / "testy")]

    with tempfile.TemporaryDirectory(prefix="sedzia-mutacje-", ignore_cleanup_errors=True) as tymczasowy:
        piaskownica = Path(tymczasowy)
        shutil.copytree(korzen / "src", piaskownica / "src", ignore=pomin)
        shutil.copytree(korzen / "testy", piaskownica / "testy", ignore=pomin)
        (piaskownica / "pyproject.toml").write_text(konfiguracja, "utf-8")
        przebieg = modul("mutmut", ["run"], piaskownica, LIMIT_MUTACJI_S)
        if przebieg.returncode != 0:
            opis = (
                f"mutmut przerwał pracę (kod {przebieg.returncode}): testy nie wykonują żadnej zmutowanej funkcji "
                "w tym samym procesie, w zmienionych plikach nie ma funkcji albo testy nie przechodzą w piaskownicy "
                "(kopia samych src/ i testy/)"
            )
            return False, opis, {"wszystkie": 0}, ogon(przebieg.stdout + przebieg.stderr, 8)
        modul("mutmut", ["export-cicd-stats"], piaskownica, LIMIT_MUTACJI_S)
        plik = piaskownica / "mutants" / "mutmut-cicd-stats.json"
        if not plik.is_file():
            return False, "mutmut nie zapisał statystyk — brak mutantów do oceny", {"wszystkie": 0}, []
        statystyki = json.loads(plik.read_text("utf-8"))
        wyniki = modul("mutmut", ["results"], piaskownica, LIMIT_MUTACJI_S).stdout
        niezabite = [w.strip() for w in wyniki.splitlines() if ": " in w]
        for numer, wiersz in enumerate(niezabite[:ILE_ROZNIC]):
            pokaz = modul("mutmut", ["show", wiersz.rsplit(": ", 1)[0]], piaskownica, LIMIT_MUTACJI_S)
            if pokaz.returncode == 0:  # pierwszy wiersz to nagłówek „# nazwa: stan”, dalej różnica
                niezabite[numer] = "\n".join([wiersz, *pokaz.stdout.strip().splitlines()[1:]])

    liczby = {
        "wszystkie": statystyki["total"],
        "zabite": statystyki["killed"],
        "przekroczony_czas": statystyki["timeout"],
        "ocalale": statystyki["survived"],
        "bez_testu": statystyki["no_tests"],
        "pominiete": statystyki["skipped"],
        "podejrzane": statystyki["suspicious"] + statystyki["segfault"],
        "prog_proc": prog,
    }
    wynik = wynik_mutacyjny(statystyki)
    if wynik is None:
        return False, "brak mutantów do oceny w mutowanych plikach", liczby, []
    liczby["wynik_proc"] = round(wynik, 1)
    porownanie = "≥" if wynik >= prog else "<"
    procent = f"{wynik:.1f}".replace(".", ",")
    opis = (
        f"wynik mutacyjny {procent}% {porownanie} próg {prog:g}% — zabite {liczby['zabite']}, "
        f"przekroczony czas {liczby['przekroczony_czas']}, ocalałe {liczby['ocalale']}, bez testu {liczby['bez_testu']}, "
        f"pominięte {liczby['pominiete']}, wszystkie {liczby['wszystkie']}; testy: {testy}"
    )
    return wynik >= prog, opis, liczby, niezabite
