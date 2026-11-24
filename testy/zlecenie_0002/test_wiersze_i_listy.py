"""Zlecenie 0002 — K07 (puste wiersze na końcu pliku) i K08 (spacje w listach identyfikatorów).

SZKIC AI — do pracy autora.

Dane są fikcyjne.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------- K07 — puste wiersze na końcu


def _z_pustymi_na_koncu(n, nazwa: str, rodzaj: str, wiersze, ile_pustych: int) -> str:
    sciezka = n.zapisz(nazwa, rodzaj, wiersze)
    with open(sciezka, "ab") as plik:
        plik.write(b"\n" * ile_pustych)
    return sciezka


@pytest.mark.parametrize("ile_pustych", [1, 3])
def test_k07_puste_wiersze_na_koncu_sprawdz(n, ile_pustych):
    plik = _z_pustymi_na_koncu(n, "plik.csv", "mozliwosci", n.wiersze_m(2), ile_pustych)
    kod, out, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", "--json", plik)
    assert kod == 0, err
    obiekt = n.jeden_json(out)
    assert obiekt["poprawny"] is True
    assert obiekt["wiersze"] == 2
    assert obiekt["bledy"] == []


def test_k07_puste_wiersze_na_koncu_biblioteka(n, rejestry):
    plik = _z_pustymi_na_koncu(n, "plik.csv", "kandydaci", [n.wiersz_k()], 2)
    wynik = rejestry.sprawdz_plik(plik, "kandydaci", partia=True)
    assert wynik.poprawny is True
    assert wynik.wiersze == 1


def test_k07_sam_naglowek_i_puste_wiersze(n):
    plik = _z_pustymi_na_koncu(n, "plik.csv", "kandydaci", [], 2)
    kod, out, _err = n.uruchom("sprawdz", "--rodzaj", "kandydaci", "--json", plik)
    assert kod == 0
    obiekt = n.jeden_json(out)
    assert obiekt["poprawny"] is True
    assert obiekt["wiersze"] == 0


def test_k07_scal_pomija_puste_wiersze_na_koncu(n):
    wiersze_a = n.wiersze_m(2)
    wiersze_b = n.wiersze_m(1, start=3)
    partia_a = _z_pustymi_na_koncu(n, "a.csv", "mozliwosci", wiersze_a, 2)
    partia_b = _z_pustymi_na_koncu(n, "b.csv", "mozliwosci", wiersze_b, 1)
    wyjscie = n.katalog / "wyjscie.csv"
    kod, out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--json", partia_a, partia_b)
    assert kod == 0, err
    assert n.jeden_json(out)["wiersze"] == 3
    assert wyjscie.read_bytes() == n.format_wyjscia("mozliwosci", wiersze_a + wiersze_b)


def test_k07_scal_rejestr_z_pustymi_na_koncu(n, rejestry):
    rejestr = _z_pustymi_na_koncu(n, "rejestr.csv", "mozliwosci", n.wiersze_m(1), 2)
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m(id="", mozliwosc="Nowa możliwość z partii")])
    wiersze, wynik = rejestry.scal_pliki([partia], "mozliwosci", rejestr=rejestr)
    assert wynik.poprawny is True
    assert [w["id"] for w in wiersze] == ["M-0001", "M-0002"]


def test_k07_pusty_wiersz_w_srodku_to_blad(n, rejestry):
    pierwszy, drugi = n.wiersze_m(2)
    sciezka = n.zapisz("plik.csv", "mozliwosci", [pierwszy])
    reszta = n.katalog / "reszta.csv"
    n.zapisz("reszta.csv", "mozliwosci", [drugi])
    linie_reszty = reszta.read_bytes().split(b"\n", 1)[1]
    with open(sciezka, "ab") as plik:
        plik.write(b"\n" + linie_reszty + b"\n")
    reszta.unlink()
    wynik = rejestry.sprawdz_plik(sciezka, "mozliwosci")
    assert wynik.poprawny is False
    assert n.pary(wynik) == {(3, "-")}


# ---------------------------------------------------------------- K08 — spacje w listach


LISTY_K = ["K-0001, K-0002", "K-0001 ,K-0002", "K-0001 , K-0002", "K-0001,  K-0002,K-0003"]
LISTY_M = ["M-0001, M-0002", "M-0001 ,M-0002", "M-0001 , M-0002", "M-0001,  M-0002,M-0003"]


@pytest.mark.parametrize("lista", LISTY_K)
def test_k08_spacje_w_kandydatach(n, rejestry, lista):
    plik = n.zapisz("plik.csv", "mozliwosci", [n.wiersz_m(kandydaci=lista)])
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.bledy == []


@pytest.mark.parametrize("lista", LISTY_M)
def test_k08_spacje_w_mozliwosciach(n, rejestry, lista):
    plik = n.zapisz("plik.csv", "kandydaci", [n.wiersz_k(mozliwosci=lista)])
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert wynik.bledy == []


@pytest.mark.parametrize(
    ("rodzaj", "kolumna", "lista"),
    [
        ("mozliwosci", "kandydaci", "K-0001, ,K-0002"),
        ("mozliwosci", "kandydaci", "K-0001 , , K-0002"),
        ("kandydaci", "mozliwosci", "M-0001, ,M-0002"),
        ("kandydaci", "mozliwosci", "M-0001,,M-0002"),
    ],
)
def test_k08_pusty_element_ze_spacjami_to_blad(n, rejestry, rodzaj, kolumna, lista):
    wiersz = n.wiersz_m(kandydaci=lista) if rodzaj == "mozliwosci" else n.wiersz_k(mozliwosci=lista)
    plik = n.zapisz("plik.csv", rodzaj, [wiersz])
    wynik = rejestry.sprawdz_plik(plik, rodzaj)
    assert n.pary(wynik) == {(2, kolumna)}


def test_k08_scal_przenosi_listy_ze_spacjami(n):
    wiersz_m = n.wiersz_m(kandydaci="K-0001 , K-0002")
    wiersz_k = n.wiersz_k(mozliwosci="M-0001,  M-0002")
    partia_m = n.zapisz("m.csv", "mozliwosci", [wiersz_m])
    partia_k = n.zapisz("k.csv", "kandydaci", [wiersz_k])
    wyj_m = n.katalog / "wyj_m.csv"
    wyj_k = n.katalog / "wyj_k.csv"
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyj_m), partia_m)[0] == 0
    assert n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyj_k), partia_k)[0] == 0
    assert wyj_m.read_bytes() == n.format_wyjscia("mozliwosci", [wiersz_m])
    assert wyj_k.read_bytes() == n.format_wyjscia("kandydaci", [wiersz_k])
