"""Bramki sędziego: każdy krok zwraca wynik z liczbami i krótkim opisem."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from . import sciezki
from .mutacje import ma_funkcje, mutuj
from .narzedzia import (
    BladUzycia,
    BrakNarzedzia,
    Przebieg,
    git,
    nazwa_testu,
    ogon,
    skanuj_sekrety,
    uruchom_pytest,
    wymagaj,
    zbierz_testy,
)

POZYTYWNY, NEGATYWNY, POMINIETY = "pozytywny", "negatywny", "pominiety"
ILE_PRZEBIEGOW = 3
ILE_SZCZEGOLOW = 15
CZERWONE = ("failed", "error")


@dataclass
class Krok:
    nazwa: str
    wynik: str
    opis: str
    liczby: dict[str, float] = field(default_factory=dict)
    szczegoly: list[str] = field(default_factory=list)


@dataclass
class Kontekst:
    korzen: Path
    tryb: str
    plik_wyroku: Path
    zlecenie: str | None = None
    baza: str | None = None
    galaz: str | None = None
    prog: float = 70.0
    z_mutacjami: bool = False
    baza_commit: str | None = None
    zmiany: dict[str, list[str]] = field(default_factory=dict)
    zebrane: list[str] = field(default_factory=list)

    @property
    def testy_zlecenia(self) -> str:
        return f"testy/zlecenie_{self.zlecenie}"


def _krok(nazwa: str, dobrze: bool, opis: str, liczby: dict | None = None, szczegoly: list[str] | None = None) -> Krok:
    szczegoly = szczegoly or []
    if len(szczegoly) > ILE_SZCZEGOLOW:
        szczegoly = [*szczegoly[:ILE_SZCZEGOLOW], f"… i {len(szczegoly) - ILE_SZCZEGOLOW} kolejnych"]
    return Krok(nazwa, POZYTYWNY if dobrze else NEGATYWNY, opis, liczby or {}, szczegoly)


def plik_zlecenia(k: Kontekst) -> Path:
    pliki = sorted((k.korzen / "zlecenia").glob(f"{k.zlecenie}-*.md"))
    if len(pliki) != 1:
        raise BladUzycia(f"oczekiwano dokładnie jednego pliku zlecenia zlecenia/{k.zlecenie}-*.md, znaleziono {len(pliki)}")
    return pliki[0]


def kryteria(k: Kontekst) -> list[str]:
    """Identyfikatory kryteriów odbioru: wiersze zlecenia zaczynające się od „- **Knn”."""
    return list(dict.fromkeys(re.findall(r"^- \*\*(K\d+)\b", plik_zlecenia(k).read_text("utf-8"), flags=re.M)))


def _bez_testu(k: Kontekst, testy: list[str]) -> list[str]:
    """Kryteria, dla których żaden z podanych testów nie ma nazwy test_knn_…"""
    nazwy = [nazwa_testu(t) for t in testy]
    return [kr for kr in kryteria(k) if not any(n.startswith(f"test_{kr.lower()}_") for n in nazwy)]


def ochrona_sciezek(k: Kontekst) -> list[Krok]:
    pliki_bazy = set(git(k.korzen, "ls-tree", "-r", "--name-only", "-z", k.baza_commit).split("\0"))
    naruszenia = [
        f"{sciezka} ({', '.join(zrodla)}): {powod}"
        for sciezka, zrodla in k.zmiany.items()
        if (powod := sciezki.naruszenie(k.tryb, k.zlecenie, sciezka, k.korzen, pliki_bazy))
    ]
    if k.galaz and sciezki.rozpoznaj_galaz(k.galaz) != (k.tryb, k.zlecenie):
        oczekiwana = f"{k.tryb}/{k.zlecenie}-opis" if k.zlecenie else f"{k.tryb}/opis"
        naruszenia.insert(0, f"gałąź „{k.galaz}” nie pasuje do trybu; oczekiwana nazwa: {oczekiwana}")
    dozwolone = sciezki.DOZWOLONE[k.tryb].format(zlecenie=k.zlecenie)
    opis = f"zmiany poza dozwolonym zakresem ({dozwolone})" if naruszenia else f"zmiany w dozwolonym zakresie ({dozwolone})"
    if not k.galaz:
        opis += "; nazwa gałęzi niesprawdzona (HEAD odłączony)"
    return [_krok("ochrona_sciezek", not naruszenia, opis, {"zmienione": len(k.zmiany), "niedozwolone": len(naruszenia)}, naruszenia)]


def zbieranie(k: Kontekst) -> list[Krok]:
    katalog = k.korzen / k.testy_zlecenia
    bledy = []
    for plik in sorted(katalog.rglob("*.py")) if katalog.is_dir() else []:
        try:
            compile(plik.read_bytes(), str(plik), "exec", dont_inherit=True)
        except (SyntaxError, ValueError) as blad:
            bledy.append(f"{plik.relative_to(k.korzen).as_posix()}: {blad}")
    kod, k.zebrane, wyjscie = zbierz_testy(k.korzen, k.testy_zlecenia)
    if kod != 0:
        bledy += ogon(wyjscie, 8)
    dobrze = not bledy and bool(k.zebrane)
    opis = f"zebrane testy z {k.testy_zlecenia}: {len(k.zebrane)}"
    if not dobrze:
        opis += " — pliki muszą się kompilować i dać zebrać bez kodu zlecenia (importy kodu wewnątrz testów albo fixture)"
    return [_krok("zbieranie_testow", dobrze, opis, {"testy": len(k.zebrane), "bledy": len(bledy)}, bledy)]


def pokrycie_kryteriow(k: Kontekst) -> list[Krok]:
    wszystkie = kryteria(k)
    brak = _bez_testu(k, k.zebrane)
    if not wszystkie:
        opis = "zlecenie nie ma kryteriów w postaci „- **Knn — …”"
    elif brak:
        opis = f"kryteria bez zebranego testu o nazwie test_knn_…: {', '.join(brak)}"
    else:
        opis = f"każde kryterium ma zebrany test (kryteria: {len(wszystkie)})"
    return [_krok("pokrycie_kryteriow", bool(wszystkie) and not brak, opis, {"kryteria": len(wszystkie), "bez_testu": len(brak)})]


def _przebiegi(k: Kontekst) -> list[Przebieg]:
    return [uruchom_pytest(k.korzen, [k.testy_zlecenia]) for _ in range(ILE_PRZEBIEGOW)]


def _stabilnosc(przebiegi: list[Przebieg]) -> Krok:
    testy = sorted({t for p in przebiegi for t in p.wyniki})
    rozne = [t for t in testy if len({p.wyniki.get(t, "brak") for p in przebiegi}) > 1]
    opis = "wyniki testów różnią się między przebiegami" if rozne else f"przebiegi ({ILE_PRZEBIEGOW}) dały identyczny wynik każdego testu"
    if not testy:
        opis = "brak wyników testów do porównania"
    szczegoly = [f"{t}: {' / '.join(p.wyniki.get(t, 'brak') for p in przebiegi)}" for t in rozne]
    return _krok("stabilnosc", bool(testy) and not rozne, opis, {"przebiegi": ILE_PRZEBIEGOW, "testy": len(testy), "niestabilne": len(rozne)}, szczegoly)


def czerwone_i_stabilne(k: Kontekst) -> list[Krok]:
    """Tryb „testy”: bez kodu zlecenia testy muszą nie przechodzić (kod wyjścia pytest 1 albo 2)."""
    przebiegi = _przebiegi(k)
    kody = [p.kod for p in przebiegi]
    wyniki = przebiegi[0].wyniki
    czerwone = [t for t, stan in wyniki.items() if stan in CZERWONE]
    zielone = sorted(t for t, stan in wyniki.items() if stan not in CZERWONE)
    bez_czerwonego = _bez_testu(k, czerwone)
    dobrze = all(kod in (1, 2) for kod in kody)
    if dobrze:
        opis = f"testy nie przechodzą na obecnym kodzie (czerwone: {len(czerwone)} z {len(wyniki)})"
    elif 0 in kody:
        opis = "testy przechodzą bez kodu zlecenia — niczego nie sprawdzają"
    else:
        opis = f"pytest zakończył się kodami {kody}; oczekiwany kod 1 albo 2"
    szczegoly = [f"uwaga — kryteria bez czerwonego testu: {', '.join(bez_czerwonego)}"] if bez_czerwonego else []
    szczegoly += [f"uwaga — test zielony już na bazie: {t} ({wyniki[t]})" for t in zielone]
    if not dobrze and 0 not in kody:
        szczegoly += ogon(przebiegi[0].wyjscie)
    liczby = {"testy": len(wyniki), "czerwone": len(czerwone), "zielone_na_bazie": len(zielone), "kryteria_bez_czerwonego_testu": len(bez_czerwonego)}
    return [_krok("czerwone_na_bazie", dobrze, opis, liczby, szczegoly), _stabilnosc(przebiegi)]


def testy_zlecenia(k: Kontekst) -> list[Krok]:
    """Tryb „kod”: każdy test zlecenia ma wynik „passed” w każdym przebiegu."""
    przebiegi = _przebiegi(k)
    kody = [p.kod for p in przebiegi]
    wyniki = przebiegi[0].wyniki
    niezielone = sorted({f"{t}: {stan}" for p in przebiegi for t, stan in p.wyniki.items() if stan != "passed"})
    dobrze = kody == [0] * ILE_PRZEBIEGOW and bool(wyniki) and not niezielone
    if dobrze:
        opis = f"testy zlecenia zielone we wszystkich przebiegach (testy: {len(wyniki)})"
    elif not wyniki:
        opis = f"brak wyników testów z {k.testy_zlecenia} (kody wyjścia pytest: {kody})"
    else:
        opis = f"testy zlecenia nie są zielone (niezielone: {len(niezielone)}; test pominięty niczego nie dowodzi)"
    zly = next((p for p in przebiegi if p.kod != 0), None)
    szczegoly = niezielone + (ogon(zly.wyjscie) if zly else [])
    return [_krok("testy_zlecenia", dobrze, opis, {"testy": len(wyniki), "niezielone": len(niezielone)}, szczegoly), _stabilnosc(przebiegi)]


def _zestaw(przebieg: Przebieg) -> Krok:
    stany = list(przebieg.wyniki.values())
    zle = sorted(f"{t}: {stan}" for t, stan in przebieg.wyniki.items() if stan in CZERWONE)
    dobrze = przebieg.kod == 0 and bool(stany)  # kod 0 bez raportu wyników to nie jest zielony zestaw
    opis = f"cały zestaw (pytest testy/): testy {len(stany)}, czerwone {len(zle)}, kod wyjścia pytest {przebieg.kod}"
    if przebieg.kod == 0 and not stany:
        opis += " — brak raportu wyników (pytest przerwany przed końcem?)"
    liczby = {"testy": len(stany), "czerwone": len(zle), "pominiete": stany.count("skipped")}
    return _krok("caly_zestaw", dobrze, opis, liczby, zle + ([] if dobrze else ogon(przebieg.wyjscie)))


def caly_zestaw(k: Kontekst) -> list[Krok]:
    return [_zestaw(uruchom_pytest(k.korzen, ["testy"]))]


def zestaw_zasad(k: Kontekst) -> list[Krok]:
    """Tryb „zasady”: jeden przebieg całego zestawu; testy sędziego (testy/sedzia) rozliczane osobno."""
    przebieg = uruchom_pytest(k.korzen, ["testy"])
    sedziego = {t: stan for t, stan in przebieg.wyniki.items() if t.startswith("testy.sedzia.")}
    zle = sorted(f"{t}: {stan}" for t, stan in sedziego.items() if stan != "passed")
    opis = f"testy sędziego (testy/sedzia): {len(sedziego)}, niezielone: {len(zle)}"
    if not sedziego:
        opis = "brak wyników testów sędziego z testy/sedzia"
    krok = _krok("testy_sedziego", bool(sedziego) and not zle, opis, {"testy": len(sedziego), "niezielone": len(zle)}, zle)
    return [krok, _zestaw(przebieg)]


def sekrety(k: Kontekst) -> list[Krok]:
    wymagaj("detect_secrets")
    if not (k.korzen / ".secrets.baseline").is_file():
        return [_krok("sekrety", False, "brak pliku .secrets.baseline — skan nie ma wzorca")]
    kandydaci = git(k.korzen, "ls-files", "-z").split("\0") if k.tryb == "calosc" else list(k.zmiany)
    pliki = [p for p in kandydaci if p and p != ".secrets.baseline" and (k.korzen / p).is_file()]
    czysto, znaleziska = skanuj_sekrety(k.korzen, pliki) if pliki else (True, [])
    zakres = "wszystkie śledzone pliki" if k.tryb == "calosc" else "zmienione pliki"
    opis = f"skan sekretów ({zakres}): pliki {len(pliki)}, nowe znaleziska {len(znaleziska)}"
    return [_krok("sekrety", czysto, opis, {"pliki": len(pliki), "znaleziska": len(znaleziska)}, znaleziska)]


def mutacje(k: Kontekst) -> list[Krok]:
    wymagaj("mutmut")
    if k.tryb == "calosc":
        if not ma_funkcje(k.korzen / "src"):
            return [_krok("mutacje", True, "w src/ nie ma jeszcze żadnej funkcji — nie ma czego mutować", {"wszystkie": 0})]
        return [_krok("mutacje", *mutuj(k.korzen, None, "testy", k.prog))]
    w_src = [s for s in k.zmiany if s.startswith("src/")]
    pliki = [s for s in w_src if s.endswith(".py") and (k.korzen / s).is_file()]
    if not pliki:
        opis = f"brak plików .py do mutowania wśród zmian w src/ (zmienione ścieżki w src/: {len(w_src)})"
        return [_krok("mutacje", False, opis, {"wszystkie": 0})]
    return [_krok("mutacje", *mutuj(k.korzen, pliki, k.testy_zlecenia, k.prog))]


# Tryb → kroki (nazwa, funkcja, czy kosztowny). Krok kosztowny jest pomijany po wcześniejszym negatywnym.
TRYBY = {
    "testy": [
        ("ochrona_sciezek", ochrona_sciezek, False),
        ("zbieranie_testow", zbieranie, False),
        ("pokrycie_kryteriow", pokrycie_kryteriow, False),
        ("czerwone_na_bazie", czerwone_i_stabilne, False),
        ("sekrety", sekrety, False),
    ],
    "kod": [
        ("ochrona_sciezek", ochrona_sciezek, False),
        ("testy_zlecenia", testy_zlecenia, False),
        ("caly_zestaw", caly_zestaw, False),
        ("sekrety", sekrety, False),
        ("mutacje", mutacje, True),
    ],
    "zasady": [("ochrona_sciezek", ochrona_sciezek, False), ("testy_sedziego", zestaw_zasad, False), ("sekrety", sekrety, False)],
    "calosc": [("caly_zestaw", caly_zestaw, False), ("sekrety", sekrety, False), ("mutacje", mutacje, True)],
}


def wykonaj(k: Kontekst) -> list[Krok]:
    kroki: list[Krok] = []
    for nazwa, funkcja, kosztowny in TRYBY[k.tryb]:
        if nazwa == "mutacje" and k.tryb == "calosc" and not k.z_mutacjami:
            continue
        if kosztowny and any(krok.wynik != POZYTYWNY for krok in kroki):
            kroki.append(Krok(nazwa, POMINIETY, "krok kosztowny pominięty, bo wcześniejszy krok jest negatywny"))
            continue
        try:
            kroki += funkcja(k)
        except BrakNarzedzia as blad:
            kroki.append(Krok(nazwa, NEGATYWNY, f"brak wymaganego narzędzia: {blad} — zainstaluj przypięte zależności (README.md)"))
        except subprocess.TimeoutExpired as blad:
            kroki.append(Krok(nazwa, NEGATYWNY, f"przekroczony limit czasu {blad.timeout:g} s"))
    return kroki
