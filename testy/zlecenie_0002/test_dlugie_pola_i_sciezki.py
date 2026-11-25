"""Zlecenie 0002 — K01 (długie pola) i K02 (błędne ścieżki).

SZKIC AI — do pracy autora.

Duże pliki powstają w katalogu tymczasowym testu. Dane są fikcyjne.
"""

from __future__ import annotations

import pytest

MILION = 1_000_000
# Treść długiego pola z separatorem, cudzysłowem i nowym wierszem; ponad milion znaków.
DLUGA_TRESC = ("Długa uwaga; z \"cudzysłowem\"\noraz nowym wierszem. " * (MILION // 40 + 1))


# ---------------------------------------------------------------- K01 — długie pola


def _wiersz(n, rodzaj: str, **zmiany: str) -> dict[str, str]:
    return n.wiersz_m(**zmiany) if rodzaj == "mozliwosci" else n.wiersz_k(**zmiany)


@pytest.mark.parametrize("rodzaj", ["mozliwosci", "kandydaci"])
def test_k01_dlugie_uwagi_sprawdz_poprawny(n, rodzaj):
    assert len(DLUGA_TRESC) >= MILION
    plik = n.zapisz("dlugi.csv", rodzaj, [_wiersz(n, rodzaj, uwagi=DLUGA_TRESC)])
    kod, out, err = n.uruchom("sprawdz", "--rodzaj", rodzaj, "--json", plik)
    assert kod == 0, err[:500]
    obiekt = n.jeden_json(out)
    assert obiekt["poprawny"] is True
    assert obiekt["wiersze"] == 1
    assert obiekt["bledy"] == []


def test_k01_dlugie_uwagi_biblioteka_bez_wyjatku(n, rejestry):
    plik = n.zapisz("dlugi.csv", "mozliwosci", [n.wiersz_m(uwagi="u" * (2 * MILION))])
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is True
    assert wynik.bledy == []


@pytest.mark.parametrize("rodzaj", ["mozliwosci", "kandydaci"])
def test_k01_scal_przenosi_dlugie_pole_bez_zmian(n, rodzaj):
    wiersz = _wiersz(n, rodzaj, uwagi=DLUGA_TRESC)
    partia = n.zapisz("partia.csv", rodzaj, [wiersz])
    wyjscie = str(n.katalog / "wyjscie.csv")
    kod, _out, err = n.uruchom("scal", "--rodzaj", rodzaj, "--wyjscie", wyjscie, partia)
    assert kod == 0, err[:500]
    assert (n.katalog / "wyjscie.csv").read_bytes() == n.format_wyjscia(rodzaj, [wiersz])


def test_k01_scal_biblioteka_dlugie_pole(n, rejestry):
    wiersz = n.wiersz_m(uwagi=DLUGA_TRESC)
    partia = n.zapisz("partia.csv", "mozliwosci", [wiersz])
    wiersze, wynik = rejestry.scal_pliki([partia], "mozliwosci")
    assert wynik.poprawny is True
    assert [w["uwagi"] for w in wiersze] == [DLUGA_TRESC]


@pytest.mark.parametrize(
    ("rodzaj", "kolumna"),
    [("mozliwosci", "mozliwosc"), ("mozliwosci", "kotwica"), ("kandydaci", "nazwa")],
)
def test_k01_dlugie_pole_z_limitem_to_blad_dlugosci(n, rodzaj, kolumna):
    plik = n.zapisz("dlugi.csv", rodzaj, [_wiersz(n, rodzaj, **{kolumna: "x" * MILION})])
    kod, out, err = n.uruchom("sprawdz", "--rodzaj", rodzaj, "--json", plik)
    assert kod == 1
    obiekt = n.jeden_json(out)
    assert obiekt["poprawny"] is False
    assert obiekt["wiersze"] == 1
    assert {(b["wiersz"], b["kolumna"]) for b in obiekt["bledy"]} == {(2, kolumna)}


def test_k01_dlugie_pole_z_limitem_biblioteka(n, rejestry):
    plik = n.zapisz("dlugi.csv", "kandydaci", [n.wiersz_k(nazwa="n" * MILION)])
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert wynik.poprawny is False
    assert n.pary(wynik) == {(2, "nazwa")}


def test_k01_scal_dlugie_pole_z_limitem_kod_1(n):
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m(mozliwosc="m" * MILION)])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, out, _err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--json", partia)
    assert kod == 1
    obiekt = n.jeden_json(out)
    assert obiekt["poprawny"] is False
    assert {(b["wiersz"], b["kolumna"]) for b in obiekt["bledy"]} == {(2, "mozliwosc")}
    assert not wyjscie.exists()


# ---------------------------------------------------------------- K02 — błędne ścieżki


def _jeden_wiersz_przyczyny(err: str) -> None:
    linie = [linia for linia in err.splitlines() if linia.strip()]
    assert len(linie) == 1, linie


def _zla_sciezka(n, rodzaj_bledu: str) -> str:
    """Ścieżka wejściowa: z bajtem NUL, wskazująca katalog albo plik nieczytelny jako UTF-8."""
    if rodzaj_bledu == "nul":
        return str(n.katalog / "zly\x00plik.csv")
    if rodzaj_bledu == "katalog":
        katalog = n.katalog / "to_katalog.csv"
        katalog.mkdir()
        return str(katalog)
    naglowek = ";".join(n.NAGLOWEK_M).encode("utf-8") + b"\n"
    sciezka = n.katalog / "nie_utf8.csv"
    sciezka.write_bytes(naglowek + b'"M-0001";"Mo\xbfliwo\xb6\xe6 w ISO-8859-2";"inne"\n')
    return str(sciezka)


BLEDY_WEJSCIA = ["nul", "katalog", "nie_utf8"]


@pytest.mark.parametrize("rodzaj_bledu", BLEDY_WEJSCIA)
@pytest.mark.parametrize("partia", [False, True])
def test_k02_sprawdz_zla_sciezka(n, rodzaj_bledu, partia):
    plik = _zla_sciezka(n, rodzaj_bledu)
    argumenty = ["sprawdz", "--rodzaj", "mozliwosci"] + (["--partia"] if partia else []) + [plik]
    kod, _out, err = n.uruchom(*argumenty)
    assert kod == 2
    _jeden_wiersz_przyczyny(err)


@pytest.mark.parametrize("rodzaj_bledu", BLEDY_WEJSCIA)
def test_k02_scal_zla_partia(n, rodzaj_bledu):
    dobra = n.zapisz("dobra.csv", "mozliwosci", [n.wiersz_m()])
    zla = _zla_sciezka(n, rodzaj_bledu)
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), dobra, zla)
    assert kod == 2
    _jeden_wiersz_przyczyny(err)
    assert not wyjscie.exists()


@pytest.mark.parametrize("rodzaj_bledu", BLEDY_WEJSCIA)
def test_k02_scal_zly_rejestr(n, rodzaj_bledu):
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m()])
    zly = _zla_sciezka(n, rodzaj_bledu)
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--rejestr", zly, partia)
    assert kod == 2
    _jeden_wiersz_przyczyny(err)
    assert not wyjscie.exists()


def _zly_cel(n, rodzaj_bledu: str) -> str:
    if rodzaj_bledu == "nul":
        return str(n.katalog / "zle\x00wyjscie.txt")
    katalog = n.katalog / "cel_katalog"
    katalog.mkdir()
    return str(katalog)


@pytest.mark.parametrize("rodzaj_bledu", ["nul", "katalog"])
def test_k02_scal_zle_wyjscie(n, rodzaj_bledu):
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m()])
    cel = _zly_cel(n, rodzaj_bledu)
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", cel, partia)
    assert kod == 2
    _jeden_wiersz_przyczyny(err)


@pytest.mark.parametrize("rodzaj_bledu", ["nul", "katalog"])
def test_k02_scal_zly_raport(n, rodzaj_bledu):
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m()])
    cel = _zly_cel(n, rodzaj_bledu)
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", cel, partia)
    assert kod == 2
    _jeden_wiersz_przyczyny(err)


def test_k02_json_przy_zlej_sciezce_nie_rzuca(n):
    kod, out, err = n.uruchom("sprawdz", "--rodzaj", "kandydaci", "--json", str(n.katalog / "a\x00b.csv"))
    assert kod == 2
    _jeden_wiersz_przyczyny(err)
    assert out.strip() == "" or isinstance(n.jeden_json(out), dict)
