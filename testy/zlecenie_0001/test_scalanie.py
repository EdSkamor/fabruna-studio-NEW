"""Zlecenie 0001 — K07 (nadawanie numerów), K08 (konflikty), K09 (wynik), K10 (ostrzeżenia), K11 (format).

SZKIC AI — do pracy autora.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


def _liczba(tekst: str, liczba: int) -> bool:
    return re.search(rf"(?<!\d){liczba}(?!\d)", tekst) is not None


# ---------------------------------------------------------------- K07 — nadawanie numerów


def _wejscia_k07(n):
    rejestr = n.zapisz("rejestr.csv", "mozliwosci", [
        n.wiersz_m(id="M-0003", mozliwosc="Rejestr: trzecia możliwość", status="scalone", partia="R"),
        n.wiersz_m(id="M-0010", mozliwosc="Rejestr: dziesiąta możliwość", status="scalone", partia="R"),
    ])
    partia_a = n.zapisz("partia_a.csv", "mozliwosci", [
        n.wiersz_m(id="", mozliwosc="A: pierwsza bez numeru", partia="A"),
        n.wiersz_m(id="M-0005", mozliwosc="A: z numerem piątym", partia="A"),
        n.wiersz_m(id="", mozliwosc="A: druga bez numeru", partia="A"),
    ])
    partia_b = n.zapisz("partia_b.csv", "mozliwosci", [
        n.wiersz_m(id="", mozliwosc="B: pierwsza bez numeru", partia="B"),
        n.wiersz_m(id="M-0012", mozliwosc="B: z numerem dwunastym", partia="B"),
        n.wiersz_m(id="", mozliwosc="B: druga bez numeru", partia="B"),
    ])
    return rejestr, partia_a, partia_b


OCZEKIWANE_K07 = {
    "Rejestr: trzecia możliwość": "M-0003",
    "A: z numerem piątym": "M-0005",
    "Rejestr: dziesiąta możliwość": "M-0010",
    "B: z numerem dwunastym": "M-0012",
    "A: pierwsza bez numeru": "M-0013",
    "A: druga bez numeru": "M-0014",
    "B: pierwsza bez numeru": "M-0015",
    "B: druga bez numeru": "M-0016",
}


def test_k07_kolejne_wolne_numery_po_najwyzszym(n, rejestry):
    rejestr, partia_a, partia_b = _wejscia_k07(n)
    wiersze, wynik = rejestry.scal_pliki([partia_a, partia_b], "mozliwosci", rejestr=rejestr)
    assert wynik.poprawny is True
    assert {w["mozliwosc"]: w["id"] for w in wiersze} == OCZEKIWANE_K07
    assert len(wiersze) == 8


def test_k07_kolejnosc_plikow_decyduje_o_numerach(n, rejestry):
    rejestr, partia_a, partia_b = _wejscia_k07(n)
    wiersze, wynik = rejestry.scal_pliki([partia_b, partia_a], "mozliwosci", rejestr=rejestr)
    assert wynik.poprawny is True
    nadane = {w["mozliwosc"]: w["id"] for w in wiersze}
    assert nadane["B: pierwsza bez numeru"] == "M-0013"
    assert nadane["B: druga bez numeru"] == "M-0014"
    assert nadane["A: pierwsza bez numeru"] == "M-0015"
    assert nadane["A: druga bez numeru"] == "M-0016"


def test_k07_bez_rejestru_numeracja_od_jedynki(n, rejestry):
    partia = n.zapisz("p.csv", "kandydaci", [
        n.wiersz_k(id="", nazwa="Pierwszy"),
        n.wiersz_k(id="", nazwa="Drugi"),
        n.wiersz_k(id="", nazwa="Trzeci"),
    ])
    wiersze, wynik = rejestry.scal_pliki([partia], "kandydaci")
    assert wynik.poprawny is True
    assert [(w["id"], w["nazwa"]) for w in wiersze] == [("K-0001", "Pierwszy"), ("K-0002", "Drugi"), ("K-0003", "Trzeci")]


def test_k07_najwyzszy_numer_z_rejestru(n, rejestry):
    rejestr = n.zapisz("r.csv", "kandydaci", [n.wiersz_k(id="K-0099", nazwa="Stary"), n.wiersz_k(id="K-0007", nazwa="Starszy")])
    partia = n.zapisz("p.csv", "kandydaci", [n.wiersz_k(id="", nazwa="Nowy")])
    wiersze, wynik = rejestry.scal_pliki([partia], "kandydaci", rejestr=rejestr)
    assert wynik.poprawny is True
    assert [w["id"] for w in wiersze] == ["K-0007", "K-0099", "K-0100"]
    assert wiersze[2]["nazwa"] == "Nowy"


def test_k07_numery_przez_cli(n):
    rejestr, partia_a, partia_b = _wejscia_k07(n)
    wyjscie = str(n.katalog / "wynik.csv")
    kod, _, _ = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", wyjscie, "--rejestr", rejestr, partia_a, partia_b)
    assert kod == 0
    linie = Path(wyjscie).read_text("utf-8").splitlines()[1:]
    ids = [linia.split(";")[0].strip('"') for linia in linie]
    assert ids == ["M-0003", "M-0005", "M-0010", "M-0012", "M-0013", "M-0014", "M-0015", "M-0016"]
    assert '"M-0013";"A: pierwsza bez numeru"' in Path(wyjscie).read_text("utf-8")


# ---------------------------------------------------------------- K08 — konflikty


def test_k08_ten_sam_id_ta_sama_tresc_daje_jeden_wiersz(n, rejestry):
    wspolny = n.wiersz_m(id="M-0004", mozliwosc="Wspólna możliwość w dwóch partiach", partia="AB")
    a = n.zapisz("a.csv", "mozliwosci", [wspolny, n.wiersz_m(id="M-0001", mozliwosc="Tylko w partii A")])
    b = n.zapisz("b.csv", "mozliwosci", [n.wiersz_m(id="M-0002", mozliwosc="Tylko w partii B"), wspolny])
    wiersze, wynik = rejestry.scal_pliki([a, b], "mozliwosci")
    assert list(wynik.bledy) == []
    assert [w["id"] for w in wiersze] == ["M-0001", "M-0002", "M-0004"]
    assert wiersze[2] == wspolny


def test_k08_ten_sam_id_ta_sama_tresc_w_rejestrze_i_partii(n, rejestry):
    wspolny = n.wiersz_k(id="K-0003", nazwa="Wspólny")
    r = n.zapisz("r.csv", "kandydaci", [wspolny])
    p = n.zapisz("p.csv", "kandydaci", [wspolny])
    wiersze, wynik = rejestry.scal_pliki([p], "kandydaci", rejestr=r)
    assert list(wynik.bledy) == []
    assert wiersze == [wspolny]


def test_k08_ten_sam_id_rozna_tresc_to_blad_z_oboma_plikami_i_wierszami(n, rejestry):
    a = n.zapisz("partia_pierwsza.csv", "mozliwosci", n.wiersze_m(2, start=1) + [n.wiersz_m(id="M-0009", mozliwosc="Wersja z pierwszej partii")])  # wiersz 4
    b = n.zapisz("partia_druga.csv", "mozliwosci", n.wiersze_m(5, start=20) + [n.wiersz_m(id="M-0009", mozliwosc="Wersja z drugiej partii")])  # wiersz 7
    wiersze, wynik = rejestry.scal_pliki([a, b], "mozliwosci")
    assert wynik.poprawny is False
    assert len(wynik.bledy) == 1
    pelny = n.pelny(wynik.bledy[0]).replace(str(n.katalog), "")
    assert "partia_pierwsza.csv" in pelny
    assert "partia_druga.csv" in pelny
    assert _liczba(pelny, 4)
    assert _liczba(pelny, 7)


def test_k08_konflikt_z_rejestrem_cli_kod_1_i_brak_wyjscia(n):
    r = n.zapisz("istniejacy.csv", "kandydaci", [n.wiersz_k(id="K-0002", nazwa="Wersja rejestru")])
    p = n.zapisz("nowa_partia.csv", "kandydaci", [n.wiersz_k(id="", nazwa="Bez numeru"), n.wiersz_k(id="K-0002", nazwa="Wersja partii")])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _, err = n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyjscie), "--rejestr", r, p)
    assert kod == 1
    assert not wyjscie.exists()
    tekst = err.replace(str(n.katalog), "")
    assert "istniejacy.csv" in tekst and "nowa_partia.csv" in tekst
    assert _liczba(tekst, 2) and _liczba(tekst, 3)
    n.linie_bledow(err)


def test_k08_istniejacy_plik_wyjsciowy_pozostaje_bez_zmian(n):
    a = n.zapisz("a.csv", "mozliwosci", [n.wiersz_m(id="M-0001", mozliwosc="Pierwsza wersja treści")])
    b = n.zapisz("b.csv", "mozliwosci", [n.wiersz_m(id="M-0001", mozliwosc="Druga wersja treści")])
    wyjscie = n.katalog / "wyjscie.csv"
    stare = b'"stara";"zawartosc"\r\nnie ruszac\n'
    wyjscie.write_bytes(stare)
    kod, _, _ = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), a, b)
    assert kod == 1
    assert wyjscie.read_bytes() == stare


def test_k08_bledne_dane_partii_blokuja_wyjscie(n):
    a = n.zapisz("a.csv", "mozliwosci", [n.wiersz_m(id="", obszar="nieznany obszar")])
    wyjscie = n.katalog / "wyjscie.csv"
    kod, _, err = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), a)
    assert kod == 1
    assert not wyjscie.exists()
    assert any(d["plik"] == a and d["wiersz"] == "2" and d["kolumna"] == "obszar" for d in n.linie_bledow(err))


# ---------------------------------------------------------------- K09 — wynik


def test_k09_wyjscie_posortowane_i_poprawne(n, rejestry):
    a = n.zapisz("a.csv", "mozliwosci", [
        n.wiersz_m(id="M-0040", mozliwosc="Czterdziesta możliwość"),
        n.wiersz_m(id="", mozliwosc="Nowa bez numeru"),
        n.wiersz_m(id="M-0002", mozliwosc="Druga możliwość"),
    ])
    b = n.zapisz("b.csv", "mozliwosci", [n.wiersz_m(id="M-0011", mozliwosc="Jedenasta możliwość"), n.wiersz_m(id="M-0001", mozliwosc="Pierwsza możliwość")])
    wyjscie = str(n.katalog / "wynik.csv")
    kod, _, _ = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", wyjscie, a, b)
    assert kod == 0
    wiersze, _ = rejestry.scal_pliki([a, b], "mozliwosci")
    assert [w["id"] for w in wiersze] == ["M-0001", "M-0002", "M-0011", "M-0040", "M-0041"]
    assert rejestry.sprawdz_plik(wyjscie, "mozliwosci").poprawny is True
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", wyjscie)
    assert kod == 0
    assert err.strip() == ""


def test_k09_pola_zachowane_bez_zmian(n, rejestry):
    pelny = n.wiersz_m(
        id="",
        mozliwosc="  Treść z odstępami na brzegach  ",
        obszar="kod i gry",
        zrodlo="źródło: rozmowa 3",
        data_zrodla="2024-02-29",
        kotwica="#kotwica-1",
        stare_studio="częściowo",
        dowod_stare_studio="zrzut ekranu",
        poziom_waznosci="pierwszy miesiąc",
        test_odbioru="uruchomić i porównać",
        kandydaci="K-0001, K-0002",
        status="ocenione",
        partia="P7",
        uwagi="  uwaga z odstępem ",
    )
    a = n.zapisz("a.csv", "mozliwosci", [pelny])
    wiersze, wynik = rejestry.scal_pliki([a], "mozliwosci")
    assert wynik.poprawny is True
    assert wiersze == [{**pelny, "id": "M-0001"}]
    wyjscie = n.katalog / "wynik.csv"
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), a)[0] == 0
    assert wyjscie.read_bytes() == n.format_wyjscia("mozliwosci", [{**pelny, "id": "M-0001"}])


def test_k09_sam_rejestr_bez_partii_bajt_w_bajt(n):
    wiersze = [
        n.wiersz_k(id="K-0001", nazwa="Pierwszy", mozliwosci="M-0001,M-0002", dowod="z dokumentacji"),
        n.wiersz_k(id="K-0002", nazwa="Drugi \"w cudzysłowie\"", poziom_dostepu="agent w piaskownicy"),
        n.wiersz_k(id="K-0010", nazwa="Dziesiąty; ze średnikiem", poprzedni_werdykt="odrzucony", data_werdyktu="2025-01-31"),
    ]
    r = n.zapisz("rejestr.csv", "kandydaci", wiersze)  # zapis z cytowaniem minimalnym
    wyjscie = n.katalog / "wynik.csv"
    kod, _, _ = n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyjscie), "--rejestr", r)
    assert kod == 0
    oczekiwane = n.format_wyjscia("kandydaci", wiersze)
    assert wyjscie.read_bytes() == oczekiwane
    # rejestr już w formacie wyjściowym przechodzi przez scalanie bez żadnej zmiany
    r2 = n.katalog / "rejestr2.csv"
    r2.write_bytes(oczekiwane)
    wyjscie2 = n.katalog / "wynik2.csv"
    assert n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyjscie2), "--rejestr", str(r2))[0] == 0
    assert wyjscie2.read_bytes() == oczekiwane


def test_k09_scalenie_nadpisuje_istniejacy_plik_wyjsciowy(n):
    a = n.zapisz("a.csv", "mozliwosci", [n.wiersz_m(id="M-0001")])
    wyjscie = n.katalog / "wynik.csv"
    wyjscie.write_bytes(b"stara tresc\n")
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), a)[0] == 0
    assert wyjscie.read_bytes() == n.format_wyjscia("mozliwosci", [n.wiersz_m(id="M-0001")])


# ---------------------------------------------------------------- K10 — ostrzeżenia o powtórzonej treści


def test_k10_ostrzezenie_przy_sprawdzaniu_wskazuje_oba_wiersze(n, rejestry):
    wiersze = n.wiersze_m(3) + [
        n.wiersz_m(id="M-0004", mozliwosc="Podsumowanie poczty rano."),  # wiersz 5
        n.wiersz_m(id="M-0005", mozliwosc="Inna, całkiem odrębna treść"),
        n.wiersz_m(id="M-0006", mozliwosc="podsumowanie  POCZTY\trano"),  # wiersz 7
    ]
    plik = n.zapisz("p.csv", "mozliwosci", wiersze)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is True
    assert list(wynik.bledy) == []
    assert len(wynik.ostrzezenia) == 1
    tekst = n.pelny(wynik.ostrzezenia[0]).replace(str(n.katalog), "")
    assert _liczba(tekst, 5) and _liczba(tekst, 7)
    kod, out, _ = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", "--json", plik)
    assert kod == 0
    dane = json.loads(out)
    assert dane["poprawny"] is True
    assert len(dane["ostrzezenia"]) == 1
    assert set(dane["ostrzezenia"][0]) == {"plik", "wiersz", "kolumna", "opis"}


def test_k10_ostrzezenie_dla_nazwy_kandydata(n, rejestry):
    plik = n.zapisz("k.csv", "kandydaci", [
        n.wiersz_k(id="K-0001", nazwa="Notatnik Pro"),
        n.wiersz_k(id="K-0002", nazwa="notatnik   pro."),
    ])
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert wynik.poprawny is True
    assert len(wynik.ostrzezenia) == 1
    tekst = n.pelny(wynik.ostrzezenia[0]).replace(str(n.katalog), "")
    assert _liczba(tekst, 2) and _liczba(tekst, 3)


def test_k10_brak_ostrzezenia_dla_roznej_tresci(n, rejestry):
    plik = n.zapisz("k.csv", "mozliwosci", [
        n.wiersz_m(id="M-0001", mozliwosc="Podsumowanie poczty rano"),
        n.wiersz_m(id="M-0002", mozliwosc="Podsumowanie poczty wieczorem"),
        n.wiersz_m(id="M-0003", mozliwosc="Podsumowanie.poczty rano"),
        n.wiersz_m(id="M-0004", mozliwosc="Podsumowanie pocztyrano"),
        n.wiersz_m(id="M-0005", mozliwosc="Podsumowanie poczty ranoX"),
    ])
    assert list(rejestry.sprawdz_plik(plik, "mozliwosci").ostrzezenia) == []
    plik_k = n.zapisz("kk.csv", "kandydaci", [n.wiersz_k(id="K-0001", nazwa="Notatnik"), n.wiersz_k(id="K-0002", nazwa="Notatniki")])
    assert list(rejestry.sprawdz_plik(plik_k, "kandydaci").ostrzezenia) == []


def test_k10_ostrzezenie_przy_scalaniu_i_raport(n, rejestry):
    a = n.zapisz("partia_a.csv", "mozliwosci", [
        n.wiersz_m(id="", mozliwosc="Kopia zapasowa notatek"),
        n.wiersz_m(id="", mozliwosc="Zupełnie inna możliwość"),
    ])
    b = n.zapisz("partia_b.csv", "mozliwosci", [
        n.wiersz_m(id="", mozliwosc="Trzecia, niezależna treść"),
        n.wiersz_m(id="", mozliwosc="KOPIA zapasowa   notatek."),
    ])
    wiersze, wynik = rejestry.scal_pliki([a, b], "mozliwosci")
    assert wynik.poprawny is True
    assert len(wiersze) == 4
    assert len(wynik.ostrzezenia) == 1
    tekst = n.pelny(wynik.ostrzezenia[0]).replace(str(n.katalog), "")
    assert "partia_a.csv" in tekst and "partia_b.csv" in tekst
    assert _liczba(tekst, 2) and _liczba(tekst, 3)

    wyjscie = n.katalog / "wynik.csv"
    raport = n.katalog / "raport.txt"
    kod, _, _ = n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), "--raport", str(raport), a, b)
    assert kod == 0
    assert wyjscie.exists()
    linie = [linia for linia in raport.read_text("utf-8").splitlines() if linia.strip()]
    assert len(linie) == 1
    linia = linie[0].replace(str(n.katalog), "")
    assert "partia_a.csv" in linia and "partia_b.csv" in linia


def test_k10_raport_wiele_ostrzezen_po_jednym_w_wierszu(n):
    a = n.zapisz("a.csv", "kandydaci", [
        n.wiersz_k(id="K-0001", nazwa="Alfa"),
        n.wiersz_k(id="K-0002", nazwa="Beta"),
        n.wiersz_k(id="K-0003", nazwa="alfa."),
        n.wiersz_k(id="K-0004", nazwa="BETA"),
        n.wiersz_k(id="K-0005", nazwa="Gamma"),
    ])
    wyjscie = n.katalog / "wynik.csv"
    raport = n.katalog / "raport.txt"
    kod, out, _ = n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyjscie), "--raport", str(raport), "--json", a)
    assert kod == 0
    dane = json.loads(out)
    assert dane["poprawny"] is True
    assert len(dane["ostrzezenia"]) == 2
    linie = [linia for linia in raport.read_text("utf-8").splitlines() if linia.strip()]
    assert len(linie) == 2
    assert any(_liczba(linia.replace(str(n.katalog), ""), 2) and _liczba(linia.replace(str(n.katalog), ""), 4) for linia in linie)
    assert any(_liczba(linia.replace(str(n.katalog), ""), 3) and _liczba(linia.replace(str(n.katalog), ""), 5) for linia in linie)


# ---------------------------------------------------------------- K11 — format


def test_k11_bom_na_wejsciu_przyjety_i_nie_trafia_na_wyjscie(n, rejestry):
    wiersz = n.wiersz_m(id="M-0001")
    plik = n.zapisz("bom.csv", "mozliwosci", [wiersz], bom=True)
    assert rejestry.sprawdz_plik(plik, "mozliwosci").poprawny is True
    assert n.uruchom("sprawdz", "--rodzaj", "mozliwosci", plik)[0] == 0
    r = n.zapisz("bom_r.csv", "kandydaci", [n.wiersz_k()], bom=True)
    assert rejestry.sprawdz_plik(r, "kandydaci").poprawny is True
    wyjscie = n.katalog / "wynik.csv"
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), plik)[0] == 0
    dane = wyjscie.read_bytes()
    assert not dane.startswith(b"\xef\xbb\xbf")
    assert b"\xef\xbb\xbf" not in dane
    assert dane == n.format_wyjscia("mozliwosci", [wiersz])


def test_k11_pola_ze_srednikiem_cudzyslowem_i_nowym_wierszem(n, rejestry):
    wiersz = n.wiersz_m(
        id="M-0001",
        mozliwosc='Treść; ze średnikiem i "cudzysłowem"',
        uwagi='pierwsza linia\ndruga linia; "cytat" ""podwójny""',
        test_odbioru="a;b;c",
        zrodlo='"w całości w cudzysłowie"',
    )
    plik = n.zapisz("znaki.csv", "mozliwosci", [wiersz, n.wiersz_m(id="", mozliwosc="Wiersz po polu wielowierszowym")])
    wiersze, wynik = rejestry.scal_pliki([plik], "mozliwosci")
    assert wynik.poprawny is True
    assert wiersze[0] == wiersz
    assert wiersze[1]["id"] == "M-0002"
    wyjscie = n.katalog / "wynik.csv"
    assert n.uruchom("scal", "--rodzaj", "mozliwosci", "--wyjscie", str(wyjscie), plik)[0] == 0
    oczekiwane = n.format_wyjscia("mozliwosci", wiersze)
    assert wyjscie.read_bytes() == oczekiwane
    assert b'"pierwsza linia\ndruga linia; ""cytat"" """"podw\xc3\xb3jny"""""' in oczekiwane


def test_k11_wszystkie_pola_w_cudzyslowach_i_konce_lf(n):
    a = n.zapisz("a.csv", "kandydaci", [n.wiersz_k(id="K-0001", nazwa="Ab"), n.wiersz_k(id="", nazwa="Cd", koszt="")])
    wyjscie = n.katalog / "wynik.csv"
    assert n.uruchom("scal", "--rodzaj", "kandydaci", "--wyjscie", str(wyjscie), a)[0] == 0
    dane = wyjscie.read_bytes()
    assert b"\r" not in dane
    assert dane.endswith(b"\n") and not dane.endswith(b"\n\n")
    linie = dane.decode("utf-8").split("\n")[:-1]
    assert len(linie) == 3
    assert linie[0] == ";".join(f'"{k}"' for k in n.NAGLOWEK_K)
    for linia in linie:
        pola = linia.split(";")
        assert len(pola) == len(n.NAGLOWEK_K)
        assert all(p.startswith('"') and p.endswith('"') and len(p) >= 2 for p in pola)
    assert linie[2].startswith('"K-0002";"Cd";"narzędzie";"";')


def test_k11_wejscie_z_cudzyslowami_i_bom_sprawdzane_poprawnie(n, rejestry):
    tekst = "﻿" + n.format_wyjscia("mozliwosci", [n.wiersz_m(mozliwosc='Średnik; i "cudzysłów"', uwagi="linia\nkolejna")]).decode("utf-8")
    plik = n.zapisz_tekst("cytowany.csv", tekst)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert wynik.poprawny is True
    kod, out, _ = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", "--json", plik)
    assert kod == 0
    assert json.loads(out)["wiersze"] == 1
