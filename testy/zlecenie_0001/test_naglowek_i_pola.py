"""Zlecenie 0001 — K01 (nagłówek) i K02 (pola wymagane i długości).

SZKIC AI — do pracy autora.
"""

from __future__ import annotations

import json

import pytest

# ---------------------------------------------------------------- K01 — nagłówek


@pytest.mark.parametrize("rodzaj", ["mozliwosci", "kandydaci"])
def test_k01_sam_poprawny_naglowek_jest_poprawny_i_ma_zero_wierszy(n, rejestry, rodzaj):
    plik = n.zapisz("sam_naglowek.csv", rodzaj, [])
    wynik = rejestry.sprawdz_plik(plik, rodzaj)
    assert wynik.poprawny is True
    assert list(wynik.bledy) == []
    kod, out, _ = n.uruchom("sprawdz", "--rodzaj", rodzaj, "--json", plik)
    assert kod == 0
    dane = json.loads(out)
    assert dane["poprawny"] is True
    assert dane["wiersze"] == 0
    assert dane["bledy"] == []


@pytest.mark.parametrize("rodzaj", ["mozliwosci", "kandydaci"])
def test_k01_plik_pusty_jest_niepoprawny(n, rejestry, rodzaj):
    plik = n.zapisz_tekst("pusty.csv", "")
    wynik = rejestry.sprawdz_plik(plik, rodzaj)
    assert wynik.poprawny is False
    assert len(wynik.bledy) >= 1
    assert all(b.kolumna == "-" and str(b.plik) == plik and b.opis for b in wynik.bledy)
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", rodzaj, plik)
    assert kod == 1
    dopasowania = n.linie_bledow(err)
    assert dopasowania
    assert all(d["plik"] == plik and d["kolumna"] == "-" for d in dopasowania)


def test_k01_brak_kolumny_wymieniony_w_komunikacie(n, rejestry):
    naglowek = [k for k in n.NAGLOWEK_M if k != "kotwica"]
    plik = n.zapisz("brak.csv", "mozliwosci", [n.wiersz_m()], naglowek=naglowek)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is False
    bledy_naglowka = [b for b in wynik.bledy if int(b.wiersz) == 1]
    assert bledy_naglowka, "błąd nagłówka musi mieć wiersz 1"
    assert all(b.kolumna == "-" for b in bledy_naglowka)
    assert any("kotwica" in b.opis for b in bledy_naglowka)
    assert str(bledy_naglowka[0].plik) == plik


def test_k01_kolumna_nadmiarowa_wymieniona_w_komunikacie(n, rejestry):
    naglowek = n.NAGLOWEK_K + ["dodatkowa_kolumna"]
    plik = n.zapisz("nadmiar.csv", "kandydaci", [n.wiersz_k()], naglowek=naglowek)
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert wynik.poprawny is False
    bledy_naglowka = [b for b in wynik.bledy if int(b.wiersz) == 1 and b.kolumna == "-"]
    assert any("dodatkowa_kolumna" in b.opis for b in bledy_naglowka)


def test_k01_brakujaca_i_nadmiarowa_naraz_cli(n):
    naglowek = [("kategoria" if k == "obszar" else k) for k in n.NAGLOWEK_M]
    plik = n.zapisz("zamiana.csv", "mozliwosci", [n.wiersz_m()], naglowek=naglowek)
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", plik)
    assert kod == 1
    dopasowania = n.linie_bledow(err)
    naglowkowe = [d for d in dopasowania if d["wiersz"] == "1" and d["kolumna"] == "-"]
    assert naglowkowe
    assert all(d["plik"] == plik for d in naglowkowe)
    tekst = " ".join(d["opis"] for d in naglowkowe)
    assert "obszar" in tekst
    assert "kategoria" in tekst


def test_k01_inna_kolejnosc_kolumn_jest_bledem(n, rejestry):
    naglowek = list(n.NAGLOWEK_M)
    naglowek[1], naglowek[2] = naglowek[2], naglowek[1]
    plik = n.zapisz("kolejnosc.csv", "mozliwosci", [n.wiersz_m()], naglowek=naglowek)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is False
    assert (1, "-") in n.pary(wynik)


def test_k01_naglowek_innego_rodzaju_jest_bledem(n, rejestry):
    plik = n.zapisz("kandydaci_jako_m.csv", "kandydaci", [n.wiersz_k()])
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is False
    assert (1, "-") in n.pary(wynik)


def test_k01_wielkosc_liter_w_naglowku_ma_znaczenie(n, rejestry):
    naglowek = [("ID" if k == "id" else k) for k in n.NAGLOWEK_K]
    plik = n.zapisz("wielkie.csv", "kandydaci", [n.wiersz_k()], naglowek=naglowek)
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert wynik.poprawny is False
    assert (1, "-") in n.pary(wynik)


# ------------------------------------------------- K02 — pola wymagane i długości

WYMAGANE_M = ["mozliwosc", "obszar", "zrodlo", "data_zrodla", "stare_studio", "status", "partia"]
WYMAGANE_K = ["nazwa", "rodzaj", "zrodlo", "data_zrodla", "status", "partia"]


@pytest.mark.parametrize("kolumna", WYMAGANE_M)
def test_k02_puste_pole_wymagane_mozliwosci(n, rejestry, kolumna):
    wiersze = n.wiersze_m(3)
    wiersze[1][kolumna] = ""
    plik = n.zapisz("wym.csv", "mozliwosci", wiersze)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert n.pary(wynik) == {(3, kolumna)}
    assert wynik.poprawny is False


@pytest.mark.parametrize("kolumna", WYMAGANE_K)
def test_k02_puste_pole_wymagane_kandydaci(n, rejestry, kolumna):
    wiersze = [n.wiersz_k(id="K-0001"), n.wiersz_k(id="K-0002", nazwa="Edytor"), n.wiersz_k(id="K-0003", nazwa="Kalendarz")]
    wiersze[2][kolumna] = ""
    plik = n.zapisz("wym.csv", "kandydaci", wiersze)
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert n.pary(wynik) == {(4, kolumna)}


@pytest.mark.parametrize(
    ("dlugosc", "dobrze"),
    [(0, False), (1, False), (9, False), (10, True), (11, True), (299, True), (300, True), (301, False), (400, False)],
)
def test_k02_dlugosc_mozliwosci_od_10_do_300(n, rejestry, dlugosc, dobrze):
    wiersz = n.wiersz_m(mozliwosc="x" * dlugosc)
    plik = n.zapisz("dl.csv", "mozliwosci", [wiersz])
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert n.pary(wynik) == (set() if dobrze else {(2, "mozliwosc")})


@pytest.mark.parametrize(
    ("dlugosc", "dobrze"),
    [(0, False), (1, False), (2, True), (3, True), (119, True), (120, True), (121, False), (200, False)],
)
def test_k02_dlugosc_nazwy_od_2_do_120(n, rejestry, dlugosc, dobrze):
    wiersz = n.wiersz_k(nazwa="n" * dlugosc)
    plik = n.zapisz("dl.csv", "kandydaci", [wiersz])
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert n.pary(wynik) == (set() if dobrze else {(2, "nazwa")})


@pytest.mark.parametrize(("dlugosc", "dobrze"), [(0, True), (1, True), (119, True), (120, True), (121, False)])
def test_k02_kotwica_najwyzej_120(n, rejestry, dlugosc, dobrze):
    wiersz = n.wiersz_m(kotwica="k" * dlugosc)
    plik = n.zapisz("kotwica.csv", "mozliwosci", [wiersz])
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert n.pary(wynik) == (set() if dobrze else {(2, "kotwica")})


def test_k02_dlugosc_liczona_w_znakach_nie_w_bajtach(n, rejestry):
    wiersze = [
        n.wiersz_m(id="M-0001", mozliwosc="ąę" * 150, kotwica="ż" * 120),
        n.wiersz_m(id="M-0002", mozliwosc="ść" * 5),
    ]
    plik = n.zapisz("znaki.csv", "mozliwosci", wiersze)
    assert rejestry.sprawdz_plik(plik, "mozliwosci").poprawny is True
    plik_k = n.zapisz("znaki_k.csv", "kandydaci", [n.wiersz_k(nazwa="ó" * 120), n.wiersz_k(id="K-0002", nazwa="łź")])
    assert rejestry.sprawdz_plik(plik_k, "kandydaci").poprawny is True


def test_k02_wszystkie_bledy_w_jednym_przebiegu(n, rejestry):
    wiersze = n.wiersze_m(6)
    wiersze[0]["zrodlo"] = ""
    wiersze[0]["partia"] = ""
    wiersze[2]["mozliwosc"] = "za krótko"  # 9 znaków
    wiersze[3]["kotwica"] = "a" * 121
    wiersze[5]["status"] = ""
    wiersze[5]["mozliwosc"] = "b" * 301
    plik = n.zapisz("wiele.csv", "mozliwosci", wiersze)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    oczekiwane = {(2, "zrodlo"), (2, "partia"), (4, "mozliwosc"), (5, "kotwica"), (7, "status"), (7, "mozliwosc")}
    assert n.pary(wynik) == oczekiwane
    assert all(str(b.plik) == plik for b in wynik.bledy)

    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", plik)
    assert kod == 1
    dopasowania = n.linie_bledow(err)
    assert {(int(d["wiersz"]), d["kolumna"]) for d in dopasowania} == oczekiwane
    assert all(d["plik"] == plik for d in dopasowania)


def test_k02_wszystkie_bledy_kandydatow_w_jednym_przebiegu(n, rejestry):
    wiersze = [
        n.wiersz_k(id="K-0001", nazwa="A"),
        n.wiersz_k(id="K-0002", nazwa="Poprawna nazwa"),
        n.wiersz_k(id="K-0003", nazwa="Trzecia", zrodlo="", rodzaj=""),
        n.wiersz_k(id="K-0004", nazwa="z" * 121, partia=""),
    ]
    plik = n.zapisz("wiele_k.csv", "kandydaci", wiersze)
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert n.pary(wynik) == {(2, "nazwa"), (4, "zrodlo"), (4, "rodzaj"), (5, "nazwa"), (5, "partia")}


def test_k02_pola_dowolne_moga_byc_puste_i_dowolne(n, rejestry):
    wiersz = n.wiersz_m(test_odbioru="", uwagi="cokolwiek; nawet \"cudzysłów\"")
    wiersz_k = n.wiersz_k(stan_dzis="?", koszt="", ryzyko="duże", wspolgranie="", werdykt="x", poprzedni_werdykt="")
    assert rejestry.sprawdz_plik(n.zapisz("m.csv", "mozliwosci", [wiersz]), "mozliwosci").poprawny is True
    assert rejestry.sprawdz_plik(n.zapisz("k.csv", "kandydaci", [wiersz_k]), "kandydaci").poprawny is True
