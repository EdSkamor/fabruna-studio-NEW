"""Usługa sędziego na PC: jedyna droga gałęzi z sesji AI do GitHuba.

SZKIC AI — do pracy autora.

Działa na osobnym koncie systemowym `sedzia`, które jako jedyne ma token GitHuba.
Sesje AI (konto właściciela) nie mają żadnego dostępu do zapisu w repozytorium;
oddają gałąź jako plik `git bundle` do katalogu kolejki (`sedzia/pc/zglos.sh`).

Dla każdego zgłoszenia usługa:
1. bierze `main` z GitHuba i gałąź z pliku do czystego repozytorium, którego nie widzi żaden kod gałęzi;
2. sama, niezależnie od kodu w repozytorium, sprawdza nazwę gałęzi i zmienione ścieżki;
3. uruchamia sędziego z `main` (nie z gałęzi) w piaskownicy bwrap: bez sieci, bez katalogów domowych,
   bez tokenu, z sędzią i środowiskiem Pythona tylko do odczytu;
4. przy wyroku pozytywnym wypycha dokładnie oceniony commit, otwiera pull request i — dla gałęzi
   `testy/…` i `kod/…` — włącza automatyczne scalenie (GitHub scala dopiero po zielonych
   sprawdzeniach „sedzia” i „recenzja”); gałęzie `zasady/…` czekają na właściciela;
5. zapisuje wynik w katalogu wyników, czytelnym dla sesji AI;
6. przy przekroczeniu limitu prób albo błędzie usługi zakłada zgłoszenie na GitHubie (powiadomienie właściciela).

Tylko biblioteka standardowa; uruchamiana jako `python3 -I kolejka.py` przez systemd.
"""

from __future__ import annotations

import calendar
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

REPO = "EdSkamor/fabruna-studio-NEW"
WLASCICIEL = REPO.split("/")[0]
URL = f"https://github.com/{REPO}.git"
API = "https://api.github.com"

KOLEJKA = Path("/srv/sedzia/kolejka")
WYNIKI = Path("/srv/sedzia/wyniki")
STAN = Path("/srv/sedzia/stan")
VENV = Path("/srv/sedzia/venv")
DOM = Path("/home/sedzia")
TOKEN = DOM / ".config/fabruna/token"
PRACA = DOM / "praca"

LIMITY = {"testy": 3, "kod": 5, "zasady": 5}  # próby na rodzaj i zlecenie; zgodnie z budżetem zleceń
MAX_ROZMIAR = 20 * 1024 * 1024
MAX_COMMITOW = 50
LIMIT_SEDZIEGO_S = 3 * 3600
LIMIT_GIT_S = 600
PROG_PLIKU_PART_S = 600

_OPIS = r"[a-z0-9][a-z0-9-]{0,60}"
WZORZEC_GALEZI = re.compile(rf"(?P<tryb>testy|kod)/(?P<numer>\d{{4}})-{_OPIS}|(?P<zasady>zasady)/{_OPIS}")
SHA = re.compile(r"[0-9a-f]{40}")
TRYBY_AUTOSCALANIA = ("testy", "kod")
BOT = "github-actions[bot]"


# ---------------------------------------------------------------- reguły (czyste funkcje, testowane)

def rozpoznaj(nazwa: str) -> tuple[str, str | None] | None:
    """Tryb i numer zlecenia z nazwy gałęzi albo None, gdy nazwa jest spoza konwencji."""
    dopasowanie = WZORZEC_GALEZI.fullmatch(nazwa)
    if not dopasowanie:
        return None
    if dopasowanie.group("zasady"):
        return "zasady", None
    return dopasowanie.group("tryb"), dopasowanie.group("numer")


def glowy_pakietu(tekst: str) -> list[tuple[str, str]]:
    """Wynik `git bundle list-heads`: lista (sha, pełna nazwa referencji)."""
    wynik = []
    for wiersz in tekst.splitlines():
        if not wiersz.strip():
            continue
        czesci = wiersz.split(" ", 1)
        if len(czesci) != 2 or not SHA.fullmatch(czesci[0]):
            raise ValueError(f"nieczytelny wiersz listy referencji: {wiersz!r}")
        wynik.append((czesci[0], czesci[1]))
    return wynik


def naruszenia(tryb: str, numer: str | None, raw: str) -> list[str]:
    """Niezależna od repozytorium kontrola zmian (`git diff --raw -z --no-renames`).

    Zasady usługi są celowo węższe niż sędziego: usługa nie przepuszcza żadnej zmiany
    `.github/` ani dowiązań symbolicznych i podmodułów, niezależnie od tego, co mówi sędzia z `main`.
    """
    pola = raw.split("\0")
    bledy: list[str] = []
    i = 0
    while i < len(pola) - 1:
        naglowek, sciezka = pola[i], pola[i + 1]
        i += 2
        if not naglowek:
            continue
        czesci = naglowek.lstrip(":").split()
        if len(czesci) < 5:
            bledy.append(f"nieczytelny wpis zmian: {naglowek!r}")
            continue
        tryb_stary, tryb_nowy, status = czesci[0], czesci[1], czesci[4]
        for tryb_pliku in (tryb_stary, tryb_nowy):
            if tryb_pliku in ("120000", "160000"):
                bledy.append(f"{sciezka}: dowiązanie symboliczne albo podmoduł — niedozwolone")
        if sciezka.startswith(".github/") or sciezka == ".github":
            bledy.append(f"{sciezka}: zmiany .github/ wprowadza wyłącznie właściciel")
            continue
        if tryb == "testy":
            if not sciezka.startswith(f"testy/zlecenie_{numer}/"):
                bledy.append(f"{sciezka}: poza testy/zlecenie_{numer}/")
            elif not sciezka.endswith(".py"):
                bledy.append(f"{sciezka}: gałąź testów dodaje tylko pliki .py (dane testowe buduje się w testach)")
            elif status != "A":
                bledy.append(f"{sciezka}: gałąź testów może tylko dodawać pliki (status {status})")
        elif tryb == "kod":
            if not sciezka.startswith("src/"):
                bledy.append(f"{sciezka}: poza src/")
            elif not sciezka.endswith(".py"):
                bledy.append(f"{sciezka}: w src/ dozwolone są tylko pliki .py")
        elif tryb == "zasady":
            if sciezka.startswith("src/") and not sciezka.endswith("/__init__.py"):
                bledy.append(f"{sciezka}: kod wchodzi wyłącznie gałęzią kod/NNNN-opis")
        else:
            bledy.append(f"{sciezka}: nieznany tryb {tryb}")
    return bledy


def nazwa_pliku_wyniku(galaz: str) -> str:
    return galaz.replace("/", "_") + ".txt"


# ---------------------------------------------------------------- narzędzia

def _git(*argumenty: str, katalog: Path | None = None, wejscie: bytes | None = None, srodowisko: dict | None = None) -> str:
    env = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(DOM),
        "LANG": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
    }
    env.update(srodowisko or {})
    polecenie = ["git", "-c", "core.hooksPath=/dev/null"]
    if katalog:
        polecenie += ["-C", str(katalog)]
    proces = subprocess.run(
        polecenie + list(argumenty), input=wejscie, capture_output=True, timeout=LIMIT_GIT_S, env=env, check=False
    )
    if proces.returncode != 0:
        raise RuntimeError(f"git {' '.join(argumenty[:2])}: {proces.stderr.decode(errors='replace').strip()[-500:]}")
    return proces.stdout.decode(errors="replace")


def _token() -> str:
    return TOKEN.read_text("utf-8").strip()


def _api(metoda: str, sciezka: str, dane: dict | None = None, uwierzytelnij: bool = True) -> object:
    zadanie = urllib.request.Request(
        sciezka if sciezka.startswith("https://") else API + sciezka,
        method=metoda,
        data=None if dane is None else json.dumps(dane).encode(),
        headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "fabruna-sedzia"},
    )
    if uwierzytelnij:
        zadanie.add_header("Authorization", f"Bearer {_token()}")
    try:
        with urllib.request.urlopen(zadanie, timeout=60) as odpowiedz:
            tresc = odpowiedz.read()
    except urllib.error.HTTPError as blad:
        raise RuntimeError(f"GitHub {metoda} {sciezka}: {blad.code} {blad.read()[:300].decode(errors='replace')}") from None
    return json.loads(tresc) if tresc else None


def _zglos_problem(tytul: str, tresc: str) -> None:
    """Zgłoszenie zakłada przepływ `zgloszenia.yml` jako github-actions, więc właściciel dostaje powiadomienie."""
    try:
        _api("POST", f"/repos/{REPO}/dispatches", {"event_type": "problem", "client_payload": {"tytul": tytul[:200], "tresc": tresc[:6000]}})
    except Exception as blad:  # noqa: BLE001 — brak powiadomienia nie może przerwać usługi
        _dziennik(f"nie udało się założyć zgłoszenia „{tytul}”: {blad}")


def _otwarte_zgloszenie(tytul: str) -> bool:
    try:
        return any(z.get("title") == tytul and (z.get("user") or {}).get("login") == BOT
                   for z in _api("GET", f"/repos/{REPO}/issues?state=open&per_page=100") or [])
    except Exception:  # noqa: BLE001
        return False


def _dziennik(wiersz: str) -> None:
    with open(WYNIKI / "dziennik.log", "a", encoding="utf-8") as plik:
        plik.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {wiersz}\n")


def _zapisz_wynik(galaz: str, tekst: str) -> None:
    cel = WYNIKI / nazwa_pliku_wyniku(galaz)
    tymczasowy = cel.with_suffix(".tmp")
    tymczasowy.write_text(tekst, "utf-8")
    tymczasowy.chmod(0o644)
    tymczasowy.replace(cel)


# ---------------------------------------------------------------- limit prób

def _klucz(tryb: str, numer: str | None, galaz: str) -> str:
    return f"{tryb}-{numer}" if numer else f"zasady-{time.strftime('%Y%m%d')}"  # zasady: wspólny limit dzienny


def _tytul_limitu(klucz: str) -> str:
    return f"[sędzia] Limit prób: {klucz}"


def _sprawdz_limit(tryb: str, klucz: str) -> str | None:
    """None — można oceniać; tekst — powód odmowy. Zamknięcie zgłoszenia przez właściciela zeruje licznik."""
    plik = STAN / f"{klucz}.json"
    stan = json.loads(plik.read_text("utf-8")) if plik.exists() else {"proby": 0, "od": 0}
    if stan["proby"] < LIMITY[tryb]:
        return None
    try:
        zgloszenia = _api("GET", f"/repos/{REPO}/issues?state=closed&per_page=100&sort=updated", uwierzytelnij=True)
        for z in zgloszenia or []:
            if z.get("title") == _tytul_limitu(klucz) and z.get("closed_at") and (z.get("user") or {}).get("login") == BOT:
                szczegoly = _api("GET", f"/repos/{REPO}/issues/{int(z['number'])}")
                if ((szczegoly or {}).get("closed_by") or {}).get("login") != WLASCICIEL:
                    continue  # licznik zeruje wyłącznie właściciel
                zamkniete = calendar.timegm(time.strptime(z["closed_at"], "%Y-%m-%dT%H:%M:%SZ"))
                if zamkniete > stan.get("ostatnia", 0):
                    plik.write_text(json.dumps({"proby": 0, "od": time.time()}), "utf-8")
                    return None
    except Exception as blad:  # noqa: BLE001
        _dziennik(f"sprawdzenie zgłoszeń limitu nie powiodło się: {blad}")
    return f"wyczerpany limit {LIMITY[tryb]} prób dla {klucz}; odblokowanie: właściciel zamyka zgłoszenie „{_tytul_limitu(klucz)}”"


def _policz_probe(tryb: str, klucz: str) -> int:
    plik = STAN / f"{klucz}.json"
    stan = json.loads(plik.read_text("utf-8")) if plik.exists() else {"proby": 0, "od": 0}
    stan["proby"] += 1
    stan["ostatnia"] = time.time()
    plik.write_text(json.dumps(stan), "utf-8")
    return stan["proby"]


# ---------------------------------------------------------------- środowisko sędziego

def _zaleznosci(czysty: Path, katalog: Path) -> None:
    """Instaluje przypięte zależności z `pyproject.toml` z `main`, gdy plik się zmienił (poza piaskownicą, z siecią)."""
    pyproject = _git("show", "main:pyproject.toml", katalog=czysty)
    skrot = hashlib.sha256(pyproject.encode()).hexdigest()
    znacznik = STAN / "pyproject.sha256"
    if znacznik.exists() and znacznik.read_text().strip() == skrot:
        return
    katalog.mkdir(parents=True, exist_ok=True)
    (katalog / "pyproject.toml").write_text(pyproject, "utf-8")
    # pip pobiera i buduje pakiety, więc działa w piaskownicy: z siecią, ale bez /home (token) i bez reszty /srv.
    proces = subprocess.run(
        ["bwrap", "--unshare-all", "--share-net", "--die-with-parent", "--new-session",
         "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--tmpfs", "/run",
         "--tmpfs", "/home", "--tmpfs", "/srv", "--tmpfs", "/root", "--ro-bind", "/run/systemd/resolve", "/run/systemd/resolve",
         "--bind", str(VENV), str(VENV), "--ro-bind", str(katalog), str(katalog), "--chdir", str(katalog),
         "--clearenv", "--setenv", "PATH", "/usr/bin:/bin", "--setenv", "HOME", "/tmp", "--setenv", "LANG", "C.UTF-8",
         str(VENV / "bin/python"), "-I", "-m", "pip", "install", "-q", "--disable-pip-version-check", "--no-cache-dir", "--group", "dev"],
        capture_output=True, text=True, timeout=1800, check=False,
    )
    if proces.returncode != 0:
        raise RuntimeError(f"instalacja zależności z main:pyproject.toml nie powiodła się: {proces.stderr[-800:]}")
    znacznik.write_text(skrot)


def _piaskownica(repo: Path, sedzia: Path, galaz: str) -> subprocess.CompletedProcess[str]:
    """Sędzia z `main` na kopii gałęzi: bez sieci, bez /home, /run i /srv (poza venv), bez tokenu."""
    polecenie = [
        "bwrap", "--unshare-all", "--die-with-parent", "--new-session",
        "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc",
        "--tmpfs", "/tmp", "--tmpfs", "/run", "--tmpfs", "/home", "--tmpfs", "/srv", "--tmpfs", "/root",
        "--ro-bind", str(VENV), str(VENV),
        "--ro-bind", str(sedzia), str(sedzia),
        "--bind", str(repo), str(repo),
        "--chdir", str(repo),
        "--clearenv",
        "--setenv", "PATH", f"{VENV}/bin:/usr/bin:/bin",
        "--setenv", "HOME", "/tmp",
        "--setenv", "LANG", "C.UTF-8",
        "--setenv", "PYTHONPATH", str(sedzia),
        "--setenv", "GIT_CONFIG_NOSYSTEM", "1",
        str(VENV / "bin/python"), "-P", "-m", "sedzia", "galaz", galaz, "--baza", "main",
    ]
    try:
        return subprocess.run(polecenie, capture_output=True, text=True, errors="replace", timeout=LIMIT_SEDZIEGO_S, check=False)
    except subprocess.TimeoutExpired as blad:
        wyjscie = blad.stdout.decode(errors="replace") if isinstance(blad.stdout, bytes) else (blad.stdout or "")
        return subprocess.CompletedProcess(polecenie, 124, wyjscie, f"przekroczony limit czasu sędziego ({LIMIT_SEDZIEGO_S} s)")


def _usun(sciezka: Path) -> None:
    def napraw(funkcja, cel, _blad):
        try:
            for sciezka in (os.path.dirname(cel), cel):
                if not os.path.islink(sciezka) and os.path.isdir(sciezka):
                    os.chmod(sciezka, 0o700)  # tylko katalogi i nigdy cel dowiązania
            funkcja(cel)
        except OSError:
            pass
    shutil.rmtree(sciezka, onexc=napraw)


# ---------------------------------------------------------------- GitHub

def _wypchnij(czysty: Path, sha: str, galaz: str) -> None:
    pomocnik = "!f() { test \"$1\" = get && echo username=x-access-token && printf 'password=%s\\n' \"$(cat " + str(TOKEN) + ")\"; }; f"
    _git("-c", "credential.helper=", "-c", f"credential.helper={pomocnik}", "push", "-q", URL, f"+{sha}:refs/heads/{galaz}", katalog=czysty)


def _pull_request(galaz: str, tryb: str, numer: str | None, wyjscie: str) -> str:
    otwarte = _api("GET", f"/repos/{REPO}/pulls?state=open&head={WLASCICIEL}:{galaz}")
    if otwarte:
        pr = otwarte[0]
    else:
        opis = (
            f"Zgłoszone przez usługę sędziego na PC (konto `sedzia`).\n\n"
            f"Wyrok sędziego z `main` w piaskownicy: **POZYTYWNY**.\n\n```\n{wyjscie[-3000:]}\n```\n\n"
            + ("Automatyczne scalenie po zielonych sprawdzeniach „sedzia” i „recenzja”.\n" if tryb in TRYBY_AUTOSCALANIA
               else "Gałąź zasad: scala wyłącznie właściciel.\n")
            + "\nSZKIC AI — do pracy autora.\n"
        )
        tytul = f"{'Testy' if tryb == 'testy' else 'Kod' if tryb == 'kod' else 'Zasady'}: {galaz}"
        pr = _api("POST", f"/repos/{REPO}/pulls", {"title": tytul, "head": galaz, "base": "main", "body": opis})
    if tryb in TRYBY_AUTOSCALANIA:
        zapytanie = "mutation($id: ID!) { enablePullRequestAutoMerge(input: {pullRequestId: $id, mergeMethod: MERGE}) { clientMutationId } }"
        wynik = _api("POST", "/graphql", {"query": zapytanie, "variables": {"id": pr["node_id"]}})
        if isinstance(wynik, dict) and wynik.get("errors"):
            raise RuntimeError(f"nie udało się włączyć automatycznego scalenia: {wynik['errors']}")
    return pr["html_url"]


# ---------------------------------------------------------------- jedno zgłoszenie

def _skopiuj_zgloszenie(plik: Path, cel: Path) -> None:
    """Kopia bez podążania za dowiązaniem, tylko zwykły plik, z limitem rozmiaru."""
    try:
        zrodlo = os.open(plik, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as blad:
        raise ValueError(f"nie da się otworzyć zgłoszenia: {blad}") from None
    try:
        if not stat.S_ISREG(os.fstat(zrodlo).st_mode):
            raise ValueError("zgłoszenie nie jest zwykłym plikiem")
        with open(cel, "wb") as wyjscie:
            razem = 0
            while blok := os.read(zrodlo, 1 << 20):
                razem += len(blok)
                if razem > MAX_ROZMIAR:
                    raise ValueError("plik zgłoszenia jest za duży")
                wyjscie.write(blok)
    finally:
        os.close(zrodlo)


def obsluz(plik: Path) -> None:
    identyfikator = plik.stem
    praca = PRACA / identyfikator
    galaz = "?"
    if praca.exists():
        _usun(praca)
    praca.mkdir(parents=True)
    try:
        pakiet = praca / "zgloszenie.bundle"
        _skopiuj_zgloszenie(plik, pakiet)

        czysty = praca / "czysty.git"
        _git("init", "-q", "--bare", "-b", "main", str(czysty))
        _git("fetch", "-q", "--no-tags", URL, "+refs/heads/main:refs/heads/main", katalog=czysty)
        try:
            glowy = glowy_pakietu(_git("bundle", "list-heads", str(pakiet), katalog=czysty))
        except RuntimeError as blad:
            raise ValueError(f"nieczytelny plik git bundle: {blad}") from None
        if len(glowy) != 1 or not glowy[0][1].startswith("refs/heads/"):
            raise ValueError("zgłoszenie musi zawierać dokładnie jedną gałąź (refs/heads/…)")
        sha, ref = glowy[0]
        galaz = ref.removeprefix("refs/heads/")
        rozpoznana = rozpoznaj(galaz)
        if rozpoznana is None:
            raise ValueError(f"nazwa gałęzi „{galaz}” spoza konwencji testy/NNNN-opis, kod/NNNN-opis, zasady/opis")
        tryb, numer = rozpoznana
        klucz = _klucz(tryb, numer, galaz)

        odmowa = _sprawdz_limit(tryb, klucz)
        if odmowa:
            _zapisz_wynik(galaz, f"zgłoszenie: {identyfikator}\nWYNIK: ODRZUCONE BEZ OCENY\n{odmowa}\n")
            _dziennik(f"{identyfikator} {galaz}: odmowa — limit")
            if not _otwarte_zgloszenie(_tytul_limitu(klucz)):
                _zglos_problem(_tytul_limitu(klucz), f"Gałąź `{galaz}` wyczerpała limit {LIMITY[tryb]} prób.\n\n"
                               "Zamknij to zgłoszenie, aby pozwolić na kolejne próby (licznik się wyzeruje), "
                               "albo zmień zlecenie.\n\nWynik ostatniej oceny: `/srv/sedzia/wyniki/" + nazwa_pliku_wyniku(galaz) + "` na PC.")
            return
        proba = _policz_probe(tryb, klucz)

        try:
            _git("fetch", "-q", str(pakiet), f"+{ref}:{ref}", katalog=czysty)
        except RuntimeError as blad:
            raise ValueError(f"nie da się pobrać gałęzi z pakietu (czy odchodzi od aktualnego main?): {blad}") from None
        if _git("rev-parse", f"{ref}^{{commit}}", katalog=czysty).strip() != sha:
            raise ValueError("commit w pakiecie nie zgadza się z listą referencji")
        ile = int(_git("rev-list", "--count", f"main..{sha}", katalog=czysty).strip())
        if not 1 <= ile <= MAX_COMMITOW:
            raise ValueError(f"gałąź ma {ile} commitów względem main (dozwolone 1–{MAX_COMMITOW})")
        raw = _git("diff", "--raw", "-z", "--no-renames", "--no-abbrev", f"main...{sha}", katalog=czysty)
        bledy = naruszenia(tryb, numer, raw)
        if bledy:
            tekst = "\n".join(f"  - {b}" for b in bledy)
            _zapisz_wynik(galaz, f"zgłoszenie: {identyfikator}\ncommit: {sha}\npróba: {proba}/{LIMITY[tryb]}\n"
                          f"WYNIK: NEGATYWNY (kontrola ścieżek usługi)\n{tekst}\n")
            _dziennik(f"{identyfikator} {galaz} {sha[:10]}: negatywny — ścieżki")
            return

        # Kopia do oceny: od tej chwili jej .git jest niezaufany i usługa nie uruchamia w nim gita.
        repo = praca / "repo"
        _git("clone", "-q", "--no-hardlinks", "--no-checkout", str(czysty), str(repo))
        _git("checkout", "-q", "-b", galaz, sha, katalog=repo)
        sedzia = praca / "sedzia-main"
        sedzia.mkdir()
        archiwum = subprocess.run(
            ["git", "-C", str(czysty), "archive", "--format=tar", "main", "sedzia"], capture_output=True, timeout=LIMIT_GIT_S, check=True
        ).stdout
        subprocess.run(["tar", "-x", "--no-same-owner", "-C", str(sedzia)], input=archiwum, check=True, timeout=LIMIT_GIT_S)
        _zaleznosci(czysty, praca / "zaleznosci")

        przebieg = _piaskownica(repo, sedzia, galaz)
        wyjscie = (przebieg.stdout or "")[-20000:]
        bledy_wyjscia = (przebieg.stderr or "")[-5000:]
        naglowek = f"zgłoszenie: {identyfikator}\ncommit: {sha}\npróba: {proba}/{LIMITY[tryb]}\n"
        if przebieg.returncode != 0:
            werdykt = "NEGATYWNY" if przebieg.returncode == 1 else f"BŁĄD SĘDZIEGO (kod {przebieg.returncode})"
            _zapisz_wynik(galaz, f"{naglowek}WYNIK: {werdykt}\n\n{wyjscie}\n{bledy_wyjscia}\n")
            _dziennik(f"{identyfikator} {galaz} {sha[:10]}: {werdykt}")
            return

        _wypchnij(czysty, sha, galaz)
        adres = _pull_request(galaz, tryb, numer, wyjscie)
        dalej = ("GitHub scali sam po zielonych sprawdzeniach „sedzia” i „recenzja”; uwagi recenzji pojawią się w komentarzu PR."
                 if tryb in TRYBY_AUTOSCALANIA else "Gałąź zasad czeka na właściciela.")
        _zapisz_wynik(galaz, f"{naglowek}WYNIK: POZYTYWNY — wypchnięte\npull request: {adres}\n{dalej}\n\n{wyjscie}\n")
        _dziennik(f"{identyfikator} {galaz} {sha[:10]}: pozytywny, {adres}")
    except Exception as blad:  # noqa: BLE001
        opis = f"{type(blad).__name__}: {blad}"
        _zapisz_wynik(galaz if galaz != "?" else f"nieznana_{identyfikator}",
                      f"zgłoszenie: {identyfikator}\nWYNIK: BŁĄD ZGŁOSZENIA\n{opis}\n")
        _dziennik(f"{identyfikator} {galaz}: błąd — {opis}")
        if not isinstance(blad, ValueError):
            _zglos_problem(f"[sędzia] Błąd usługi przy {galaz}", f"```\n{traceback.format_exc()[-4000:]}\n```")
    finally:
        try:
            plik.unlink(missing_ok=True)
        except OSError:
            pass
        _usun(praca)


def main() -> int:
    for katalog in (STAN, PRACA):
        katalog.mkdir(parents=True, exist_ok=True)
    with open(STAN / "blokada", "w") as blokada:
        fcntl.flock(blokada, fcntl.LOCK_EX)
        while True:
            teraz = time.time()
            wpisy = []
            for p in KOLEJKA.iterdir():
                try:
                    st = p.lstat()
                except OSError:
                    continue  # znikł w międzyczasie
                if stat.S_ISDIR(st.st_mode):
                    continue  # katalogi pomijamy (nie da się ich bezpiecznie usunąć)
                wiek = teraz - st.st_mtime
                if wiek > PROG_PLIKU_PART_S or wiek < -60:  # porzucony albo z datą z przyszłości
                    if not p.name.endswith(".bundle") or wiek < -60:
                        try:
                            p.unlink()
                        except OSError:
                            pass
                        continue
                wpisy.append((st.st_mtime, p))
            wpisy.sort()
            gotowe = [p for _, p in wpisy if p.name.endswith(".bundle") and not p.name.startswith(".")]
            if gotowe:
                try:
                    obsluz(gotowe[0])
                except Exception as blad:  # noqa: BLE001 — jedno zgłoszenie nie zatrzymuje kolejki
                    _dziennik(f"{gotowe[0].name}: nieobsłużony błąd {blad}")
                    try:
                        gotowe[0].unlink()
                    except OSError:
                        return 1
                continue
            if wpisy:
                time.sleep(5)  # trwa zapis zgłoszenia (.part)
                continue
            return 0


if __name__ == "__main__":
    sys.exit(main())
