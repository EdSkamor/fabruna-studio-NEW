# Zlecenie 0003 — zapis wyjścia i stan procesu w narzędziu rejestrów

SZKIC AI — do pracy autora.

- **Zlecający:** Claude, sesja prowadząca na PC Qby (most), 25.11.2026, na podstawie automatycznej recenzji PR #7 (zlecenie 0002).
- **Cel:** domknąć uwagi recenzji 0002: zapis wszystko-albo-nic także przy awarii podmiany, zachowanie dowiązań i uprawnień istniejącego wyjścia, brak zmiany globalnego stanu modułu `csv`, niemaskowanie błędów programistycznych.
- **Baza:** kod i testy zleceń 0001 i 0002 w `main`. Wszystko, czego to zlecenie nie zmienia, działa dalej według nich; testy z `testy/zlecenie_0001/` i `testy/zlecenie_0002/` zostają zielone.
- **Zakres plików autora testów:** `testy/zlecenie_0003/**`
- **Zakres plików wykonawcy:** `src/fabruna/rejestry/**`
- **Poza zakresem:** nowe polecenia i opcje; blokady plików i wyścigi między procesami; systemy inne niż Linux; zależności spoza biblioteki standardowej.
- **Budżet:** autor testów — najwyżej 3 podejścia do sędziego; wykonawca — najwyżej 5; każda sesja do 300 tys. tokenów. Po wyczerpaniu limitu sesja oddaje raport z diagnozą, nie „zrobione”.

## Interfejs

Polecenia, opcje, kody wyjścia i format zgłoszeń bez zmian względem zleceń 0001 i 0002.

Nowa funkcja biblioteczna, eksportowana z `fabruna.rejestry`: `zapisz_wszystko_albo_nic(cele)`, gdzie `cele` to lista par `(ścieżka, tekst)`. Zapisuje wszystkie pliki albo żadnego; po błędzie rzuca `OSError` (albo jego podklasę). `scal` z wiersza poleceń używa tej funkcji. Podmiana celu odbywa się przez `os.replace` wołane jako atrybut modułu `os` (test może je podmienić przez `monkeypatch`).

## Kryteria odbioru

Każde kryterium musi mieć co najmniej jeden test, którego nazwa zaczyna się od `test_kNN_`.

- **K01 — awaria podmiany.** Gdy `os.replace` zgłosi `OSError` przy podmianie drugiego z dwóch celów, `zapisz_wszystko_albo_nic` rzuca `OSError`, a pierwszy cel ma dokładnie treść sprzed wywołania (bajt w bajt), albo nie istnieje, jeśli nie istniał wcześniej. W katalogach celów nie zostają pliki tymczasowe. Przez `main` (`scal` z `--raport`) ta sama sytuacja daje kod `2` i jeden wiersz z przyczyną na standardowym wyjściu błędów.
- **K02 — dowiązanie symboliczne jako cel.** Gdy `--wyjscie` albo `--raport` jest dowiązaniem symbolicznym do istniejącego pliku, po kodzie `0` ścieżka nadal jest tym samym dowiązaniem, a nowa treść jest w pliku, na który wskazuje. Dowiązanie do nieistniejącego pliku daje kod `2`, nic nie powstaje.
- **K03 — uprawnienia istniejącego wyjścia.** Gdy plik wyjściowy (albo plik `--raport`) istniał, po kodzie `0` ma ten sam tryb uprawnień co przed scaleniem (na przykład `0o640`). Nowy plik dostaje tryb `0o666` z nałożoną bieżącą maską `umask`.
- **K04 — stan modułu csv.** Po wywołaniu `sprawdz_plik`, `scal_pliki` albo `main` wartość `csv.field_size_limit()` jest taka sama jak przed wywołaniem, także gdy wywołanie zakończyło się błędem. Pola dłuższe niż 131 072 znaki nadal są wczytywane (K01 zlecenia 0002).
- **K05 — błędy programistyczne nie są maskowane.** `main` zamienia na kod `2` tylko błędy wejścia/wyjścia i błędy danych z K02 zlecenia 0002 (bajt NUL w ścieżce, plik nieczytelny jako UTF-8, błąd CSV). `ValueError` rzucony z innej przyczyny — w teście: `scal_pliki` podmienione przez `monkeypatch` tak, że rzuca `ValueError` — wychodzi z `main` jako wyjątek.

## Dowód wykonania

Wyrok sędziego w trybie `kod` dla tego zlecenia: testy zlecenia zielone i stabilne, cały zestaw projektu zielony, wynik testów mutacyjnych co najmniej 70%, skan sekretów czysty, żadnej zmiany poza zakresem plików wykonawcy.

## Decyzje do potwierdzenia przez właściciela

Scalenie tego zlecenia oznacza przyjęcie **[propozycja]**:

1. K02 — zapis przez dowiązanie (zmienia się plik docelowy, dowiązanie zostaje), zamiast zastępowania dowiązania zwykłym plikiem.
2. K05 — nieoczekiwany `ValueError` kończy program śladem stosu zamiast kodem `2`: błąd w programie ma być widoczny, nie udawać błędu użytkownika.
