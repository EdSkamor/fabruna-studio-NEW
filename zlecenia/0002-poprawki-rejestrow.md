# Zlecenie 0002 — poprawki narzędzia rejestrów po recenzji

SZKIC AI — do pracy autora.

- **Zlecający:** Claude, sesja prowadząca na PC Qby (most), 24.11.2026, na podstawie recenzji niezależnej sesji do zlecenia 0001.
- **Cel:** usunąć błędy znalezione w recenzji `fabruna.rejestry` (wyjątki zamiast kodów wyjścia, przepełnienie numeracji, nieatomowy zapis, niespójne traktowanie istniejącego rejestru) i doprecyzować trzy zachowania, których zlecenie 0001 nie rozstrzygało.
- **Baza:** kod i testy zlecenia 0001 w `main`. Wszystko, czego to zlecenie nie zmienia, działa dalej według zlecenia 0001; testy z `testy/zlecenie_0001/` zostają zielone.
- **Zakres plików autora testów:** `testy/zlecenie_0002/**`
- **Zakres plików wykonawcy:** `src/fabruna/rejestry/**`
- **Poza zakresem:** numeracja wierszy według linii fizycznych (zostaje numer rekordu CSV, nagłówek = 1); zawężenie normalizacji z K10 zlecenia 0001 (`casefold`, wszystkie końcowe kropki — zostaje jak jest); nowe polecenia i opcje; zależności spoza biblioteki standardowej.
- **Budżet:** autor testów — najwyżej 3 podejścia do sędziego; wykonawca — najwyżej 5; każda sesja do 300 tys. tokenów. Po wyczerpaniu limitu sesja oddaje raport z diagnozą, nie „zrobione”.

## Interfejs

Bez zmian względem zlecenia 0001: te same polecenia, opcje, funkcje biblioteczne, kody wyjścia (`0` — dane poprawne, `1` — błędy w danych, `2` — błąd użycia albo wejścia/wyjścia) i format zgłoszeń `PLIK:WIERSZ: KOLUMNA: opis`.

Zmiany zachowania opisują kryteria poniżej. Zasada ogólna: `main(argv)` nigdy nie rzuca wyjątku z powodu danych wejściowych, ścieżek ani zapisu — zawsze zwraca kod wyjścia. Z opcją `--json` przy kodzie `0` i `1` na standardowe wyjście trafia dokładnie jeden obiekt JSON (jak w zleceniu 0001); przy kodzie `2` standardowe wyjście może być puste, a przyczyna trafia na standardowe wyjście błędów.

## Kryteria odbioru

Każde kryterium musi mieć co najmniej jeden test, którego nazwa zaczyna się od `test_kNN_` (na przykład `test_k01_pole_200_tysiecy_znakow`).

- **K01 — długie pola.** Pole dowolnej długości (co najmniej 1 000 000 znaków) jest wczytywane bez wyjątku. Długie pole w kolumnie bez limitu (na przykład `uwagi`) daje plik poprawny, kod `0`, a `scal` przenosi je na wyjście bez zmiany treści. Długie pole w kolumnie z limitem (`mozliwosc`, `nazwa`, `kotwica`) daje zwykły błąd długości z K02 zlecenia 0001, kod `1`; z `--json` standardowe wyjście zawiera jeden poprawny obiekt JSON.
- **K02 — błędne ścieżki.** Ścieżka zawierająca bajt NUL, ścieżka wskazująca katalog zamiast pliku i plik nieczytelny jako UTF-8 dają kod `2` i jeden wiersz z przyczyną na standardowym wyjściu błędów; `main` nie rzuca wyjątku. Dotyczy plików podanych do `sprawdz`, partii, `--rejestr`, `--wyjscie` i `--raport`.
- **K03 — koniec numeracji.** Gdy wiersz bez identyfikatora miałby dostać numer większy niż `9999`, `scal` zgłasza błąd danych (kod `1`) przy tym wierszu (jego plik i numer, kolumna `id`), z opisem zawierającym słowa „brak wolnego numeru”; plik wyjściowy nie powstaje, a istniejący plik o tej nazwie pozostaje bez zmian. Wiersz z identyfikatorem `M-9999` albo `K-9999` bez nadawania numerów nadal scala się poprawnie.
- **K04 — zapis wszystko albo nic.** `scal` zapisuje plik wyjściowy i plik `--raport` tak, że po zakończeniu z kodem innym niż `0` żaden z nich nie powstał ani nie zmienił się (istniejące pliki zostają identyczne bajt w bajt), a po zakończeniu z kodem `0` oba mają pełną treść. Przykład: `--raport` w nieistniejącym katalogu daje kod `2` i plik wyjściowy nie powstaje. W katalogach docelowych nie zostają pliki tymczasowe ani przy kodzie `0`, ani przy kodzie `2`.
- **K05 — istniejący rejestr jest pełnym rejestrem.** Plik podany w `--rejestr` jest sprawdzany jak w `sprawdz` bez opcji `--partia`: wiersz z pustym identyfikatorem w rejestrze to błąd danych (kod `1`), plik wyjściowy nie powstaje. Puste identyfikatory są dozwolone tylko w partiach. To samo w bibliotece: `scal_pliki(partie, rodzaj, rejestr=...)` zwraca wynik z tym błędem.
- **K06 — jedno zgłoszenie na komórkę.** W `scal` powtórzony identyfikator z różną treścią w obrębie jednego pliku daje dokładnie jeden błąd dla drugiego wystąpienia (plik, wiersz, kolumna `id`), z numerem wiersza pierwszego wystąpienia w opisie. Ogólnie: żadne polecenie nie zgłasza dwóch błędów o tym samym pliku, wierszu i kolumnie.
- **K07 — puste wiersze na końcu pliku.** Całkowicie puste wiersze (bez żadnego znaku poza końcem wiersza) na końcu pliku są pomijane: plik jest poprawny, nie liczą się do `wiersze` i nie trafiają na wyjście `scal`. Pusty wiersz między wierszami danych pozostaje błędem z kolumną `-`.
- **K08 — spacje w listach identyfikatorów.** Spacje przed i po przecinku są dozwolone w obu polach list: `kandydaci` i `mozliwosci` (na przykład `M-0001, M-0002`). Pusty element listy pozostaje błędem (K05 zlecenia 0001). `scal` przenosi wartość pola bez zmiany.

## Dowód wykonania

Wyrok sędziego w trybie `kod` dla tego zlecenia: testy zlecenia zielone i stabilne, cały zestaw projektu zielony (w tym `testy/zlecenie_0001/`), wynik testów mutacyjnych co najmniej 70%, skan sekretów czysty, żadnej zmiany poza zakresem plików wykonawcy.

## Decyzje do potwierdzenia przez właściciela

Scalenie tego zlecenia oznacza przyjęcie trzech rozstrzygnięć, których zlecenie 0001 nie zawierało **[propozycja]**:

1. K05 — pusty identyfikator w istniejącym rejestrze jest błędem (zamiast nadawania mu numeru), bo rejestr to wynik poprzedniego scalenia i zgodnie z K09 zlecenia 0001 przechodzi `sprawdz` bez `--partia`.
2. K07 — puste wiersze pomijane tylko na końcu pliku (arkusze często je dopisują), w środku pliku dalej błąd.
3. K08 — spacje dozwolone także w liście `mozliwosci`, dla spójności z `kandydaci`.
