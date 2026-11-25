"""Zlecenie 0003 — K04 (stan modułu csv) i K05 (błędy programistyczne nie są maskowane).

SZKIC AI — do pracy autora.

Dane są fikcyjne.
"""

from __future__ import annotations

import csv

import pytest

DOMYSLNY = 131_072
LIMITY = [DOMYSLNY, 4_096]
DLUGIE = "d" * (3 * DOMYSLNY)


# ---------------------------------------------------------------- K04 — stan modułu csv


@pytest.mark.parametrize("limit", LIMITY)
def test_k04_sprawdz_plik_przywraca_limit(n, rejestry, limit_csv, limit):
    plik = n.zapisz("dlugi.csv", [n.wiersz_m(uwagi=DLUGIE)])
    csv.field_size_limit(limit)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert csv.field_size_limit() == limit
    assert wynik.poprawny is True
    assert wynik.bledy == []


@pytest.mark.parametrize("limit", LIMITY)
def test_k04_scal_pliki_przywraca_limit(n, rejestry, limit_csv, limit):
    rejestr = n.zapisz("rejestr.csv", [n.wiersz_m(id="M-0001", mozliwosc="Pierwsza możliwość testowa")])
    partia = n.zapisz("partia.csv", [n.wiersz_m(id="M-0002", mozliwosc="Druga możliwość testowa", uwagi=DLUGIE)])
    csv.field_size_limit(limit)
    wiersze, wynik = rejestry.scal_pliki([partia], "mozliwosci", rejestr)
    assert csv.field_size_limit() == limit
    assert wynik.poprawny is True
    assert [w["uwagi"] for w in wiersze] == ["", DLUGIE]


@pytest.mark.parametrize("limit", LIMITY)
def test_k04_main_przywraca_limit(n, limit_csv, limit):
    wiersze = [n.wiersz_m(uwagi=DLUGIE)]
    partia = n.zapisz("partia.csv", wiersze)
    wyjscie = n.katalog / "wyjscie.csv"
    csv.field_size_limit(limit)
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), partia)
    assert csv.field_size_limit() == limit
    assert kod == 0, err[:500]
    assert wyjscie.read_bytes() == n.format_wyjscia(wiersze)

    kod, _out, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", partia)
    assert csv.field_size_limit() == limit
    assert kod == 0, err[:500]


@pytest.mark.parametrize("limit", LIMITY)
def test_k04_sprawdz_plik_blad_utf8_przywraca_limit(n, rejestry, limit_csv, limit):
    plik = n.katalog / "zly.csv"
    plik.write_bytes(b"id;mozliwosc\n\xff\xfe;x\n")
    csv.field_size_limit(limit)
    with pytest.raises(ValueError):
        rejestry.sprawdz_plik(str(plik), "mozliwosci")
    assert csv.field_size_limit() == limit


@pytest.mark.parametrize("limit", LIMITY)
def test_k04_scal_pliki_brak_pliku_przywraca_limit(n, rejestry, limit_csv, limit):
    partia = n.zapisz("partia.csv", n.wiersze())
    csv.field_size_limit(limit)
    with pytest.raises(OSError):
        rejestry.scal_pliki([partia, str(n.katalog / "nie_ma.csv")], "mozliwosci")
    assert csv.field_size_limit() == limit


@pytest.mark.parametrize("limit", LIMITY)
def test_k04_main_z_bledem_przywraca_limit(n, limit_csv, limit):
    zly = n.katalog / "zly.csv"
    zly.write_bytes(b"id;mozliwosc\n\xff\xfe;x\n")
    csv.field_size_limit(limit)
    kod, _out, _err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", str(zly))
    assert kod == 2
    assert csv.field_size_limit() == limit

    kod, _out, _err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(n.katalog / "wyjscie.csv"), str(n.katalog / "nie_ma.csv")
    )
    assert kod == 2
    assert csv.field_size_limit() == limit


# ---------------------------------------------------------------- K05 — błędy programistyczne nie są maskowane


def _zepsuj_scal_pliki(monkeypatch, rejestry):
    def zepsuta(*_args, **_kwargs):
        raise ValueError("sztuczny błąd programu")

    monkeypatch.setattr(f"{rejestry.main.__module__}.scal_pliki", zepsuta)


def test_k05_value_error_z_scal_pliki_wychodzi_z_main(n, rejestry, monkeypatch):
    partia = n.zapisz("partia.csv", n.wiersze())
    wyjscie = n.katalog / "wyjscie.csv"
    _zepsuj_scal_pliki(monkeypatch, rejestry)
    with pytest.raises(ValueError, match="sztuczny błąd programu"):
        rejestry.main(["scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), partia])
    assert not wyjscie.exists()


def test_k05_value_error_z_raportem_i_json(n, rejestry, monkeypatch):
    partia = n.zapisz("partia.csv", n.wiersze())
    wyjscie = n.katalog / "wyjscie.csv"
    raport = n.katalog / "raport.txt"
    _zepsuj_scal_pliki(monkeypatch, rejestry)
    with pytest.raises(ValueError, match="sztuczny błąd programu"):
        rejestry.main(
            ["scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), "--json", partia]
        )


def test_k05_bledy_danych_nadal_daja_kod_2(n):
    zly = n.katalog / "zly.csv"
    zly.write_bytes(b"id;mozliwosc\n\xff\xfe;x\n")
    kod, _out, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", str(zly))
    assert kod == 2
    assert err.strip()

    kod, _out, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", str(n.katalog / "zly\0.csv"))
    assert kod == 2
    assert err.strip()

    partia = n.zapisz("partia.csv", n.wiersze())
    kod, _out, err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(n.katalog / "wy\0jscie.csv"), partia
    )
    assert kod == 2
    assert err.strip()


def test_k05_blad_wejscia_wyjscia_daje_kod_2(n):
    kod, _out, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", str(n.katalog / "nie_ma.csv"))
    assert kod == 2
    assert err.strip()
