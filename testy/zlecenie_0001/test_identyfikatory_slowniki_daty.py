"""Zlecenie 0001 — K03 (identyfikatory), K04 (słowniki), K05 (zależności), K06 (daty).

SZKIC AI — do pracy autora.
"""

from __future__ import annotations

import re

import pytest

# ---------------------------------------------------------------- K03 — identyfikatory


@pytest.mark.parametrize("zly", ["M-001", "M-00001", "m-0001", "K-0001", "M0001", "M-000a", " M-0001", "M-0001 ", "M_0001", "MM-0001"])
def test_k03_zly_wzorzec_id_mozliwosci(n, rejestry, zly):
    wiersze = [n.wiersz_m(id="M-0001"), n.wiersz_m(id=zly, mozliwosc="Inna możliwość testowa")]
    if zly.strip() == "M-0001":
        wiersze[0]["id"] = "M-0002"
    plik = n.zapisz("id.csv", "mozliwosci", wiersze)
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == {(3, "id")}
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci", partia=True)) == {(3, "id")}


@pytest.mark.parametrize("zly", ["K-001", "K-00001", "k-0001", "M-0001", "K0001", "K-00x1"])
def test_k03_zly_wzorzec_id_kandydatow(n, rejestry, zly):
    plik = n.zapisz("id.csv", "kandydaci", [n.wiersz_k(id=zly)])
    assert n.pary(rejestry.sprawdz_plik(plik, "kandydaci")) == {(2, "id")}


def test_k03_poprawne_wzorce_id(n, rejestry):
    wiersze = [n.wiersz_m(id=i, mozliwosc=f"Możliwość o numerze {i}") for i in ("M-0000", "M-0001", "M-9999", "M-0420")]
    assert rejestry.sprawdz_plik(n.zapisz("m.csv", "mozliwosci", wiersze), "mozliwosci").poprawny is True
    wiersze_k = [n.wiersz_k(id=i, nazwa=f"Kandydat {i}") for i in ("K-0000", "K-9999")]
    assert rejestry.sprawdz_plik(n.zapisz("k.csv", "kandydaci", wiersze_k), "kandydaci").poprawny is True


def test_k03_powtorzone_id_przy_drugim_i_kolejnym_wystapieniu(n, rejestry):
    wiersze = n.wiersze_m(11)  # wiersze 2..12
    wiersze.append(n.wiersz_m(id="M-0077", mozliwosc="Pierwsze wystąpienie M-0077"))  # wiersz 13
    wiersze.append(n.wiersz_m(id="M-0012", mozliwosc="Zwykły wiersz czternasty"))  # wiersz 14
    wiersze.append(n.wiersz_m(id="M-0077", mozliwosc="Drugie wystąpienie identyfikatora"))  # wiersz 15
    wiersze.append(n.wiersz_m(id="M-0077", mozliwosc="Trzecie wystąpienie identyfikatora"))  # wiersz 16
    plik = n.zapisz("powt.csv", "mozliwosci", wiersze)
    wynik = rejestry.sprawdz_plik(plik, "mozliwosci")
    assert n.pary(wynik) == {(15, "id"), (16, "id")}
    for blad in wynik.bledy:
        assert re.search(r"(?<!\d)13(?!\d)", blad.opis), blad.opis


def test_k03_powtorzone_id_kandydatow(n, rejestry):
    wiersze = [
        n.wiersz_k(id="K-0005", nazwa="Pierwszy"),
        n.wiersz_k(id="K-0006", nazwa="Drugi"),
        n.wiersz_k(id="K-0005", nazwa="Trzeci"),
    ]
    plik = n.zapisz("powt.csv", "kandydaci", wiersze)
    wynik = rejestry.sprawdz_plik(plik, "kandydaci")
    assert n.pary(wynik) == {(4, "id")}
    assert re.search(r"(?<!\d)2(?!\d)", wynik.bledy[0].opis)


def test_k03_pusty_id_dozwolony_tylko_w_partii(n, rejestry):
    wiersze = [
        n.wiersz_m(id="", mozliwosc="Pierwsza bez numeru"),
        n.wiersz_m(id="M-0003", mozliwosc="Z numerem trzecim"),
        n.wiersz_m(id="", mozliwosc="Druga bez numeru"),
    ]
    plik = n.zapisz("partia.csv", "mozliwosci", wiersze)
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci", partia=True)) == set()
    assert rejestry.sprawdz_plik(plik, "mozliwosci", partia=True).poprawny is True
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == {(2, "id"), (4, "id")}
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci", partia=False)) == {(2, "id"), (4, "id")}


def test_k03_pusty_id_w_partii_cli(n):
    plik = n.zapisz("partia_k.csv", "kandydaci", [n.wiersz_k(id=""), n.wiersz_k(id="", nazwa="Kolejny")])
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "kandydaci", "--partia", plik)
    assert kod == 0
    assert err.strip() == ""
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "kandydaci", plik)
    assert kod == 1
    assert {(int(d["wiersz"]), d["kolumna"]) for d in n.linie_bledow(err)} == {(2, "id"), (3, "id")}


# ---------------------------------------------------------------- K04 — słowniki

OBSZARY = [
    "asystent codzienny", "praca nocna i samodzielna", "pisanie i redakcja", "gra fabularna", "media", "kod i gry",
    "wiedza i notatki", "telefon i nadzór", "bezpieczeństwo i kopie", "sprzęt i system", "firma", "dziesiątka",
    "jakość i testy", "inne",
]
STARE_STUDIO = ["tak", "częściowo", "nie", "nie wiadomo"]
POZIOMY = ["rdzeń", "pierwszy miesiąc", "później", "odrzucone"]
STATUSY = ["zebrane", "scalone", "ocenione"]
RODZAJE = ["model", "wtyczka", "narzędzie", "system", "metoda", "własny składnik"]
DOWODY = ["sprawdzone na PC", "z dokumentacji", "nieznane"]
DOSTEPY = ["tylko Qba", "agent za zgodą", "agent w piaskownicy", "agent z siecią"]

SLOWNIKI_M = {"obszar": OBSZARY, "stare_studio": STARE_STUDIO, "poziom_waznosci": [""] + POZIOMY, "status": STATUSY}
SLOWNIKI_K = {
    "rodzaj": RODZAJE,
    "dowod": [""] + DOWODY,
    "poziom_waznosci": [""] + POZIOMY,
    "poziom_dostepu": [""] + DOSTEPY,
    "status": STATUSY,
}


@pytest.mark.parametrize(("kolumna", "wartosc"), [(k, w) for k, ws in SLOWNIKI_M.items() for w in ws])
def test_k04_kazda_wartosc_slownika_mozliwosci_przyjeta(n, rejestry, kolumna, wartosc):
    wiersz = n.wiersz_m(dowod_stare_studio="dowód testowy", **{kolumna: wartosc})
    plik = n.zapisz("sl.csv", "mozliwosci", [wiersz])
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == set()


@pytest.mark.parametrize(("kolumna", "wartosc"), [(k, w) for k, ws in SLOWNIKI_K.items() for w in ws])
def test_k04_kazda_wartosc_slownika_kandydatow_przyjeta(n, rejestry, kolumna, wartosc):
    plik = n.zapisz("sl.csv", "kandydaci", [n.wiersz_k(**{kolumna: wartosc})])
    assert n.pary(rejestry.sprawdz_plik(plik, "kandydaci")) == set()


def _zle_warianty(wartosci: list[str]) -> list[str]:
    dobre = [w for w in wartosci if w]
    return ["spoza słownika", " " + dobre[0], dobre[0] + " ", dobre[-1].upper(), dobre[-1].capitalize() if dobre[-1] != dobre[-1].capitalize() else dobre[-1] + "x"]


ZLE_M = [(k, z) for k, ws in SLOWNIKI_M.items() for z in _zle_warianty(ws)] + [
    ("obszar", "telefon i nadzor"),
    ("obszar", "bezpieczenstwo i kopie"),
    ("stare_studio", "czesciowo"),
    ("poziom_waznosci", "rdzen"),
    ("poziom_waznosci", "pozniej"),
    ("obszar", ""),
    ("stare_studio", ""),
    ("status", ""),
]
ZLE_K = [(k, z) for k, ws in SLOWNIKI_K.items() for z in _zle_warianty(ws)] + [
    ("rodzaj", "narzedzie"),
    ("rodzaj", "wlasny skladnik"),
    ("dowod", "sprawdzone na pc"),
    ("poziom_dostepu", "tylko qba"),
    ("poziom_dostepu", "agent z siecia"),
    ("rodzaj", ""),
    ("status", ""),
]


@pytest.mark.parametrize(("kolumna", "wartosc"), ZLE_M)
def test_k04_wartosc_spoza_slownika_mozliwosci(n, rejestry, kolumna, wartosc):
    wiersze = n.wiersze_m(2)
    for w in wiersze:
        w["dowod_stare_studio"] = "dowód testowy"
    wiersze[1][kolumna] = wartosc
    plik = n.zapisz("zle.csv", "mozliwosci", wiersze)
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == {(3, kolumna)}


@pytest.mark.parametrize(("kolumna", "wartosc"), ZLE_K)
def test_k04_wartosc_spoza_slownika_kandydatow(n, rejestry, kolumna, wartosc):
    plik = n.zapisz("zle.csv", "kandydaci", [n.wiersz_k(id="K-0001"), n.wiersz_k(id="K-0002", nazwa="Drugi", **{kolumna: wartosc})])
    assert n.pary(rejestry.sprawdz_plik(plik, "kandydaci")) == {(3, kolumna)}


def test_k04_slownik_rejestru_nie_obowiazuje_w_drugim(n, rejestry):
    # wartość ze słownika `dowod` kandydatów nie jest wartością `stare_studio` możliwości i odwrotnie
    plik_m = n.zapisz("m.csv", "mozliwosci", [n.wiersz_m(stare_studio="nieznane")])
    assert n.pary(rejestry.sprawdz_plik(plik_m, "mozliwosci")) == {(2, "stare_studio")}
    plik_k = n.zapisz("k.csv", "kandydaci", [n.wiersz_k(dowod="nie wiadomo")])
    assert n.pary(rejestry.sprawdz_plik(plik_k, "kandydaci")) == {(2, "dowod")}
    plik_k2 = n.zapisz("k2.csv", "kandydaci", [n.wiersz_k(rodzaj="media")])
    assert n.pary(rejestry.sprawdz_plik(plik_k2, "kandydaci")) == {(2, "rodzaj")}


def test_k04_bledy_slownikowe_cli_format(n):
    wiersze = [n.wiersz_m(id="M-0001", obszar="Media"), n.wiersz_m(id="M-0002", mozliwosc="Druga możliwość", status=" zebrane")]
    plik = n.zapisz("cli.csv", "mozliwosci", wiersze)
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", plik)
    assert kod == 1
    linie = [linia for linia in err.splitlines() if linia.strip()]
    assert len(linie) == 2
    assert any(linia.startswith(f"{plik}:2: obszar: ") for linia in linie)
    assert any(linia.startswith(f"{plik}:3: status: ") for linia in linie)


# ---------------------------------------------------------------- K05 — zależności między polami


@pytest.mark.parametrize(("stare", "dowod", "blad"), [
    ("tak", "", True),
    ("częściowo", "", True),
    ("nie", "", False),
    ("nie wiadomo", "", False),
    ("tak", "zrzut ekranu", False),
    ("częściowo", "notatka", False),
    ("nie", "coś jednak jest", False),
])
def test_k05_dowod_stare_studio(n, rejestry, stare, dowod, blad):
    plik = n.zapisz("ss.csv", "mozliwosci", [n.wiersz_m(stare_studio=stare, dowod_stare_studio=dowod)])
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == ({(2, "dowod_stare_studio")} if blad else set())


@pytest.mark.parametrize(("poprzedni", "data", "blad"), [
    ("odrzucony", "", True),
    ("x", "", True),
    ("odrzucony", "2025-06-01", False),
    ("", "", False),
    ("", "2025-06-01", False),
])
def test_k05_data_werdyktu_przy_poprzednim_werdykcie(n, rejestry, poprzedni, data, blad):
    plik = n.zapisz("w.csv", "kandydaci", [n.wiersz_k(poprzedni_werdykt=poprzedni, data_werdyktu=data)])
    assert n.pary(rejestry.sprawdz_plik(plik, "kandydaci")) == ({(2, "data_werdyktu")} if blad else set())


@pytest.mark.parametrize("lista", ["", "K-0001", "K-0001,K-0002", "K-0001, K-0002", "K-0001 ,K-0002", "K-0001,  K-0002, K-0003"])
def test_k05_poprawna_lista_kandydatow(n, rejestry, lista):
    plik = n.zapisz("l.csv", "mozliwosci", [n.wiersz_m(kandydaci=lista)])
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == set()


@pytest.mark.parametrize("lista", ["K-0001,,K-0002", "K-0001,", ",K-0001", ",", "K-001", "K-0001,M-0001", "K-0001;K-0002", "K-0001 K-0002", "k-0001", "K-0001, ,K-0002"])
def test_k05_zla_lista_kandydatow(n, rejestry, lista):
    plik = n.zapisz("l.csv", "mozliwosci", [n.wiersz_m(id="M-0001"), n.wiersz_m(id="M-0002", mozliwosc="Druga możliwość", kandydaci=lista)])
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == {(3, "kandydaci")}


@pytest.mark.parametrize("lista", ["", "M-0001", "M-0001,M-0002", "M-0009,M-0010,M-0011"])
def test_k05_poprawna_lista_mozliwosci(n, rejestry, lista):
    plik = n.zapisz("l.csv", "kandydaci", [n.wiersz_k(mozliwosci=lista)])
    assert n.pary(rejestry.sprawdz_plik(plik, "kandydaci")) == set()


@pytest.mark.parametrize("lista", ["M-0001,,M-0002", "M-0001,", "M-01", "K-0001", "M-0001,K-0002", "m-0001"])
def test_k05_zla_lista_mozliwosci(n, rejestry, lista):
    plik = n.zapisz("l.csv", "kandydaci", [n.wiersz_k(mozliwosci=lista)])
    assert n.pary(rejestry.sprawdz_plik(plik, "kandydaci")) == {(2, "mozliwosci")}


# ---------------------------------------------------------------- K06 — daty

DOBRE_DATY = ["2024-02-29", "2026-01-01", "2026-12-31", "2000-02-29", "2026-04-30"]
ZLE_DATY = [
    "2026-02-30", "2023-02-29", "1900-02-29", "2026-04-31", "2026-13-01", "2026-00-10", "2026-01-00", "2026-01-32",
    "2026-1-05", "2026-01-5", "26-01-05", "2026/01/05", "20260105", "2026-01-05 ", " 2026-01-05", "2026-01-05T00:00",
    "05-01-2026", "dzisiaj", "2026-W01-1",
]


@pytest.mark.parametrize("data", DOBRE_DATY)
def test_k06_poprawna_data(n, rejestry, data):
    plik_m = n.zapisz("d.csv", "mozliwosci", [n.wiersz_m(data_zrodla=data)])
    assert n.pary(rejestry.sprawdz_plik(plik_m, "mozliwosci")) == set()
    plik_k = n.zapisz("dk.csv", "kandydaci", [n.wiersz_k(data_zrodla=data, poprzedni_werdykt="odrzucony", data_werdyktu=data)])
    assert n.pary(rejestry.sprawdz_plik(plik_k, "kandydaci")) == set()


@pytest.mark.parametrize("data", ZLE_DATY)
def test_k06_zla_data_zrodla_mozliwosci(n, rejestry, data):
    plik = n.zapisz("d.csv", "mozliwosci", [n.wiersz_m(id="M-0001"), n.wiersz_m(id="M-0002", mozliwosc="Druga możliwość", data_zrodla=data)])
    assert n.pary(rejestry.sprawdz_plik(plik, "mozliwosci")) == {(3, "data_zrodla")}


@pytest.mark.parametrize("data", ZLE_DATY)
def test_k06_zla_data_kandydatow(n, rejestry, data):
    plik = n.zapisz("d.csv", "kandydaci", [n.wiersz_k(data_zrodla=data)])
    assert n.pary(rejestry.sprawdz_plik(plik, "kandydaci")) == {(2, "data_zrodla")}
    plik_w = n.zapisz("w.csv", "kandydaci", [n.wiersz_k(poprzedni_werdykt="odrzucony", data_werdyktu=data)])
    assert n.pary(rejestry.sprawdz_plik(plik_w, "kandydaci")) == {(2, "data_werdyktu")}
    plik_bez = n.zapisz("wb.csv", "kandydaci", [n.wiersz_k(poprzedni_werdykt="", data_werdyktu=data)])
    assert n.pary(rejestry.sprawdz_plik(plik_bez, "kandydaci")) == {(2, "data_werdyktu")}


def test_k06_bledy_dat_cli(n):
    wiersze = [n.wiersz_m(id="M-0001", data_zrodla="2026-02-30"), n.wiersz_m(id="M-0002", mozliwosc="Druga możliwość", data_zrodla="2024-02-29")]
    plik = n.zapisz("cli.csv", "mozliwosci", wiersze)
    kod, _, err = n.uruchom("sprawdz", "--rodzaj", "mozliwosci", plik)
    assert kod == 1
    linie = [linia for linia in err.splitlines() if linia.strip()]
    assert len(linie) == 1
    assert linie[0].startswith(f"{plik}:2: data_zrodla: ")
