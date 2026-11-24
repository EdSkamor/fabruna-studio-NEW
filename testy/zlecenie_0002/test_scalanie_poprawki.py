"""Zlecenie 0002 — K03 (koniec numeracji), K04 (zapis wszystko albo nic),
K05 (istniejący rejestr jest pełnym rejestrem), K06 (jedno zgłoszenie na komórkę).

SZKIC AI — do pracy autora.

Dane są fikcyjne.
"""

from __future__ import annotations

import re
from collections import Counter

import pytest

STARA_TRESC = b"stara tresc pliku, ktorej nie wolno ruszyc\n"


# ---------------------------------------------------------------- K03 — koniec numeracji


@pytest.mark.parametrize(("rodzaj", "prefiks"), [("mozliwosci", "M-"), ("kandydaci", "K-")])
def test_k03_brak_wolnego_numeru_main(n, rodzaj, prefiks):
    wiersz = n.wiersz_m if rodzaj == "mozliwosci" else n.wiersz_k
    klucz = "mozliwosc" if rodzaj == "mozliwosci" else "nazwa"
    rejestr = n.zapisz("rejestr.csv", rodzaj, [
        wiersz(id=f"{prefiks}9998", **{klucz: "Wpis rejestru numer jeden"}),
    ])
    partia = n.zapisz("partia.csv", rodzaj, [
        wiersz(id="", **{klucz: "Wpis partii dostaje ostatni"}),
        wiersz(id="", **{klucz: "Wpis partii bez miejsca"}),
    ])
    wyjscie = n.katalog / "wyjscie.csv"
    wyjscie.write_bytes(STARA_TRESC)
    kod, _out, err = n.uruchom("scal", "--rodzaj", rodzaj, "--wyjscie", str(wyjscie), "--rejestr", rejestr, partia)
    assert kod == 1
    bledy = [m for m in n.linie_bledow(err) if m["plik"] == partia and m["wiersz"] == "3" and m["kolumna"] == "id"]
    assert len(bledy) == 1
    assert "brak wolnego numeru" in bledy[0]["opis"]
    assert not any(m["plik"] == partia and m["wiersz"] == "2" for m in n.linie_bledow(err))
    assert wyjscie.read_bytes() == STARA_TRESC


def test_k03_brak_wolnego_numeru_biblioteka(n, rejestry):
    partia = n.zapisz("partia.csv", "mozliwosci", [
        n.wiersz_m(id="M-9999", mozliwosc="Możliwość z ostatnim numerem"),
        n.wiersz_m(id="", mozliwosc="Możliwość bez identyfikatora"),
    ])
    wiersze, wynik = rejestry.scal_pliki([partia], "mozliwosci")
    assert wynik.poprawny is False
    bledy = [b for b in wynik.bledy if (str(b.plik), int(b.wiersz), b.kolumna) == (partia, 3, "id")]
    assert len(bledy) == 1
    assert "brak wolnego numeru" in bledy[0].opis
    assert not any(re.search(r"M-\d{5}", w.get("id", "")) for w in wiersze)


def test_k03_brak_wolnego_numeru_nie_tworzy_wyjscia(n):
    partia = n.zapisz("partia.csv", "kandydaci", [
        n.wiersz_k(id="K-9999", nazwa="Ostatni kandydat"),
        n.wiersz_k(id="", nazwa="Kandydat bez numeru"),
    ])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, out, _err = n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyjscie), "--json", partia)
    assert kod == 1
    obiekt = n.jeden_json(out)
    assert obiekt["poprawny"] is False
    assert any(b["wiersz"] == 3 and b["kolumna"] == "id" and "brak wolnego numeru" in b["opis"] for b in obiekt["bledy"])
    assert not wyjscie.exists()


@pytest.mark.parametrize(("rodzaj", "prefiks"), [("mozliwosci", "M-"), ("kandydaci", "K-")])
def test_k03_numer_9999_bez_nadawania_scala_sie(n, rodzaj, prefiks):
    wiersz = (n.wiersz_m if rodzaj == "mozliwosci" else n.wiersz_k)(id=f"{prefiks}9999")
    partia = n.zapisz("partia.csv", rodzaj, [wiersz])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _out, err = n.uruchom("scal", "--rodzaj", rodzaj, "--wyjscie", str(wyjscie), partia)
    assert kod == 0, err
    assert wyjscie.read_bytes() == n.format_wyjscia(rodzaj, [wiersz])


def test_k03_nadanie_numeru_9999_jest_poprawne(n, rejestry):
    partia = n.zapisz("partia.csv", "mozliwosci", [
        n.wiersz_m(id="M-9998", mozliwosc="Przedostatnia możliwość"),
        n.wiersz_m(id="", mozliwosc="Ostatnia wolna możliwość"),
    ])
    wiersze, wynik = rejestry.scal_pliki([partia], "mozliwosci")
    assert wynik.poprawny is True
    assert [w["id"] for w in wiersze] == ["M-9998", "M-9999"]


# ---------------------------------------------------------------- K04 — zapis wszystko albo nic


def _partia_z_ostrzezeniem(n) -> str:
    return n.zapisz("partia.csv", "mozliwosci", [
        n.wiersz_m(id="M-0001", mozliwosc="Podsumowanie poczty rano"),
        n.wiersz_m(id="M-0002", mozliwosc="podsumowanie  POCZTY rano."),
    ])


def test_k04_raport_w_nieistniejacym_katalogu_bez_wyjscia(n):
    partia = _partia_z_ostrzezeniem(n)
    wyjscie = n.katalog / "wyjscie.csv"
    raport = n.katalog / "nie_ma_takiego" / "raport.txt"
    przed = n.drzewo()
    kod, _out, err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )
    assert kod == 2
    assert not wyjscie.exists()
    assert n.drzewo() == przed, err


def test_k04_raport_nieudany_istniejace_wyjscie_bez_zmian(n):
    partia = _partia_z_ostrzezeniem(n)
    wyjscie = n.katalog / "wyjscie.csv"
    wyjscie.write_bytes(STARA_TRESC)
    raport = n.katalog / "brak" / "raport.txt"
    przed = n.drzewo()
    kod, _out, _err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )
    assert kod == 2
    assert wyjscie.read_bytes() == STARA_TRESC
    assert n.drzewo() == przed


def test_k04_wyjscie_nieudane_raport_nie_powstaje(n):
    partia = _partia_z_ostrzezeniem(n)
    wyjscie = n.katalog / "brak" / "wyjscie.csv"
    raport = n.katalog / "raport.txt"
    przed = n.drzewo()
    kod, _out, _err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )
    assert kod == 2
    assert not raport.exists()
    assert n.drzewo() == przed


def test_k04_blad_danych_nie_rusza_raportu_ani_wyjscia(n):
    partia = n.zapisz("partia.csv", "mozliwosci", [
        n.wiersz_m(id="M-0001", mozliwosc="Podsumowanie poczty rano"),
        n.wiersz_m(id="M-0002", mozliwosc="podsumowanie poczty rano"),
        n.wiersz_m(id="M-0003", obszar="spoza słownika"),
    ])
    wyjscie = n.katalog / "wyjscie.csv"
    raport = n.katalog / "raport.txt"
    wyjscie.write_bytes(STARA_TRESC)
    raport.write_bytes(STARA_TRESC)
    przed = n.drzewo()
    kod, _out, _err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )
    assert kod == 1
    assert n.drzewo() == przed


def test_k04_blad_danych_raport_nie_powstaje(n):
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m(status="nieznany")])
    wyjscie = n.katalog / "wyjscie.csv"
    raport = n.katalog / "raport.txt"
    przed = n.drzewo()
    kod, _out, _err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )
    assert kod == 1
    assert not raport.exists()
    assert not wyjscie.exists()
    assert n.drzewo() == przed


def test_k04_sukces_pelna_tresc_i_bez_plikow_tymczasowych(n):
    wiersze = [
        n.wiersz_m(id="M-0001", mozliwosc="Podsumowanie poczty rano"),
        n.wiersz_m(id="M-0002", mozliwosc="podsumowanie  POCZTY rano."),
    ]
    partia = n.zapisz("partia.csv", "mozliwosci", wiersze)
    (n.katalog / "cel").mkdir()
    wyjscie = n.katalog / "cel" / "wyjscie.csv"
    raport = n.katalog / "raport.txt"
    raport.write_bytes(STARA_TRESC)
    przed = n.drzewo()
    kod, _out, err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), partia
    )
    assert kod == 0, err
    po = n.drzewo()
    assert set(po) == set(przed) | {"cel/wyjscie.csv"}
    assert wyjscie.read_bytes() == n.format_wyjscia("mozliwosci", wiersze)
    linie = raport.read_text("utf-8").splitlines()
    assert len(linie) == 1
    assert linie[0].startswith(f"{partia}:3: mozliwosc: ")


def test_k04_sukces_nadpisuje_istniejace_wyjscie(n):
    wiersz = n.wiersz_m()
    partia = n.zapisz("partia.csv", "mozliwosci", [wiersz])
    wyjscie = n.katalog / "wyjscie.csv"
    wyjscie.write_bytes(STARA_TRESC)
    przed = set(n.drzewo())
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), partia)
    assert kod == 0, err
    assert set(n.drzewo()) == przed
    assert wyjscie.read_bytes() == n.format_wyjscia("mozliwosci", [wiersz])


# ---------------------------------------------------------------- K05 — istniejący rejestr


def test_k05_pusty_id_w_rejestrze_to_blad(n):
    rejestr = n.zapisz("rejestr.csv", "mozliwosci", [
        n.wiersz_m(id="M-0001", mozliwosc="Pierwsza możliwość rejestru"),
        n.wiersz_m(id="", mozliwosc="Możliwość rejestru bez numeru"),
    ])
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m(id="", mozliwosc="Możliwość z partii bez numeru")])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--rejestr", rejestr, partia)
    assert kod == 1
    klucze = {(m["plik"], m["wiersz"], m["kolumna"]) for m in n.linie_bledow(err)}
    assert (rejestr, "3", "id") in klucze
    assert not any(plik == partia for plik, _, _ in klucze)
    assert not wyjscie.exists()


def test_k05_pusty_id_w_rejestrze_biblioteka(n, rejestry):
    rejestr = n.zapisz("rejestr.csv", "kandydaci", [n.wiersz_k(id="", nazwa="Kandydat bez numeru")])
    partia = n.zapisz("partia.csv", "kandydaci", [n.wiersz_k(id="K-0002", nazwa="Kandydat z partii")])
    _wiersze, wynik = rejestry.scal_pliki([partia], "kandydaci", rejestr=rejestr)
    assert wynik.poprawny is False
    assert (rejestr, 2, "id") in n.klucze(wynik)


def test_k05_pusty_id_w_samym_rejestrze_bez_partii(n):
    rejestr = n.zapisz("rejestr.csv", "kandydaci", [n.wiersz_k(id="")])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, out, _err = n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyjscie), "--rejestr", rejestr, "--json")
    assert kod == 1
    obiekt = n.jeden_json(out)
    assert any(b["plik"] == rejestr and b["wiersz"] == 2 and b["kolumna"] == "id" for b in obiekt["bledy"])
    assert not wyjscie.exists()


def test_k05_puste_id_w_partii_nadal_dozwolone(n, rejestry):
    rejestr = n.zapisz("rejestr.csv", "mozliwosci", [n.wiersz_m(id="M-0004", mozliwosc="Możliwość z rejestru")])
    partia = n.zapisz("partia.csv", "mozliwosci", [n.wiersz_m(id="", mozliwosc="Możliwość z partii")])
    wiersze, wynik = rejestry.scal_pliki([partia], "mozliwosci", rejestr=rejestr)
    assert wynik.poprawny is True
    assert [w["id"] for w in wiersze] == ["M-0004", "M-0005"]


# ---------------------------------------------------------------- K06 — jedno zgłoszenie na komórkę


def test_k06_powtorzony_id_rozna_tresc_jeden_blad_main(n):
    partia = n.zapisz("partia.csv", "mozliwosci", [
        n.wiersz_m(id="M-0007", mozliwosc="Pierwsza treść możliwości"),
        n.wiersz_m(id="M-0008", mozliwosc="Zupełnie inna możliwość"),
        n.wiersz_m(id="M-0007", mozliwosc="Druga, różna treść możliwości"),
    ])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _out, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), partia)
    assert kod == 1
    bledy = n.linie_bledow(err)
    trafione = [m for m in bledy if (m["plik"], m["wiersz"], m["kolumna"]) == (partia, "4", "id")]
    assert len(trafione) == 1, [m.group(0) for m in bledy]
    assert re.search(r"(?<!\d)2(?!\d)", trafione[0]["opis"])
    assert len(bledy) == 1
    assert not wyjscie.exists()


def test_k06_powtorzony_id_rozna_tresc_jeden_blad_biblioteka(n, rejestry):
    partia = n.zapisz("partia.csv", "kandydaci", [
        n.wiersz_k(id="K-0003", nazwa="Pierwszy kandydat"),
        n.wiersz_k(id="K-0003", nazwa="Inny kandydat"),
    ])
    _wiersze, wynik = rejestry.scal_pliki([partia], "kandydaci")
    assert wynik.poprawny is False
    assert n.klucze(wynik) == [(partia, 3, "id")]
    assert re.search(r"(?<!\d)2(?!\d)", wynik.bledy[0].opis)


def _bez_powtorzen(klucze) -> None:
    powtorzone = [k for k, ile in Counter(klucze).items() if ile > 1]
    assert powtorzone == []


def test_k06_sprawdz_bez_dwoch_bledow_tej_samej_komorki(n, rejestry):
    plik = n.zapisz("plik.csv", "mozliwosci", [
        n.wiersz_m(id="M-01", mozliwosc="Pierwsza możliwość testowa"),
        n.wiersz_m(id="M-01", mozliwosc="Druga możliwość testowa"),
    ])
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is False
    assert (plik, 2, "id") in n.klucze(wynik)
    assert (plik, 3, "id") in n.klucze(wynik)
    _bez_powtorzen(n.klucze(wynik))


def test_k06_scal_bez_dwoch_bledow_tej_samej_komorki(n):
    rejestr = n.zapisz("rejestr.csv", "mozliwosci", [n.wiersz_m(id="M-0001", mozliwosc="Treść z rejestru")])
    partia = n.zapisz("partia.csv", "mozliwosci", [
        n.wiersz_m(id="M-0001", mozliwosc="Inna treść w partii"),
        n.wiersz_m(id="M-0001", mozliwosc="Jeszcze inna treść w partii"),
        n.wiersz_m(id="M-0002", mozliwosc="Możliwość druga"),
        n.wiersz_m(id="M-0002", mozliwosc="Możliwość druga zmieniona"),
    ])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, out, _err = n.uruchom(
        "scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--rejestr", rejestr, "--json", partia
    )
    assert kod == 1
    obiekt = n.jeden_json(out)
    klucze = [(b["plik"], b["wiersz"], b["kolumna"]) for b in obiekt["bledy"]]
    _bez_powtorzen(klucze)
    for wiersz in (2, 3, 5):
        assert (partia, wiersz, "id") in klucze
    assert not wyjscie.exists()
