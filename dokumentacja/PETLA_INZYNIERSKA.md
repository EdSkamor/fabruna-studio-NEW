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
4. Recenzja automatyczna w CI i scalenie automatyczne (rozdział 12); gałęzie zasad scala właściciel.

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

W trybach „testy” i „kod” dochodzą dwa kroki: „zakazy” (statyczny zakaz konstrukcji, którymi kod pod testem mógłby podrobić wyrok — lista w `sedzia/zakazy.py` i w rozdziale 12) przed uruchomieniem czegokolwiek oraz „nienaruszalnosc” na końcu (stan repozytorium po przebiegach taki sam jak na starcie).

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
- Pull request może zmienić sam plik przepływu. Sesje AI nie mogą jednak wypchnąć żadnej gałęzi: robi to wyłącznie usługa sędziego, która odrzuca każdą zmianę `.github/`, a jej token nie ma uprawnienia „Workflows” (rozdział 12).
- Sędzia sam nie jest piaskownicą: kod wykonawcy działa w procesie pytest. Na PC usługa uruchamia sędziego w piaskownicy bwrap (rozdział 12), w CI — na jednorazowej maszynie bez sekretów. Celową manipulację wykrywa recenzja zmiany; sędzia ma jedynie proste bezpieczniki (raport JUnit, zakazane odwołania).
- Wyrok lokalny zależy od lokalnego środowiska (na przykład `.venv`, `.git/info/exclude`). Wiążący jest wyrok z CI, a dopóki CI nie działa — wyrok uruchomiony ponownie przez sesję prowadzącą na czystym klonie (`drzewo_czyste: true`). Wyrok ogłoszony przez samego wykonawcę nie wystarcza.
- Sędzia pilnuje całego `src/`; węższy zakres plików ze zlecenia sprawdza recenzent.
- Między scaleniem testów zlecenia a scaleniem jego kodu `main` jest czerwony: tryb „calosc” daje wtedy wyrok negatywny, zgodnie z prawdą. Tryb „kod” wymaga zielonego całego zestawu, więc zlecenia idą pojedynczo — testy następnego zlecenia scala się po kodzie poprzedniego. [propozycja] Bramka „żaden test zielony na bazie nie jest czerwony na gałęzi” (drugi przebieg zestawu na bazie) pozwoliłaby prowadzić zlecenia równolegle.
- Stabilność to trzy kolejne przebiegi w tej samej kolejności; nie wykrywa zależności od kolejności testów.
- Przypięte są tylko trzy narzędzia; ich zależności pośrednie nie.

## 12. Automatyczne scalanie i usługa sędziego

Cel: właściciel nie zatwierdza każdego kroku, a żadna sesja AI nie może obejść sędziego ani recenzji.

**Granica zaufania.** Prawo zapisu w repozytorium ma tylko token (fine-grained, jedno repozytorium; uprawnienia: Contents, Pull requests, Issues — zapis; bez Workflows i Administration) zapisany na osobnym koncie systemowym `sedzia` (`/home/sedzia`, tryb 700). Sesje AI działają na koncie właściciela i nie mają ani tego tokenu, ani klucza wdrożeniowego, ani `sudo`.

**Droga gałęzi.** Sesja: `sh sedzia/pc/zglos.sh GAŁĄŹ --czekaj` — plik `git bundle` trafia do `/srv/sedzia/kolejka` (zapis dla właściciela, odczyt cudzych zgłoszeń niemożliwy). Usługa `fabruna-sedzia` (`sedzia/pc/kolejka.py`, instalowana przez właściciela z commitu `main` skryptem `sedzia/pc/instalacja.sh`):

1. pobiera `main` z GitHuba i gałąź z pliku do czystego repozytorium, którego nie widzi żaden kod gałęzi;
2. sprawdza nazwę gałęzi, liczbę commitów i zmienione ścieżki własnymi regułami — węższymi niż sędziego: nigdy `.github/`, dowiązań ani podmodułów;
3. liczy próby (testy 3, kod 5, zasady 5 na klucz); po limicie odmawia i zakłada zgłoszenie „[sędzia] Limit prób: …”; zamknięcie zgłoszenia przez właściciela zeruje licznik;
4. uruchamia sędziego z `main` (`git archive main sedzia`, `python -P`) w piaskownicy bwrap: bez sieci, z ukrytymi `/home`, `/run`, `/srv`, `/tmp`, z sędzią i środowiskiem Pythona tylko do odczytu, we własnej przestrzeni procesów; od tej chwili kopia repozytorium jest niezaufana i usługa nie uruchamia w niej gita;
5. przy wyroku pozytywnym wypycha z czystego repozytorium dokładnie oceniony commit, otwiera pull request i dla `testy/…` i `kod/…` włącza automatyczne scalenie;
6. wynik zapisuje w `/srv/sedzia/wyniki/<gałąź>.txt` (czytelny dla sesji), dziennik w `/srv/sedzia/wyniki/dziennik.log`.

**Na GitHubie** (reguła „ochrona-main”, bez wyjątków): wymagane sprawdzenia „sedzia” (sędzia z gałęzi bazowej, ponownie, na czystej maszynie) i „recenzja”.

**Recenzja** (`.github/workflows/recenzja.yml`, `sedzia/ci/recenzja.py`): zdarzenie `pull_request_target`, więc przepływ i skrypt pochodzą z `main`. Recenzent (Claude Code, sekret `CLAUDE_CODE_OAUTH_TOKEN`) nie ma żadnych narzędzi: dostaje AGENTS.md i zlecenie z `main`, różnice, pełne zmienione pliki i kontekst (dla testów `src/`, dla kodu testy zlecenia), oddzielone znacznikami z losowym kluczem. Tekst w danych skierowany do recenzenta jest powodem odrzucenia. Ostatni wiersz odpowiedzi musi brzmieć dokładnie „WERDYKT: PRZYJĘTE”; wszystko inne — w tym brak sekretu, błąd i za duża zmiana — to odrzucenie. Recenzja trafia do komentarza pull requesta.

**Powiadomienia właściciela:** komentarz recenzji w pull requeście (autor dostaje powiadomienie), nieudany przebieg CI, zgłoszenia od usługi (`.github/workflows/zgloszenia.yml`, zakłada je github-actions).

**Znane ograniczenia.**
- [niesprawdzone do pierwszego przebiegu] wymagane sprawdzenie z `pull_request_target`, automatyczne scalenie przez token fine-grained, wersja `@anthropic-ai/claude-code@2.1.332` w npm, powiadomienia e-mail.
- Zgoda dwóch modeli nie jest dowodem: recenzja jest dodatkową bramką, nie zastępuje sędziego.
- Kod pod testem działa w procesie pytest, więc teoretycznie może podrobić raport. Sędzia odrzuca statycznie znane drogi (krok „zakazy”, `sedzia/zakazy.py`: `atexit`, `os._exit`, `sys.argv`, `sys.modules`, `os.environ`, `importlib`, `ctypes`, `eval`/`exec`, dynamiczne `getattr`, hooki i obiekty pytest w testach, napisy w rodzaju „MUTANT”/„junit”), uruchamia narzędzia z `python -I`, bierze konfigurację mutmut z bazy i po przebiegach sprawdza, że repozytorium się nie zmieniło (krok „nienaruszalnosc”). Statyczne zakazy w Pythonie nie są pełną piaskownicą — obejście, którego nie przewidziano, może wykryć tylko recenzja. Prompt injection może osłabić recenzję, ale tekst skierowany do recenzenta jest powodem odrzucenia.
- Na PC sędzia działa na Pythonie 3.14, w CI na 3.13 — wyroki mogą się różnić; wiążące jest sprawdzenie „sedzia” w CI.
- Reguła nie wymaga gałęzi aktualnej względem `main`; połączenie zmian sprawdza dopiero przebieg na `main` i nocny. [propozycja] kolejka scalania (merge queue).
- Ucieczka z piaskownicy bwrap dałaby dostęp do tokenu konta `sedzia`; token nie może jednak zmienić przepływów CI ani reguł ochrony.
- Zmiany `.github/` wprowadza wyłącznie właściciel (edytor GitHuba albo własny klucz poza zasięgiem sesji AI).
- Pull request z rozwidlenia dostaje czerwone „recenzja” (jawny błąd, nie pominięcie). Jego własny `sedzia.yml` może jednak dać zielone „sedzia” — takich pull requestów nie scala się bez przeglądu; w ustawieniach Actions: zatwierdzanie przebiegów dla wszystkich spoza repozytorium.
- Usługa przepuszcza w `src/` i w testach zlecenia wyłącznie pliki `.py`; recenzja odrzuca każdy plik binarny. Zgłoszenia limitu liczą się tylko, gdy założył je github-actions, a licznik zeruje zamknięcie przez właściciela.
- Przeglądarka, w której właściciel jest zalogowany do GitHuba, nie może być używana przez sesje AI do działań w repozytorium.
