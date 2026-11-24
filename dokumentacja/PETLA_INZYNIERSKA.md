# Pętla inżynierska — opis mechanizmu

SZKIC AI — do pracy autora.

## 1. Zasada

Program nie sprawdza sam siebie. O tym, czy praca jest zrobiona, rozstrzyga sędzia-skrypt na podstawie mierzalnych bramek. Najważniejsze są dwie rzeczy: wysokiej jakości testy oraz pewność, że nowa zmiana nie psuje tego, co już jest.

## 2. Role

| Rola | Zadanie | Ograniczenie |
|---|---|---|
| Zlecający | pisze zlecenie z kryteriami odbioru | nie pisze testów ani kodu tego zlecenia |
| Autor testów | zamienia kryteria na testy | nie pisze kodu; tylko nowe pliki w `testy/zlecenie_NNNN/` |
| Wykonawca | pisze kod do zielonego wyroku | nie zmienia testów, sędziego ani konfiguracji; tylko `src/` |
| Sędzia-skrypt | wydaje wyrok (`wyrok.json`) | nie jest sesją AI; używa tylko biblioteki standardowej i narzędzi przez podproces |
| Recenzent | czyta zmianę i wyrok z niezależnej sesji | nie jest autorem testów ani wykonawcą |
| Właściciel | zatwierdza scalenie | jedyny, kto zmienia zasady (gałąź `zasady/…`) |

## 3. Przebieg zlecenia

1. Zlecenie `zlecenia/NNNN-opis.md` według `zlecenia/WZOR.md`; kryteria w wierszach `- **K01 — nazwa.** treść`.
2. Gałąź `testy/NNNN-opis`: autor testów oddaje testy. Sędzia w trybie „testy” sprawdza, że są czerwone, stabilne i pokrywają każde kryterium. Scalenie.
3. Gałąź `kod/NNNN-opis` (od gałęzi z testami): wykonawca oddaje kod. Sędzia w trybie „kod” sprawdza testy zlecenia, cały zestaw, sekrety i wynik mutacyjny. Limit podejść jest w zleceniu; po jego wyczerpaniu sesja oddaje raport z diagnozą.
4. Recenzja z niezależnej sesji, potem scalenie przez właściciela.

Bazą (`--baza`) jest zawsze stan, od którego gałąź odchodzi: `main` po scaleniu poprzedniego etapu albo — przy pracy lokalnej przed scaleniem — gałąź poprzedniego etapu (zasady → testy → kod).

## 4. Rodzaje gałęzi i dozwolone ścieżki

| Gałąź | Wolno zmienić | Tryb sędziego |
|---|---|---|
| `testy/NNNN-opis` | wyłącznie nowe pliki w `testy/zlecenie_NNNN/` | `testy` |
| `kod/NNNN-opis` | wyłącznie `src/` | `kod` |
| `zasady/opis` | `sedzia/`, `testy/`, `.github/`, `dokumentacja/`, `zlecenia/`, `AGENTS.md`, `pyproject.toml`, `README.md`, `.gitignore`, `.secrets.baseline` oraz puste `src/**/__init__.py` | `zasady` |
| `main` | — (stan po scaleniu) | `calosc` |

Nazwa: małe litery, cyfry i łączniki; numer zlecenia to cztery cyfry. Inna nazwa gałęzi w pull requeście to wyrok negatywny.

Zmiana poza dozwolonym zakresem to wyrok negatywny. Sędzia liczy trzy źródła zmian: commity względem bazy (`git diff --name-only --no-renames BAZA...HEAD`; przeniesienie pliku to usunięcie i dodanie), zmiany niezatwierdzone (`git diff HEAD`) oraz pliki nieśledzone (`git ls-files --others --exclude-standard`). Lokalnie sprawdza też, czy nazwa gałęzi pasuje do trybu i numeru zlecenia.

Dwa doprecyzowania względem pierwotnej listy ścieżek:

- Gałąź `testy/…` może tylko dodawać pliki. Zmiana albo usunięcie istniejącego pliku testów wymaga gałęzi `zasady/…` — dlatego zasady obejmują całe `testy/`, nie tylko `testy/sedzia/`.
- Gałąź `zasady/…` nie wnosi kodu do `src/`. Wyjątek: pusty plik `__init__.py` (znacznik pakietu).

## 5. Sędzia

    python -m sedzia testy  --zlecenie NNNN --baza REF
    python -m sedzia kod    --zlecenie NNNN --baza REF [--prog-mutacji 70]
    python -m sedzia zasady --baza REF
    python -m sedzia calosc [--mutacje] [--prog-mutacji 70]
    python -m sedzia galaz NAZWA [--baza REF] [--prog-mutacji 70]

Tryb `galaz` wyznacza tryb i numer zlecenia z nazwy gałęzi (używa go CI); `main` daje tryb `calosc`. Każdy tryb przyjmuje `--wyrok PLIK` (domyślnie `wyrok.json` w katalogu repozytorium).

Kody wyjścia: `0` — wyrok pozytywny; `1` — negatywny; `2` — błąd użycia albo wewnętrzny (wtedy wyrok nie powstaje).

`wyrok.json` zawiera: `wyrok`, `tryb`, `zlecenie`, `baza`, `baza_commit`, `head`, `drzewo_czyste`, `galaz`, `narzedzia` (wersje), `czas_s` oraz listę `kroki`. Na początku przebiegu sędzia usuwa stary plik wyroku. `drzewo_czyste: false` oznacza, że oceniane były także zmiany niezatwierdzone, więc wyrok nie opisuje samego commita `head`. Każdy krok ma `nazwa`, `wynik` (`pozytywny`, `negatywny`, `pominiety`), `opis`, `liczby` i `szczegoly` (w pliku pełne; na ekranie pierwsze 12 pozycji). Wyrok jest pozytywny tylko wtedy, gdy wszystkie kroki są pozytywne.

Reguły ogólne:

- Brak wymaganego narzędzia (git, pytest, mutmut, detect-secrets) to wynik negatywny kroku z nazwą narzędzia, nigdy ciche pominięcie.
- Po pierwszym negatywnym kroku sędzia wykonuje pozostałe tanie kroki. Krok kosztowny (mutacje) dostaje wtedy wynik `pominiety`, a wyrok jest negatywny.
- Każdy przebieg pytest jest rozliczany z raportu JUnit, test po teście. Kod wyjścia 0 bez raportu wyników nie jest zielony.

## 6. Bramki

### Tryb „testy” (autor testów oddał testy, kodu jeszcze nie ma)

| Krok | Wynik pozytywny, gdy |
|---|---|
| `ochrona_sciezek` | wszystkie zmiany to nowe pliki w `testy/zlecenie_NNNN/` |
| `zbieranie_testow` | każdy plik `.py` w katalogu testów zlecenia się kompiluje, a `pytest --collect-only` kończy się kodem 0 i zbiera co najmniej jeden test |
| `pokrycie_kryteriow` | każdy identyfikator `Knn` ze zlecenia ma co najmniej jeden zebrany test o nazwie zaczynającej się od `test_knn_` (bez rozróżniania wielkości liter) |
| `czerwone_na_bazie` | w każdym z trzech przebiegów pytest kończy się kodem 1 albo 2; kod 0 oznacza „testy niczego nie sprawdzają” |
| `stabilnosc` | trzy przebiegi dają identyczny wynik każdego testu |
| `sekrety` | skan zmienionych plików nie daje nowego znaleziska |

Krok `czerwone_na_bazie` wypisuje też ostrzeżenia, które nie zmieniają wyroku: testy zielone już na bazie oraz kryteria bez żadnego czerwonego testu. To materiał dla recenzenta.

### Tryb „kod” (wykonawca oddał kod)

| Krok | Wynik pozytywny, gdy |
|---|---|
| `ochrona_sciezek` | wszystkie zmiany są w `src/` |
| `testy_zlecenia` | w trzech przebiegach pytest kończy się kodem 0 i każdy test zlecenia ma wynik „passed” (test pominięty nie jest zielony) |
| `stabilnosc` | trzy przebiegi dają identyczny wynik każdego testu |
| `caly_zestaw` | `pytest testy/` kończy się kodem 0 i zostawia raport wyników |
| `sekrety` | skan zmienionych plików nie daje nowego znaleziska |
| `mutacje` | wynik mutacyjny plików `.py` z `src/` zmienionych względem bazy, liczony testami zlecenia, jest nie niższy niż próg (domyślnie 70%) |

Krok `mutacje` jest negatywny także wtedy, gdy: wśród zmian w `src/` nie ma pliku `.py`; nie powstał żaden mutant; mutmut przerwał pracę (na przykład żaden test nie wykonuje zmutowanej funkcji); mutowany kod zawiera `pragma: no mutate` albo odwołanie do pytest lub mutmut.

### Tryb „zasady”

`ochrona_sciezek`, `testy_sedziego` (każdy test z `testy/sedzia` ma wynik „passed” i jest ich co najmniej jeden), `caly_zestaw`, `sekrety`. Testy sędziego i cały zestaw to jeden przebieg `pytest testy/`, rozliczony dwa razy.

### Tryb „calosc” (main po scaleniu, przebieg nocny)

`caly_zestaw`, `sekrety` (wszystkie śledzone pliki), a z opcją `--mutacje` także `mutacje` całego `src/` wszystkimi testami poza `testy/sedzia`. Gdy w `src/` nie ma żadnej funkcji, krok `mutacje` jest pozytywny z liczbą mutantów 0.

## 7. Wynik mutacyjny

    wynik = (zabite + przekroczony czas) / (wszystkie − pominięte) · 100%

- Przekroczenie czasu liczy się jako zabicie mutanta.
- Mutant bez testu, ocalały i podejrzany zostają w mianowniku, więc obniżają wynik.
- Przykład: 11 mutantów, 1 pominięty, 6 zabitych, 1 z przekroczonym czasem → (6 + 1) / (11 − 1) = 70%.

Sędzia uruchamia mutmut w piaskownicy: do katalogu tymczasowego kopiuje `src/` i `testy/` (bez `testy/sedzia`) oraz zapisuje tam własny `pyproject.toml`. Bierze do niego tabelę `[tool.pytest.ini_options]` i `[tool.mutmut]` z repozytorium, po czym sam ustawia `source_paths = ["src"]`, `also_copy = ["testy"]`, `only_mutate` (lista zmienionych plików) i `pytest_add_cli_args_test_selection` (katalog testów zlecenia). Liczby czyta z `mutants/mutmut-cicd-stats.json` (polecenie `mutmut export-cicd-stats`), a nazwy niezabitych mutantów z `mutmut results`. Piaskownica znika po przebiegu, dlatego `wyrok.json` w szczegółach kroku `mutacje` niesie każdego niezabitego mutanta razem z różnicą względem oryginału (`mutmut show`, pierwszych 40) — to materiał dla autora testów i recenzenta.

## 8. Co z tego wynika dla autora testów

- Importy testowanego kodu wewnątrz testów albo fixture; plik z importem na górze nie da się zebrać bez kodu.
- Mutmut wiąże test z funkcją tylko wtedy, gdy test woła ją w tym samym procesie. Kod sprawdzany wyłącznie przez podproces zostaje „bez testu” i obniża wynik. Zlecenie powinno więc dawać funkcję wejściową, którą test wywoła bezpośrednio.
- `testy/conftest.py` daje dwa fixture: `srodowisko_podprocesu` (środowisko z `PYTHONPATH` wskazującym `src/`) i `katalog_src` (dla testów czytających pliki źródłowe; w piaskownicy mutacji taki test jest pomijany, bo mutmut przepisuje pliki).
- Testy widzą w piaskownicy tylko `src/` i `testy/`.
- Fałszywy alarm skanu sekretów zatwierdza się wyłącznie w `.secrets.baseline` (zmiana typu „zasady”); dyrektywa w kodzie nie działa.

## 9. CI i właściciele ścieżek

`.github/workflows/sedzia.yml`: zadanie `sedzia` dla pull requestów do `main` i wypchnięć na `main` (pełna historia, Python 3.13, `pip install --group dev`, `python -P -m sedzia galaz …`, `wyrok.json` jako artefakt); zadanie `noc` według harmonogramu (`python -m sedzia calosc --mutacje`).

W pull requeście sędzia pochodzi z gałęzi bazowej (`git archive origin/main sedzia`), nie z ocenianej gałęzi; wyjątkiem jest pierwsze wdrożenie, gdy baza nie ma jeszcze sędziego. `.github/CODEOWNERS` kieruje do właściciela zmiany w `testy/`, `sedzia/`, `.github/`, `zlecenia/`, `dokumentacja/`, `AGENTS.md`, `pyproject.toml`, `.gitignore` i `.secrets.baseline`.

## 10. Testy sędziego

`testy/sedzia/`: każdy test buduje tymczasowe repozytorium git z kopią sędziego i minimalnym projektem, tworzy gałęzie i uruchamia sędziego podprocesem. Litery w nazwach testów: (a) ścieżka szczęśliwa „testy”; (b) gałąź testów zmienia `src/`; (c) kryterium bez testu; (d) testy zielone na bazie; (e) test niestabilny; (f) ścieżka szczęśliwa „kod”; (g) gałąź kodu zmienia testy; (h) gałąź kodu zmienia sędziego, konfigurację albo zlecenie; (i) czerwony test zlecenia; (j) regresja poza zleceniem; (k) słabe testy poniżej progu; (l) fałszywy sekret; (m) zmiana niezatwierdzona, plik nieśledzony, przeniesienie pliku. Dalsze litery: sędzia z bazy wobec podmienionego sędziego, brak narzędzi, nazwa gałęzi, tryby „zasady” i „calosc”, błędy użycia, próby obejścia mutacji, fixture.

Testy uruchamiające mutmut mają znacznik `wolny`. Wszystkie muszą przechodzić.

## 11. Niesprawdzone i znane ograniczenia

- [niesprawdzone: przypiąć pełnym skrótem przy pierwszym wypchnięciu] wersje akcji w `sedzia.yml` (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`).
- [niesprawdzone] działanie przepływu na GitHubie, w tym dostępność `origin/main` po pobraniu pełnej historii. Lokalnie wykonano tylko skrypty kroków na klonie.
- [niesprawdzone] ochrona gałęzi `main` (wymagane sprawdzenie „sedzia”, wymagana zgoda właściciela ścieżek) — ustawia się ją w GitHubie, nie w repozytorium.
- Pull request może zmienić sam plik przepływu; chroni przed tym tylko przegląd właściciela ścieżki `.github/`.
- Sędzia nie jest piaskownicą: kod wykonawcy działa w procesie pytest. Celową manipulację wykrywa recenzja zmiany; sędzia ma jedynie proste bezpieczniki (raport JUnit, zakazane odwołania).
- Wyrok lokalny zależy od lokalnego środowiska (na przykład `.venv`, `.git/info/exclude`). Wiążący jest wyrok z CI, a dopóki CI nie działa — wyrok uruchomiony ponownie przez sesję prowadzącą na czystym klonie (`drzewo_czyste: true`). Wyrok ogłoszony przez samego wykonawcę nie wystarcza.
- Sędzia pilnuje całego `src/`; węższy zakres plików ze zlecenia sprawdza recenzent.
- Między scaleniem testów zlecenia a scaleniem jego kodu `main` jest czerwony: tryb „calosc” daje wtedy wyrok negatywny, zgodnie z prawdą. Tryb „kod” wymaga zielonego całego zestawu, więc zlecenia idą pojedynczo — testy następnego zlecenia scala się po kodzie poprzedniego. [propozycja] Bramka „żaden test zielony na bazie nie jest czerwony na gałęzi” (drugi przebieg zestawu na bazie) pozwoliłaby prowadzić zlecenia równolegle.
- Stabilność to trzy kolejne przebiegi w tej samej kolejności; nie wykrywa zależności od kolejności testów.
- Przypięte są tylko trzy narzędzia; ich zależności pośrednie nie.
