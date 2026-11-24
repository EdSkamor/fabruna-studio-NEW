"""Zlecenie 0001 — K12 (kody wyjścia i JSON), K13 (bez zależności zewnętrznych), testy przez podproces.

SZKIC AI — do pracy autora.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

KLUCZE_JSON = {"poprawny", "wiersze", "bledy", "ostrzezenia"}
KLUCZE_ELEMENTU = {"plik", "wiersz", "kolumna", "opis"}


# ---------------------------------------------------------------- K12 — kody wyjścia i JSON


def test_k12_sprawdz_kod_0_dla_poprawnych_danych(n):
    plik = n.zapisz("ok.csv", "mozliwosci", n.wiersze_m(3))
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", plik)
    assert kod == 0
    assert err.strip() == ""


def test_k12_sprawdz_kod_1_dla_bledow_danych(n):
    plik = n.zapisz("zle.csv", "kandydaci", [n.wiersz_k(rodzaj="silnik")])
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "kandydaci", plik)
    assert kod == 1
    assert [(d["plik"], d["wiersz"], d["kolumna"]) for d in n.linie_bledow(err)] == [(plik, "2", "rodzaj")]


def test_k12_nieistniejacy_plik_kod_2(n):
    brak = str(n.katalog / "nie_ma_takiego.csv")
    assert n.uruchom("sprawdz", "--rodzaj", "mozliwosci", brak)[0] == 2
    assert n.uruchom("sprawdz", "--rodzaj", "mozliwosci", "--json", brak)[0] == 2
    wyjscie = n.katalog / "wynik.csv"
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), brak)[0] == 2
    assert not wyjscie.exists()
    ok = n.zapisz("ok.csv", "mozliwosci", [n.wiersz_m()])
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), ok, brak)[0] == 2
    assert not wyjscie.exists()
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--rejestr", brak, ok)[0] == 2
    assert not wyjscie.exists()


@pytest.mark.parametrize("rodzaj", ["inne", "Mozliwosci", "kandydat", "możliwości", ""])
def test_k12_nieznany_rodzaj_kod_2(n, rodzaj):
    plik = n.zapisz("ok.csv", "mozliwosci", [n.wiersz_m()])
    assert n.uruchom("sprawdz", "--rodzaj", rodzaj, plik)[0] == 2
    assert n.uruchom("scal", "--rodzaj", rodzaj, "--wyjscie", str(n.katalog / "w.csv"), plik)[0] == 2
    assert not (n.katalog / "w.csv").exists()


@pytest.mark.parametrize("argv", [
    [],
    ["nieznane_polecenie"],
    ["sprawdz"],
    ["sprawdz", "--rodzaj", "mozliwosci"],
    ["sprawdz", "PLIK"],
    ["sprawdz", "--rodzaj", "mozliwosci", "--nieznana-opcja", "PLIK"],
    ["scal", "--rodzaj", "mozliwosci", "PLIK"],
    ["scal", "--wyjscie", "W", "PLIK"],
])
def test_k12_bledy_uzycia_kod_2_bez_konczenia_procesu(n, argv):
    plik = n.zapisz("ok.csv", "mozliwosci", [n.wiersz_m()])
    argumenty = [plik if a == "PLIK" else str(n.katalog / "w.csv") if a == "W" else a for a in argv]
    assert n.uruchom(*argumenty)[0] == 2


def test_k12_main_zwraca_liczbe(n):
    plik = n.zapisz("ok.csv", "mozliwosci", [n.wiersz_m()])
    kod = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", plik)[0]
    assert type(kod) is int


def test_k12_json_przy_poprawnych_danych(n):
    plik = n.zapisz("ok.csv", "kandydaci", [n.wiersz_k(id="K-0001"), n.wiersz_k(id="K-0002", nazwa="Drugi"), n.wiersz_k(id="K-0003", nazwa="Trzeci")])
    kod, out, _ = n.uruchom("sprawdz", "--rodzaj", "kandydaci", "--json", plik)
    assert kod == 0
    dane = json.loads(out)
    assert set(dane) == KLUCZE_JSON
    assert dane["poprawny"] is True
    assert type(dane["wiersze"]) is int and dane["wiersze"] == 3
    assert dane["bledy"] == []
    assert dane["ostrzezenia"] == []


def test_k12_json_przy_bledach_danych(n):
    wiersze = n.wiersze_m(4)
    wiersze[1]["obszar"] = "Media"
    wiersze[3]["data_zrodla"] = "2026-02-30"
    wiersze[3]["status"] = ""
    plik = n.zapisz("zle.csv", "mozliwosci", wiersze)
    kod, out, _ = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", "--json", plik)
    assert kod == 1
    dane = json.loads(out)
    assert set(dane) == KLUCZE_JSON
    assert dane["poprawny"] is False
    assert dane["wiersze"] == 4
    assert dane["ostrzezenia"] == []
    for blad in dane["bledy"]:
        assert set(blad) == KLUCZE_ELEMENTU
        assert type(blad["wiersz"]) is int
        assert blad["plik"] == plik
        assert isinstance(blad["opis"], str) and blad["opis"]
    assert {(b["wiersz"], b["kolumna"]) for b in dane["bledy"]} == {(3, "obszar"), (5, "data_zrodla"), (5, "status")}


def test_k12_json_przy_bledzie_naglowka(n):
    plik = n.zapisz("nagl.csv", "mozliwosci", [n.wiersz_m()], naglowek=n.NAGLOWEK_M[:-1])
    kod, out, _ = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", "--json", plik)
    assert kod == 1
    dane = json.loads(out)
    assert set(dane) == KLUCZE_JSON
    assert dane["poprawny"] is False
    assert any(b["wiersz"] == 1 and b["kolumna"] == "-" and "uwagi" in b["opis"] for b in dane["bledy"])


def test_k12_json_scal(n):
    a = n.zapisz("a.csv", "mozliwosci", [n.wiersz_m(id=""), n.wiersz_m(id="M-0004", mozliwosc="Czwarta możliwość")])
    wyjscie = n.katalog / "wynik.csv"
    kod, out, _ = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--json", a)
    assert kod == 0
    dane = json.loads(out)
    assert set(dane) == KLUCZE_JSON
    assert dane["poprawny"] is True
    assert dane["wiersze"] == 2
    assert dane["bledy"] == []

    b = n.zapisz("b.csv", "mozliwosci", [n.wiersz_m(id="M-0004", mozliwosc="Czwarta, ale inna treść")])
    wyjscie2 = n.katalog / "wynik2.csv"
    kod, out, _ = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie2), "--json", a, b)
    assert kod == 1
    dane = json.loads(out)
    assert set(dane) == KLUCZE_JSON
    assert dane["poprawny"] is False
    assert len(dane["bledy"]) == 1
    assert set(dane["bledy"][0]) == KLUCZE_ELEMENTU
    assert not wyjscie2.exists()


def test_k12_wynik_biblioteczny(n, rejestry):
    plik = n.zapisz("zle.csv", "mozliwosci", [n.wiersz_m(stare_studio="może")])
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is False
    assert len(wynik.bledy) == 1
    blad = wynik.bledy[0]
    assert (str(blad.plik), int(blad.wiersz), blad.kolumna) == (plik, 2, "stare_studio")
    assert list(wynik.ostrzezenia) == []


# ---------------------------------------------------------------- testy przez podproces (sprawdz, scal)


def _python_m(srodowisko, katalog, *argv):
    return subprocess.run(
        [sys.executable, "-m", "fabruna.rejestry", *argv],
        env=srodowisko, capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )


def test_k12_podproces_sprawdz(n, srodowisko_podprocesu):
    dobry = n.zapisz("dobry.csv", "mozliwosci", n.wiersze_m(2))
    zly = n.zapisz("zly.csv", "mozliwosci", [n.wiersz_m(id="M-01")])
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "sprawdz", "--rodzaj", "mozliwosci", dobry)
    assert wynik.returncode == 0, wynik.stderr
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "sprawdz", "--rodzaj", "mozliwosci", zly)
    assert wynik.returncode == 1
    linie = [linia for linia in wynik.stderr.splitlines() if linia.strip()]
    assert len(linie) == 1 and linie[0].startswith(f"{zly}:2: id: ")
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "sprawdz", "--rodzaj", "mozliwosci", "--json", zly)
    assert wynik.returncode == 1
    assert json.loads(wynik.stdout)["poprawny"] is False
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "sprawdz", "--rodzaj", "nieznany", dobry)
    assert wynik.returncode == 2
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "sprawdz", "--rodzaj", "mozliwosci", str(n.katalog / "brak.csv"))
    assert wynik.returncode == 2


def test_k09_podproces_scal(n, srodowisko_podprocesu):
    r = n.zapisz("rejestr.csv", "mozliwosci", [n.wiersz_m(id="M-0002", mozliwosc="Z rejestru, numer dwa")], bom=True)
    p = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m(id="", mozliwosc='Nowa; z "cudzysłowem"', partia="P2")])
    wyjscie = n.katalog / "wynik.csv"
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--rejestr", r, p)
    assert wynik.returncode == 0, wynik.stderr
    assert wyjscie.read_bytes() == n.format_wyjscia("mozliwosci", [
        n.wiersz_m(id="M-0002", mozliwosc="Z rejestru, numer dwa"),
        n.wiersz_m(id="M-0003", mozliwosc='Nowa; z "cudzysłowem"', partia="P2"),
    ])
    konflikt = n.zapisz("konflikt.csv", "mozliwosci", [n.wiersz_m(id="M-0002", mozliwosc="Inna treść dla numeru dwa")])
    wyjscie2 = n.katalog / "wynik2.csv"
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie2), "--rejestr", r, konflikt)
    assert wynik.returncode == 1
    assert not wyjscie2.exists()
    wynik = _python_m(srodowisko_podprocesu, n.katalog, "scal", "--rodzaj", "zle", "--wyjscie", str(wyjscie2), p)
    assert wynik.returncode == 2


# ---------------------------------------------------------------- K13 — bez zależności zewnętrznych


def _moduly_importowane(plik: Path) -> list[str]:
    drzewo = ast.parse(plik.read_text("utf-8"), filename=str(plik))
    moduly = []
    for wezel in ast.walk(drzewo):
        if isinstance(wezel, ast.Import):
            moduly += [alias.name for alias in wezel.names]
        elif isinstance(wezel, ast.ImportFrom) and wezel.level == 0 and wezel.module:
            moduly.append(wezel.module)
        elif isinstance(wezel, ast.Call) and getattr(wezel.func, "attr", getattr(wezel.func, "id", "")) in ("import_module", "__import__"):
            moduly.append("<import dynamiczny>")
    return moduly


def test_k13_tylko_biblioteka_standardowa_i_wlasny_pakiet(katalog_src):
    katalog = katalog_src / "fabruna" / "rejestry"
    assert (katalog / "__init__.py").is_file()
    assert (katalog / "__main__.py").is_file()
    pliki = sorted(katalog.rglob("*.py"))
    obce = []
    for plik in pliki:
        for modul in _moduly_importowane(plik):
            korzen = modul.split(".")[0]
            if korzen != "fabruna" and korzen not in sys.stdlib_module_names:
                obce.append(f"{plik.relative_to(katalog_src)}: {modul}")
    assert obce == []


def test_k13_wykrywanie_importow_dziala(tmp_path):
    # kontrola samego sprawdzenia: moduł spoza biblioteki standardowej jest rozpoznany
    plik = tmp_path / "proba.py"
    plik.write_text("import os\nfrom fabruna import x\nimport requests\nfrom yaml import load\nfrom . import y\n", "utf-8")
    moduly = _moduly_importowane(plik)
    obce = [m for m in moduly if m.split(".")[0] != "fabruna" and m.split(".")[0] not in sys.stdlib_module_names]
    assert obce == ["requests", "yaml"]
    from fabruna.rejestry import main  # noqa: F401  (pakiet musi istnieć)
