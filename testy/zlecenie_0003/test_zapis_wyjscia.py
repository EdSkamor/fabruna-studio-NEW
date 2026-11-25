"""Zlecenie 0003 — K01 (awaria podmiany), K02 (dowiązanie jako cel), K03 (uprawnienia wyjścia).

SZKIC AI — do pracy autora.

Dane są fikcyjne.
"""

from __future__ import annotations

import os
import stat

import pytest

STARA_A = b"stara tresc pierwszego celu\n"
STARA_B = b"stara tresc drugiego celu\n"


def _tryb(sciezka) -> int:
    return stat.S_IMODE(os.stat(sciezka).st_mode)


# ---------------------------------------------------------------- K01 — awaria podmiany


@pytest.mark.parametrize("pierwszy_istnial", [True, False])
@pytest.mark.parametrize("drugi_istnial", [True, False])
def test_k01_awaria_drugiej_podmiany_biblioteka(n, rejestry, awaria_podmiany, pierwszy_istnial, drugi_istnial):
    katalog_a = n.katalog / "a"
    katalog_b = n.katalog / "b"
    katalog_a.mkdir()
    katalog_b.mkdir()
    pierwszy = katalog_a / "pierwszy.csv"
    drugi = katalog_b / "drugi.txt"
    if pierwszy_istnial:
        pierwszy.write_bytes(STARA_A)
    if drugi_istnial:
        drugi.write_bytes(STARA_B)
    przed_a = n.nazwy(katalog_a)
    przed_b = n.nazwy(katalog_b)
    zastepca = awaria_podmiany("drugi.txt")

    with pytest.raises(OSError):
        rejestry.zapisz_wszystko_albo_nic([(str(pierwszy), "nowa treść A\n"), (str(drugi), "nowa treść B\n")])

    assert zastepca.zgloszona
    if pierwszy_istnial:
        assert pierwszy.read_bytes() == STARA_A
    else:
        assert not os.path.lexists(pierwszy)
    if drugi_istnial:
        assert drugi.read_bytes() == STARA_B
    else:
        assert not os.path.lexists(drugi)
    assert n.nazwy(katalog_a) == przed_a
    assert n.nazwy(katalog_b) == przed_b


def test_k01_awaria_w_jednym_katalogu_bez_plikow_tymczasowych(n, rejestry, awaria_podmiany):
    pierwszy = n.katalog / "wyjscie.csv"
    drugi = n.katalog / "raport.txt"
    pierwszy.write_bytes(STARA_A)
    przed = n.nazwy(n.katalog)
    awaria_podmiany("raport.txt")
    with pytest.raises(OSError):
        rejestry.zapisz_wszystko_albo_nic([(str(pierwszy), "A\n"), (str(drugi), "B\n")])
    assert pierwszy.read_bytes() == STARA_A
    assert n.nazwy(n.katalog) == przed


def test_k01_zapis_bez_awarii_zapisuje_oba(n, rejestry):
    pierwszy = n.katalog / "pierwszy.csv"
    drugi = n.katalog / "drugi.txt"
    pierwszy.write_bytes(STARA_A)
    rejestry.zapisz_wszystko_albo_nic([(str(pierwszy), "nowa treść A\n"), (str(drugi), "nowa treść B\n")])
    assert pierwszy.read_bytes() == "nowa treść A\n".encode("utf-8")
    assert drugi.read_bytes() == "nowa treść B\n".encode("utf-8")
    assert n.nazwy(n.katalog) == {"pierwszy.csv", "drugi.txt"}


def test_k01_eksport_z_pakietu(rejestry):
    assert callable(rejestry.zapisz_wszystko_albo_nic)
    assert "zapisz_wszystko_albo_nic" in rejestry.__all__


@pytest.mark.parametrize("wyjscie_istnialo", [True, False])
def test_k01_awaria_podmiany_przez_main(n, awaria_podmiany, wyjscie_istnialo):
    partia = n.zapisz("wejscie/partia.csv", n.wiersze())
    katalog = n.katalog / "cele"
    katalog.mkdir()
    wyjscie = katalog / "wyjscie.csv"
    raport = katalog / "raport.txt"
    if wyjscie_istnialo:
        wyjscie.write_bytes(STARA_A)
    raport.write_bytes(STARA_B)
    przed = n.nazwy(katalog)
    zastepca = awaria_podmiany("raport.txt")

    kod, _out, err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )

    assert zastepca.zgloszona
    assert kod == 2
    linie = [linia for linia in err.splitlines() if linia.strip()]
    assert len(linie) == 1, err
    if wyjscie_istnialo:
        assert wyjscie.read_bytes() == STARA_A
    else:
        assert not os.path.lexists(wyjscie)
    assert raport.read_bytes() == STARA_B
    assert n.nazwy(katalog) == przed


# ---------------------------------------------------------------- K02 — dowiązanie symboliczne jako cel


@pytest.mark.parametrize("wzgledne", [False, True])
def test_k02_wyjscie_jako_dowiazanie(n, wzgledne):
    wiersze = n.wiersze()
    partia = n.zapisz("partia.csv", wiersze)
    dane = n.katalog / "dane"
    dane.mkdir()
    prawdziwy = dane / "prawdziwy.csv"
    prawdziwy.write_bytes(STARA_A)
    wskazanie = "dane/prawdziwy.csv" if wzgledne else str(prawdziwy)
    dowiazanie = n.katalog / "wyjscie.csv"
    os.symlink(wskazanie, dowiazanie)

    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(dowiazanie), partia)

    assert kod == 0, err
    assert os.path.islink(dowiazanie)
    assert os.readlink(dowiazanie) == wskazanie
    assert prawdziwy.read_bytes() == n.format_wyjscia(wiersze)
    assert n.nazwy(dane) == {"prawdziwy.csv"}


def test_k02_raport_jako_dowiazanie(n):
    wiersze = n.wiersze()
    partia = n.zapisz("partia.csv", wiersze)
    prawdziwy = n.katalog / "prawdziwy_raport.txt"
    prawdziwy.write_bytes(STARA_B)
    dowiazanie = n.katalog / "raport.txt"
    os.symlink(str(prawdziwy), dowiazanie)
    wyjscie = n.katalog / "wyjscie.csv"

    kod, _out, err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(dowiazanie), partia
    )

    assert kod == 0, err
    assert os.path.islink(dowiazanie)
    assert os.readlink(dowiazanie) == str(prawdziwy)
    assert prawdziwy.read_bytes() == b""
    assert wyjscie.read_bytes() == n.format_wyjscia(wiersze)


def test_k02_wyjscie_dowiazanie_do_nieistniejacego(n):
    partia = n.zapisz("partia.csv", n.wiersze())
    brakujacy = n.katalog / "brak.csv"
    dowiazanie = n.katalog / "wyjscie.csv"
    os.symlink(str(brakujacy), dowiazanie)
    przed = n.nazwy(n.katalog)

    kod, _out, _err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(dowiazanie), partia)

    assert kod == 2
    assert not os.path.lexists(brakujacy)
    assert os.path.islink(dowiazanie)
    assert os.readlink(dowiazanie) == str(brakujacy)
    assert n.nazwy(n.katalog) == przed


def test_k02_raport_dowiazanie_do_nieistniejacego(n):
    partia = n.zapisz("partia.csv", n.wiersze())
    brakujacy = n.katalog / "brak.txt"
    dowiazanie = n.katalog / "raport.txt"
    os.symlink(str(brakujacy), dowiazanie)
    wyjscie = n.katalog / "wyjscie.csv"
    przed = n.nazwy(n.katalog)

    kod, _out, _err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(dowiazanie), partia
    )

    assert kod == 2
    assert not os.path.lexists(brakujacy)
    assert not os.path.lexists(wyjscie)
    assert os.path.islink(dowiazanie)
    assert n.nazwy(n.katalog) == przed


# ---------------------------------------------------------------- K03 — uprawnienia istniejącego wyjścia


@pytest.mark.parametrize("tryb", [0o640, 0o600, 0o664])
def test_k03_istniejace_wyjscie_zachowuje_tryb(n, umaska, tryb):
    wiersze = n.wiersze()
    partia = n.zapisz("partia.csv", wiersze)
    wyjscie = n.katalog / "wyjscie.csv"
    wyjscie.write_bytes(STARA_A)
    os.chmod(wyjscie, tryb)

    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), partia)

    assert kod == 0, err
    assert wyjscie.read_bytes() == n.format_wyjscia(wiersze)
    assert _tryb(wyjscie) == tryb


@pytest.mark.parametrize("tryb", [0o640, 0o600])
def test_k03_istniejacy_raport_zachowuje_tryb(n, umaska, tryb):
    partia = n.zapisz("partia.csv", n.wiersze())
    wyjscie = n.katalog / "wyjscie.csv"
    raport = n.katalog / "raport.txt"
    raport.write_bytes(STARA_B)
    os.chmod(raport, tryb)

    kod, _out, err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )

    assert kod == 0, err
    assert raport.read_bytes() == b""
    assert _tryb(raport) == tryb
    assert _tryb(wyjscie) == 0o666 & ~umaska


def test_k03_nowe_pliki_tryb_z_maska(n, umaska):
    partia = n.zapisz("partia.csv", n.wiersze())
    wyjscie = n.katalog / "wyjscie.csv"
    raport = n.katalog / "raport.txt"
    kod, _out, err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )
    assert kod == 0, err
    assert _tryb(wyjscie) == 0o666 & ~umaska
    assert _tryb(raport) == 0o666 & ~umaska


def test_k03_nowe_wyjscie_inna_maska(n, umaska):
    partia = n.zapisz("partia.csv", n.wiersze())
    wyjscie = n.katalog / "wyjscie.csv"
    poprzednia = os.umask(0o027)
    try:
        kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), partia)
    finally:
        os.umask(poprzednia)
    assert kod == 0, err
    assert _tryb(wyjscie) == 0o640
