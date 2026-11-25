"""Testy sędziego. Każdy buduje tymczasowe repozytorium git i uruchamia sędziego podprocesem.

Litery w nazwach odpowiadają przypadkom wymaganym w dokumentacja/PETLA_INZYNIERSKA.md.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

KORZEN = Path(__file__).resolve().parents[2]
PLIK_TESTOW = "testy/zlecenie_0001/test_liczenie.py"
PLIK_KODU = "src/fabruna/liczenie.py"
TESTY = ("testy", "--zlecenie", "0001", "--baza", "main")
KOD = ("kod", "--zlecenie", "0001", "--baza", "main")

TESTY_DOBRE = '''\
import subprocess
import sys

import pytest


def test_k01_suma():
    from fabruna.liczenie import suma

    assert suma([1, 2, 3]) == 6
    assert suma([]) == 0


def test_k01_suma_z_wiersza_polecen(srodowisko_podprocesu):
    polecenie = [sys.executable, "-m", "fabruna.liczenie", "2", "3"]
    wynik = subprocess.run(polecenie, capture_output=True, text=True, env=srodowisko_podprocesu)
    assert wynik.stdout.strip() == "5"


def test_k02_srednia():
    from fabruna.liczenie import srednia

    assert srednia([1, 2, 6]) == 3
    with pytest.raises(ValueError, match="^pusta lista$"):
        srednia([])


def test_k01_kod_importuje_tylko_biblioteke_standardowa(katalog_src):
    import ast

    drzewo = ast.parse((katalog_src / "fabruna" / "liczenie.py").read_text("utf-8"))
    importy = {alias.name for wezel in ast.walk(drzewo) if isinstance(wezel, ast.Import) for alias in wezel.names}
    importy |= {wezel.module for wezel in ast.walk(drzewo) if isinstance(wezel, ast.ImportFrom)}
    assert importy == {"argparse"}
'''

TESTY_SLABE = '''\
def test_k01_suma():
    from fabruna.liczenie import suma

    assert suma([]) == 0


def test_k02_srednia():
    from fabruna.liczenie import srednia

    assert srednia([4]) is not None
'''

TESTY_ZIELONE_BEZ_KODU = "def test_k01_nic():\n    assert True\n\n\ndef test_k02_nic():\n    assert 1 + 1 == 2\n"

TEST_NIESTABILNY = '''

def test_k02_raz_czerwony_raz_zielony():
    from pathlib import Path

    licznik = Path(LICZNIK_PROBY)
    numer = int(licznik.read_text()) + 1 if licznik.exists() else 1
    licznik.write_text(str(numer))
    assert numer % 2 == 0
'''

KOD_DOBRY = '''\
import argparse


def suma(liczby):
    wynik = 0
    for liczba in liczby:
        wynik += liczba
    return wynik


def srednia(liczby):
    if not liczby:
        raise ValueError("pusta lista")
    return suma(liczby) / len(liczby)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("liczby", nargs="*", type=int)
    print(suma(parser.parse_args().liczby))
'''


def galaz_testow(repo, tresc: str = TESTY_DOBRE) -> None:
    repo.galaz("testy/0001-liczenie")
    repo.zapisz(PLIK_TESTOW, tresc)
    repo.zatwierdz("testy zlecenia 0001")


def galaz_kodu(repo, testy: str = TESTY_DOBRE, kod: str = KOD_DOBRY) -> None:
    """Testy zlecenia trafiają na main, potem powstaje gałąź z kodem."""
    repo.zapisz(PLIK_TESTOW, testy)
    repo.zatwierdz("testy zlecenia 0001")
    repo.galaz("kod/0001-liczenie")
    repo.zapisz(PLIK_KODU, kod)
    repo.zatwierdz("kod zlecenia 0001")


def negatywny_tylko(wynik, *nazwy: str) -> None:
    """Wyrok jest negatywny, a negatywne są dokładnie wskazane kroki — nie inne, przypadkowe."""
    assert wynik.kod == 1, wynik.wyjscie
    assert wynik.wyrok["wyrok"] == "negatywny"
    assert {nazwa for nazwa, stan in wynik.kroki.items() if stan == "negatywny"} == set(nazwy), wynik.wyjscie
    assert "WYROK: NEGATYWNY" in wynik.wyjscie


def falszywy_klucz() -> str:
    # Sklejany w locie, żeby skan sekretów tego repozytorium nie znalazł go w pliku testów.
    return "AKIA" + "IOSFODNN7" + "EXAMPLE"


def test_a_tryb_testy_sciezka_szczesliwa(repo):
    galaz_testow(repo)
    wynik = repo.sedzia(*TESTY)
    assert wynik.kod == 0, wynik.wyjscie
    assert (wynik.wyrok["wyrok"], wynik.wyrok["tryb"], wynik.wyrok["zlecenie"], wynik.wyrok["baza"]) == ("pozytywny", "testy", "0001", "main")
    assert list(wynik.kroki) == ["ochrona_sciezek", "zakazy", "zbieranie_testow", "pokrycie_kryteriow", "czerwone_na_bazie", "stabilnosc", "sekrety", "nienaruszalnosc"]
    assert set(wynik.kroki.values()) == {"pozytywny"}
    assert wynik.wyrok["drzewo_czyste"] is True
    assert wynik.krok("czerwone_na_bazie")["liczby"] == {"testy": 4, "czerwone": 4, "zielone_na_bazie": 0, "kryteria_bez_czerwonego_testu": 0}
    assert wynik.krok("stabilnosc")["liczby"] == {"przebiegi": 3, "testy": 4, "niestabilne": 0}
    assert "WYROK: POZYTYWNY" in wynik.wyjscie


def test_a_wyrok_odnotowuje_zmiany_niezatwierdzone(repo):
    galaz_testow(repo)
    repo.zapisz("testy/zlecenie_0001/test_dodatkowy.py", "def test_k01_dodatkowy():\n    assert False\n")
    wynik = repo.sedzia(*TESTY)
    assert (wynik.kod, wynik.wyrok["drzewo_czyste"]) == (0, False), wynik.wyjscie
    assert "drzewo robocze: ze zmianami niezatwierdzonymi" in wynik.wyjscie


def test_b_galaz_testow_zmienia_src(repo):
    galaz_testow(repo)
    repo.zapisz("src/fabruna/stare.py", "def podwoj(liczba):\n    return liczba + liczba\n")
    repo.zatwierdz("zmiana kodu na gałęzi testów")
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "ochrona_sciezek")
    assert wynik.krok("ochrona_sciezek")["szczegoly"] == ["src/fabruna/stare.py (commit): poza testy/zlecenie_0001/"]


def test_c_kryterium_bez_testu(repo):
    galaz_testow(repo, TESTY_DOBRE.replace("test_k02_srednia", "test_srednia"))
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "pokrycie_kryteriow")
    assert wynik.krok("pokrycie_kryteriow")["opis"].endswith(": K02")
    assert wynik.krok("pokrycie_kryteriow")["liczby"] == {"kryteria": 2, "bez_testu": 1}


def test_d_testy_zielone_na_bazie(repo):
    galaz_testow(repo, TESTY_ZIELONE_BEZ_KODU)
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "czerwone_na_bazie")
    assert "niczego nie sprawdzają" in wynik.krok("czerwone_na_bazie")["opis"]


def test_e_test_niestabilny(repo, tmp_path):
    licznik = f"\nLICZNIK_PROBY = {str(tmp_path / 'licznik.txt')!r}\n"
    galaz_testow(repo, TESTY_DOBRE + licznik + TEST_NIESTABILNY)
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "stabilnosc")
    assert wynik.krok("stabilnosc")["liczby"] == {"przebiegi": 3, "testy": 5, "niestabilne": 1}
    assert wynik.krok("stabilnosc")["szczegoly"][0].endswith("test_k02_raz_czerwony_raz_zielony: failed / passed / failed")


@pytest.mark.wolny
def test_f_tryb_kod_sciezka_szczesliwa(repo):
    galaz_kodu(repo)
    wynik = repo.sedzia(*KOD)
    assert wynik.kod == 0, wynik.wyjscie
    assert list(wynik.kroki) == ["ochrona_sciezek", "zakazy", "testy_zlecenia", "stabilnosc", "caly_zestaw", "sekrety", "mutacje", "nienaruszalnosc"]
    assert set(wynik.kroki.values()) == {"pozytywny"}
    liczby = wynik.krok("mutacje")["liczby"]
    assert liczby["wszystkie"] >= 8 and liczby["prog_proc"] == 70
    # Mutowany jest tylko plik zmieniony względem bazy: mutanty z fabruna/stare.py byłyby „bez testu”.
    assert (liczby["zabite"], liczby["bez_testu"], liczby["ocalale"]) == (liczby["wszystkie"], 0, 0)
    assert liczby["wynik_proc"] == 100


def test_g_galaz_kodu_zmienia_testy(repo):
    galaz_kodu(repo)
    repo.zapisz(PLIK_TESTOW, TESTY_SLABE)
    repo.zatwierdz("osłabienie testów przez wykonawcę")
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "ochrona_sciezek")
    assert wynik.krok("ochrona_sciezek")["szczegoly"] == [f"{PLIK_TESTOW} (commit): poza src/"]
    assert wynik.kroki["mutacje"] == "pominiety"


@pytest.mark.parametrize("sciezka", ["sedzia/kroki.py", "pyproject.toml", "zlecenia/0001-liczenie.md"])
def test_h_galaz_kodu_zmienia_sedziego_albo_zasady(repo, sciezka):
    galaz_kodu(repo)
    repo.dopisz(sciezka, "\n# dopisek wykonawcy\n")
    repo.zatwierdz("zmiana poza zakresem wykonawcy")
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "ochrona_sciezek")
    assert wynik.krok("ochrona_sciezek")["szczegoly"] == [f"{sciezka} (commit): poza src/"]


def test_i_czerwony_test_zlecenia(repo):
    galaz_kodu(repo, kod=KOD_DOBRY.replace("wynik += liczba", "wynik -= liczba"))
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "testy_zlecenia", "caly_zestaw")
    assert wynik.krok("testy_zlecenia")["liczby"] == {"testy": 4, "niezielone": 3}
    assert wynik.kroki["mutacje"] == "pominiety"


def test_j_regresja_poza_zleceniem(repo):
    galaz_kodu(repo)
    repo.zapisz("src/fabruna/stare.py", "def podwoj(liczba):\n    return 3 * liczba\n")
    repo.zatwierdz("zepsucie istniejącego kodu")
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "caly_zestaw")
    assert wynik.kroki["testy_zlecenia"] == "pozytywny"
    assert wynik.krok("caly_zestaw")["szczegoly"][0] == "testy.istniejace.test_stare::test_podwoj: failed"
    assert wynik.kroki["mutacje"] == "pominiety"


@pytest.mark.wolny
def test_k_slabe_testy_wynik_mutacyjny_ponizej_progu(repo):
    # Mocne testy spoza katalogów zleceń nie mogą podnieść wyniku: liczą się wyłącznie testy zleceń.
    repo.zapisz("testy/inne/test_mocne.py", TESTY_DOBRE)
    galaz_kodu(repo, testy=TESTY_SLABE)
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "mutacje")
    liczby = wynik.krok("mutacje")["liczby"]
    oceniane = liczby["wszystkie"] - liczby["pominiete"]
    assert liczby["wynik_proc"] == round(100 * (liczby["zabite"] + liczby["przekroczony_czas"]) / oceniane, 1)
    assert 0 < liczby["wynik_proc"] < 70 and liczby["ocalale"] > 0
    niezabite = wynik.krok("mutacje")["szczegoly"]
    assert len(niezabite) == liczby["ocalale"] + liczby["bez_testu"], "wyrok wskazuje każdego niezabitego mutanta"
    assert all(wiersz.startswith("fabruna.liczenie.") for wiersz in niezabite)
    # Wyrok niesie różnicę każdego niezabitego mutanta — materiał dla autora testów i recenzenta.
    assert all("\n-" in wiersz and "\n+" in wiersz for wiersz in niezabite), niezabite
    assert any("\n-        wynik += liczba" in wiersz for wiersz in niezabite)
    assert "@@" not in wynik.wyjscie, "na ekranie tylko nazwy mutantów, różnice są w wyrok.json"
    # Ten sam kod i testy przechodzą, gdy próg leży poniżej zmierzonego wyniku: decyduje wyłącznie próg.
    nizszy = repo.sedzia(*KOD, "--prog-mutacji", str(liczby["wynik_proc"] - 1))
    assert nizszy.kod == 0, nizszy.wyjscie


def test_k_testy_innego_zlecenia_licza_sie_do_mutacji(repo):
    # Zlecenie poprawek zmienia kod opisany testami wcześniejszego zlecenia: te testy zabijają mutanty starej logiki.
    repo.zapisz("testy/zlecenie_0000/test_mocne.py", TESTY_DOBRE)
    galaz_kodu(repo, testy=TESTY_SLABE)
    wynik = repo.sedzia(*KOD)
    assert wynik.kod == 0, wynik.wyjscie
    assert "testy: testy/zlecenie_0000, testy/zlecenie_0001" in wynik.krok("mutacje")["opis"]


@pytest.mark.parametrize("dopisek", ["", "  # pragma: allowlist secret"])
def test_l_falszywy_sekret(repo, dopisek):
    galaz_kodu(repo, kod=KOD_DOBRY + f'\nKLUCZ = "{falszywy_klucz()}"{dopisek}\n')
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "sekrety")
    wiersz = len(KOD_DOBRY.splitlines()) + 2
    assert wynik.krok("sekrety")["szczegoly"] == [f"{PLIK_KODU}:{wiersz} — AWS Access Key"]
    assert falszywy_klucz() not in wynik.wyjscie + json.dumps(wynik.wyrok), "sędzia nie powiela treści sekretu"


@pytest.mark.parametrize(
    ("tryb", "sciezka", "do_indeksu", "zrodlo"),
    [
        ("testy", "notatki.txt", False, "plik nieśledzony"),
        ("kod", "pyproject.toml", False, "zmiana niezatwierdzona"),
        ("kod", "sedzia/dodatek.py", True, "zmiana niezatwierdzona"),
    ],
)
def test_m_zmiana_niezatwierdzona_albo_plik_niesledzony(repo, tryb, sciezka, do_indeksu, zrodlo):
    (galaz_testow if tryb == "testy" else galaz_kodu)(repo)
    repo.dopisz(sciezka, "# dopisek poza commitami\n")
    if do_indeksu:
        repo.git("add", sciezka)
    wynik = repo.sedzia(*(TESTY if tryb == "testy" else KOD))
    negatywny_tylko(wynik, "ochrona_sciezek")
    assert wynik.krok("ochrona_sciezek")["szczegoly"][0].startswith(f"{sciezka} ({zrodlo}): poza ")


def test_n_sedzia_z_bazy_ocenia_galaz_ktora_podmienila_sedziego(repo, tmp_path):
    galaz_kodu(repo)
    repo.zapisz("sedzia/__main__.py", "raise SystemExit(0)\n")
    repo.zatwierdz("sędzia zawsze na tak")
    assert repo.sedzia(*KOD).kod == 0, "podmieniony sędzia ocenia sam siebie — dlatego CI bierze sędziego z bazy"
    with tarfile.open(fileobj=io.BytesIO(repo.git("archive", "--format=tar", "main", "sedzia"))) as archiwum:
        archiwum.extractall(tmp_path / "baza", filter="data")
    wynik = repo.sedzia(*KOD, opcje=("-P",), srodowisko={"PYTHONPATH": str(tmp_path / "baza")})
    negatywny_tylko(wynik, "ochrona_sciezek")
    assert wynik.krok("ochrona_sciezek")["szczegoly"] == ["sedzia/__main__.py (commit): poza src/"]


def test_o_brak_narzedzi_to_wyrok_negatywny(repo, tmp_path):
    subprocess.run([sys.executable, "-m", "venv", "--without-pip", str(tmp_path / "gole")], check=True)
    galaz_testow(repo)
    wynik = repo.sedzia(*TESTY, python=str(tmp_path / "gole" / "bin" / "python"))
    assert wynik.kod == 1, wynik.wyjscie
    assert wynik.kroki["ochrona_sciezek"] == "pozytywny"
    for nazwa, narzedzie in (("zbieranie_testow", "pytest"), ("czerwone_na_bazie", "pytest"), ("sekrety", "detect_secrets")):
        assert wynik.kroki[nazwa] == "negatywny"
        assert f"brak wymaganego narzędzia: {narzedzie}" in wynik.krok(nazwa)["opis"]


def test_p_tryb_wyznaczony_z_nazwy_galezi(repo):
    galaz_testow(repo)
    wynik = repo.sedzia("galaz", "testy/0001-liczenie", "--baza", "main")
    assert (wynik.kod, wynik.wyrok["tryb"], wynik.wyrok["zlecenie"]) == (0, "testy", "0001"), wynik.wyjscie
    negatywny_tylko(repo.sedzia("galaz", "rozne-poprawki", "--baza", "main"), "rodzaj_galezi")
    # Gałąź z samymi testami oceniana jako „kod” (i odwrotnie) pada na ochronie ścieżek.
    assert repo.sedzia("galaz", "kod/0001-liczenie", "--baza", "main").kroki["ochrona_sciezek"] == "negatywny"
    assert repo.sedzia("kod", "--zlecenie", "0001", "--baza", "main").kroki["ochrona_sciezek"] == "negatywny"


def test_q_galaz_testow_nie_podmienia_istniejacych_testow(repo):
    repo.zapisz(PLIK_TESTOW, TESTY_DOBRE)
    repo.zatwierdz("testy zlecenia 0001 na main")
    repo.galaz("testy/0001-poprawka")
    repo.zapisz(PLIK_TESTOW, TESTY_SLABE)
    repo.zatwierdz("podmiana testów na słabsze")
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "ochrona_sciezek")
    assert "istniejącego pliku testów" in wynik.krok("ochrona_sciezek")["szczegoly"][0]


def test_r_tryb_zasady(repo):
    repo.galaz("zasady/porzadki")
    repo.zapisz("dokumentacja/NOTATKA.md", "# Notatka\n")
    repo.zapisz("src/fabruna/nowy/__init__.py")
    repo.zatwierdz("porządki")
    wynik = repo.sedzia("zasady", "--baza", "main")
    assert wynik.kod == 0, wynik.wyjscie
    assert list(wynik.kroki) == ["ochrona_sciezek", "testy_sedziego", "caly_zestaw", "sekrety"]
    repo.zapisz("src/fabruna/nowy/__init__.py", "def przemycona():\n    return 1\n")
    repo.zatwierdz("kod przemycony gałęzią zasad")
    negatywny_tylko(repo.sedzia("zasady", "--baza", "main"), "ochrona_sciezek")


def test_s_tryb_calosc_na_main(repo):
    wynik = repo.sedzia("galaz", "main")
    assert (wynik.kod, wynik.wyrok["tryb"]) == (0, "calosc"), wynik.wyjscie
    assert wynik.kroki == {"caly_zestaw": "pozytywny", "sekrety": "pozytywny"}
    assert wynik.krok("sekrety")["liczby"]["pliki"] >= 10


@pytest.mark.wolny
def test_t_tryb_calosc_z_mutacjami_calego_src(repo):
    wynik = repo.sedzia("calosc", "--mutacje")
    assert wynik.kod == 0, wynik.wyjscie
    assert wynik.krok("mutacje")["liczby"]["wszystkie"] >= 1
    assert wynik.krok("mutacje")["liczby"]["wynik_proc"] == 100


@pytest.mark.parametrize(
    "argumenty",
    [
        ("testy", "--zlecenie", "0009", "--baza", "main"),
        ("testy", "--zlecenie", "0001", "--baza", "nie-ma-takiej-galezi"),
        ("testy", "--zlecenie", "1", "--baza", "main"),
        ("kod", "--zlecenie", "0001"),
        ("galaz", "kod/0001-liczenie"),
    ],
)
def test_u_blad_uzycia_to_kod_2_bez_wyroku(repo, argumenty):
    wynik = repo.sedzia(*argumenty)
    assert wynik.kod == 2, wynik.wyjscie
    assert wynik.wyrok is None


@pytest.mark.parametrize(
    ("stare", "nowe"),
    [
        ("wynik += liczba", "wynik += liczba  # pragma: no mutate"),
        ("wynik += liczba", "wynik += liczba if 'MUTANT_UNDER_TEST' else liczba"),
        ("wynik += liczba", "wynik += liczba if 'pytest' not in sys.modules else liczba"),
    ],
)
def test_v_kod_nie_wylacza_mutacji_i_nie_rozpoznaje_narzedzi_sedziego(repo, stare, nowe):
    galaz_kodu(repo, kod=KOD_DOBRY.replace(stare, nowe))
    wynik = repo.sedzia(*KOD)
    if "pragma" not in nowe:
        # Rozpoznanie narzędzi sędziego zatrzymuje już krok „zakazy”; mutacje są wtedy pomijane.
        assert wynik.kod == 1 and wynik.kroki["zakazy"] == "negatywny", wynik.wyjscie
        assert wynik.kroki["mutacje"] == "pominiety"
        return
    negatywny_tylko(wynik, "mutacje")
    assert wynik.krok("mutacje")["liczby"] == {"niedozwolone_odwolania": 1}
    assert wynik.krok("mutacje")["szczegoly"] == [f"{PLIK_KODU}:7"]


def test_u_blad_uzycia_nie_zostawia_starego_wyroku(repo):
    galaz_testow(repo)
    assert repo.sedzia(*TESTY).kod == 0
    assert (repo.katalog / "wyrok.json").is_file()
    wynik = repo.sedzia("testy", "--zlecenie", "0009", "--baza", "main")
    assert wynik.kod == 2 and wynik.wyrok is None, "stary wyrok pozytywny nie może przetrwać nieudanego przebiegu"


@pytest.mark.parametrize(
    ("sciezka", "negatywne"),
    [
        ("src/fabruna/stare.py", {"caly_zestaw"}),
        (PLIK_KODU, {"testy_zlecenia", "stabilnosc", "caly_zestaw"}),
    ],
)
def test_v_przerwany_pytest_z_kodem_zero_nie_jest_zielony(repo, sciezka, negatywne):
    galaz_kodu(repo)
    repo.zapisz(sciezka, "import os\n\n\ndef podwoj(liczba):\n    os._exit(0)\n\n\ndef suma(liczby):\n    os._exit(0)\n")
    repo.zatwierdz("kod, który kończy proces testów kodem zero")
    negatywny_tylko(repo.sedzia(*KOD), *negatywne, "zakazy")


def test_m_przeniesienie_pliku_testow_do_src_nie_ukrywa_zmiany(repo):
    galaz_kodu(repo)
    repo.git("mv", PLIK_TESTOW, "src/fabruna/test_liczenie.py")
    repo.zatwierdz("plik testów przeniesiony do src/")
    wynik = repo.sedzia(*KOD)
    assert wynik.kod == 1 and wynik.kroki["ochrona_sciezek"] == "negatywny", wynik.wyjscie
    assert wynik.krok("ochrona_sciezek")["szczegoly"] == [f"{PLIK_TESTOW} (commit): poza src/"]


def test_p_nazwa_galezi_musi_pasowac_do_trybu_i_zlecenia(repo):
    repo.zapisz(PLIK_TESTOW, TESTY_DOBRE)
    repo.zatwierdz("testy zlecenia 0001")
    repo.galaz("kod/0002-inne-zlecenie")
    repo.zapisz(PLIK_KODU, KOD_DOBRY)
    repo.zatwierdz("kod na gałęzi innego zlecenia")
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "ochrona_sciezek")
    assert wynik.krok("ochrona_sciezek")["szczegoly"] == ["gałąź „kod/0002-inne-zlecenie” nie pasuje do trybu; oczekiwana nazwa: kod/0001-opis"]


def test_w_pominiety_test_zlecenia_nie_jest_zielony(repo):
    z_pominieciem = TESTY_DOBRE.replace("def test_k02_srednia():", '@pytest.mark.skip(reason="później")\ndef test_k02_srednia():')
    galaz_kodu(repo, testy=z_pominieciem)
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "testy_zlecenia")
    assert wynik.krok("testy_zlecenia")["szczegoly"] == ["testy.zlecenie_0001.test_liczenie::test_k02_srednia: skipped"]


def test_x_plik_testow_ktorego_nie_da_sie_zebrac(repo):
    galaz_testow(repo, "from fabruna.liczenie import suma\n\n" + TESTY_DOBRE)
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "zbieranie_testow", "pokrycie_kryteriow")
    assert wynik.krok("zbieranie_testow")["liczby"]["testy"] == 0


def test_y_fixture_srodowisko_podprocesu_wskazuje_src_tego_drzewa(srodowisko_podprocesu):
    polecenie = [sys.executable, "-c", "import fabruna; print(fabruna.__file__)"]
    wynik = subprocess.run(polecenie, capture_output=True, text=True, env=srodowisko_podprocesu, cwd="/", check=True)
    assert Path(wynik.stdout.strip()) == KORZEN / "src" / "fabruna" / "__init__.py"


def test_z_wzor_wyniku_mutacyjnego():
    # (zabite + przekroczony czas) / (wszystkie − pominięte): (6 + 1) / (11 − 1) = 70%; brak mutantów → None
    kod = (
        "from sedzia.mutacje import wynik_mutacyjny as w;"
        "print(w(dict(total=11, skipped=1, killed=6, timeout=1)), w(dict(total=3, skipped=3, killed=0, timeout=0)))"
    )
    wynik = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, cwd=KORZEN, check=True)
    assert wynik.stdout.split() == ["70.0", "None"]


def test_b_zmiany_na_bazie_po_rozgalezieniu_nie_obciazaja_galezi(repo):
    galaz_testow(repo)
    repo.git("switch", "-q", "main")
    repo.zapisz("dokumentacja/NOWE.md", "# Zmiana na main po rozgałęzieniu\n")
    repo.zatwierdz("zmiana na main")
    repo.git("switch", "-q", "testy/0001-liczenie")
    wynik = repo.sedzia(*TESTY)
    assert wynik.kod == 0, wynik.wyjscie
    assert wynik.krok("ochrona_sciezek")["liczby"] == {"zmienione": 1, "niedozwolone": 0}


@pytest.mark.parametrize(
    ("tresc", "negatywne"),
    [("def test_atrapa():\n    assert False\n", {"testy_sedziego", "caly_zestaw"}), (None, {"testy_sedziego"})],
)
def test_r_tryb_zasady_wymaga_zielonych_testow_sedziego(repo, tresc, negatywne):
    repo.galaz("zasady/zmiana-testow-sedziego")
    if tresc is None:
        repo.git("rm", "-q", "testy/sedzia/test_atrapa.py")
    else:
        repo.zapisz("testy/sedzia/test_atrapa.py", tresc)
    repo.zatwierdz("zmiana testów sędziego")
    negatywny_tylko(repo.sedzia("zasady", "--baza", "main"), *negatywne)


def test_f_galaz_kodu_bez_zmian_w_plikach_py_nie_ma_czego_mutowac(repo):
    repo.zapisz(PLIK_TESTOW, TESTY_DOBRE)
    repo.zapisz(PLIK_KODU, KOD_DOBRY)
    repo.zatwierdz("testy i kod zlecenia 0001 już na main")
    repo.galaz("kod/0001-same-dane")
    repo.zapisz("src/fabruna/dane.txt", "1 2 3\n")
    repo.zatwierdz("same dane, bez kodu")
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "mutacje")
    assert wynik.krok("mutacje")["liczby"] == {"wszystkie": 0}


def test_t_tryb_calosc_z_mutacjami_gdy_w_src_nie_ma_funkcji(repo):
    repo.git("rm", "-q", "src/fabruna/stare.py", "testy/istniejace/test_stare.py")
    repo.zatwierdz("pusty pakiet, jak w szkielecie repozytorium")
    wynik = repo.sedzia("calosc", "--mutacje")
    assert wynik.kod == 0, wynik.wyjscie
    assert (wynik.kroki["mutacje"], wynik.krok("mutacje")["liczby"]) == ("pozytywny", {"wszystkie": 0})


TESTY_TYLKO_PODPROCESEM = '''\
import subprocess
import sys


def test_k01_suma_z_wiersza_polecen(srodowisko_podprocesu):
    polecenie = [sys.executable, "-m", "fabruna.liczenie", "2", "3"]
    wynik = subprocess.run(polecenie, capture_output=True, text=True, env=srodowisko_podprocesu)
    assert wynik.stdout.strip() == "5"


def test_k02_tez_tylko_podprocesem(srodowisko_podprocesu):
    polecenie = [sys.executable, "-m", "fabruna.liczenie", "4"]
    wynik = subprocess.run(polecenie, capture_output=True, text=True, env=srodowisko_podprocesu)
    assert wynik.stdout.strip() == "4"
'''


@pytest.mark.wolny
def test_k_testy_tylko_przez_podproces_nie_zabijaja_mutantow(repo):
    galaz_kodu(repo, testy=TESTY_TYLKO_PODPROCESEM)
    wynik = repo.sedzia(*KOD)
    negatywny_tylko(wynik, "mutacje")
    assert "mutmut przerwał pracę" in wynik.krok("mutacje")["opis"]


@pytest.mark.parametrize(
    "kod",
    [
        "import atexit\n\n\ndef suma(liczby):\n    atexit.register(print)\n    return sum(liczby)\n",
        "import sys\n\n\ndef suma(liczby):\n    return sum(liczby) if sys.argv else 0\n",
        "def suma(liczby):\n    return getattr(liczby, 'co' + 'kolwiek', sum)(liczby)\n",
        "def suma(liczby):\n    return eval('sum')(liczby)\n",
    ],
)
def test_x_kod_nie_siega_do_procesu_ani_pytest(repo, kod):
    """Konstrukcje, którymi kod pod testem mógłby podrobić raport pytest (atexit + os._exit, sys.argv…)."""
    galaz_kodu(repo, kod=KOD_DOBRY + "\n\n" + kod.replace("def suma", "def suma_2"))
    wynik = repo.sedzia(*KOD)
    assert wynik.kod == 1 and wynik.kroki["zakazy"] == "negatywny", wynik.wyjscie


def test_x_testy_nie_rejestruja_hookow_pytest(repo):
    galaz_testow(repo, TESTY_DOBRE + "\n\ndef pytest_runtest_makereport(item, call):\n    return None\n")
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "zakazy")


def test_x_testy_zmieniajace_repozytorium_w_trakcie_oceny(repo):
    zapis = "\n\ndef test_k01_podrzuca_plik():\n    from pathlib import Path\n    (Path(__file__).parents[2] / 'podrzucony.py').write_text('')\n    assert False\n"
    galaz_testow(repo, TESTY_DOBRE + zapis)
    wynik = repo.sedzia(*TESTY)
    negatywny_tylko(wynik, "nienaruszalnosc")
    assert wynik.krok("nienaruszalnosc")["szczegoly"] == ["podrzucony.py"]
