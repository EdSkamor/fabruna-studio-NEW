"""Reguły usługi sędziego na PC (sedzia/pc/kolejka.py) i parsowanie werdyktu recenzji (sedzia/ci/recenzja.py)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[2]


def _modul(sciezka: str, nazwa: str):
    spec = importlib.util.spec_from_file_location(nazwa, KORZEN / sciezka)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


kolejka = _modul("sedzia/pc/kolejka.py", "kolejka_pc")
recenzja = _modul("sedzia/ci/recenzja.py", "recenzja_ci")

ZERO = "0" * 40


def _raw(*wpisy: tuple[str, str, str, str]) -> str:
    """Format `git diff --raw -z`: „:stary nowy sha sha status\\0ścieżka\\0”."""
    return "".join(f":{stary} {nowy} {ZERO} {ZERO} {status}\0{sciezka}\0" for stary, nowy, status, sciezka in wpisy)


@pytest.mark.parametrize(
    ("nazwa", "oczekiwane"),
    [
        ("testy/0002-poprawki-rejestrow", ("testy", "0002")),
        ("kod/0002-poprawki-rejestrow", ("kod", "0002")),
        ("zasady/automatyczne-scalanie", ("zasady", None)),
        ("main", None),
        ("kod/2-x", None),
        ("kod/0002-Duze", None),
        ("kod/0002-x/../main", None),
        ("testy/0002-", None),
    ],
)
def test_rozpoznanie_galezi(nazwa, oczekiwane):
    assert kolejka.rozpoznaj(nazwa) == oczekiwane


def test_testy_tylko_nowe_pliki_w_katalogu_zlecenia():
    dobre = _raw(("000000", "100644", "A", "testy/zlecenie_0002/test_a.py"))
    assert kolejka.naruszenia("testy", "0002", dobre) == []
    zle = _raw(
        ("100644", "100644", "M", "testy/zlecenie_0002/test_a.py"),
        ("000000", "100644", "A", "testy/zlecenie_0001/test_b.py"),
        ("100644", "000000", "D", "testy/zlecenie_0002/stary.py"),
    )
    assert len(kolejka.naruszenia("testy", "0002", zle)) == 3


def test_kod_tylko_src():
    assert kolejka.naruszenia("kod", "0002", _raw(("100644", "100644", "M", "src/fabruna/rejestry/rdzen.py"))) == []
    for sciezka in ("sedzia/kroki.py", "testy/zlecenie_0002/test_a.py", "pyproject.toml", "AGENTS.md"):
        assert kolejka.naruszenia("kod", "0002", _raw(("100644", "100644", "M", sciezka))), sciezka


def test_github_zawsze_odrzucony_takze_w_zasadach():
    for tryb, numer in (("zasady", None), ("kod", "0002"), ("testy", "0002")):
        assert kolejka.naruszenia(tryb, numer, _raw(("000000", "100644", "A", ".github/workflows/x.yml")))


def test_dowiazania_i_podmoduly_odrzucone():
    assert kolejka.naruszenia("kod", "0002", _raw(("000000", "120000", "A", "src/link")))
    assert kolejka.naruszenia("kod", "0002", _raw(("000000", "160000", "A", "src/pod")))


def test_zasady_bez_kodu_poza_pustymi_init():
    assert kolejka.naruszenia("zasady", None, _raw(("100644", "100644", "M", "sedzia/kroki.py"))) == []
    assert kolejka.naruszenia("zasady", None, _raw(("000000", "100644", "A", "src/fabruna/nowy/__init__.py"))) == []
    assert kolejka.naruszenia("zasady", None, _raw(("100644", "100644", "M", "src/fabruna/rejestry/rdzen.py")))


def test_glowy_pakietu():
    sha = "a" * 40
    assert kolejka.glowy_pakietu(f"{sha} refs/heads/kod/0002-x\n") == [(sha, "refs/heads/kod/0002-x")]
    with pytest.raises(ValueError):
        kolejka.glowy_pakietu("zly wiersz\n")


@pytest.mark.parametrize(
    ("odpowiedz", "oczekiwane"),
    [
        ("Uwagi…\nWERDYKT: PRZYJĘTE", True),
        ("Uwagi…\n**WERDYKT: PRZYJĘTE**\n", True),
        ("Uwagi…\nWERDYKT: ODRZUCONE", False),
        ("WERDYKT: PRZYJĘTE\nale jeszcze coś", None),
        ("WERDYKT: PRZYJĘTE albo ODRZUCONE", None),
        ("", None),
    ],
)
def test_werdykt_recenzji(odpowiedz, oczekiwane):
    assert recenzja.werdykt(odpowiedz) is oczekiwane
