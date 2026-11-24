# Zlecenie 0001 — narzędzie rejestrów przeglądu

SZKIC AI — do pracy autora.

- **Zlecający:** Claude z Projektu „Agent Studio — zaplecze techniczne” (sesja prowadząca), 24.11.2026.
- **Cel:** jedno narzędzie, które sprawdza pliki rejestrów przeglądu (możliwości, kandydaci) i scala partie wierszy w jeden rejestr. Partie oddają sesje czytające, scala sesja prowadząca (plan przeglądu AS_30).
- **Zakres plików autora testów:** `testy/zlecenie_0001/**`
- **Zakres plików wykonawcy:** `src/fabruna/rejestry/**`
- **Poza zakresem:** ocena treści wierszy, sieć, Dysk Google, interfejs graficzny, zależności spoza biblioteki standardowej Pythona.
- **Budżet:** autor testów — najwyżej 3 podejścia do sędziego; wykonawca — najwyżej 5; każda sesja do 400 tys. tokenów. Po wyczerpaniu limitu sesja oddaje raport z diagnozą, nie „zrobione”.

## Interfejs

Pakiet `fabruna.rejestry`, uruchamiany jako moduł:

    python -m fabruna.rejestry sprawdz --rodzaj {mozliwosci|kandydaci} [--partia] [--json] PLIK
    python -m fabruna.rejestry scal --rodzaj {mozliwosci|kandydaci} --wyjscie PLIK_WYJ [--rejestr ISTNIEJACY] [--raport PLIK_RAPORTU] [--json] [PARTIA ...]

Kody wyjścia: `0` — dane poprawne; `1` — błędy w danych; `2` — błąd użycia albo wejścia/wyjścia (brak pliku, zły argument).

Błędy trafiają na standardowe wyjście błędów, po jednym w wierszu, w postaci `PLIK:WIERSZ: KOLUMNA: opis`. Wiersze liczone od 1, nagłówek ma numer 1. Dla błędu całego pliku (na przykład nagłówka) KOLUMNA to `-`.

Z opcją `--json` na standardowe wyjście trafia dokładnie jeden obiekt JSON: `{"poprawny": bool, "wiersze": int, "bledy": [...], "ostrzezenia": [...]}`. Każdy błąd i każde ostrzeżenie to obiekt z polami `plik`, `wiersz`, `kolumna`, `opis`. `wiersze` to liczba wierszy danych (bez nagłówka).

Funkcje biblioteczne (do testów bez podprocesu):

- `fabruna.rejestry.sprawdz_plik(sciezka, rodzaj, partia=False)` zwraca obiekt wyniku;
- `fabruna.rejestry.scal_pliki(partie, rodzaj, rejestr=None)` zwraca parę `(wiersze, wynik)`, gdzie `wiersze` to lista słowników w kolejności wyjściowej;
- obiekt wyniku ma listy `bledy` i `ostrzezenia` (elementy z polami `plik`, `wiersz`, `kolumna`, `opis`) oraz właściwość `poprawny` (prawda, gdy lista błędów jest pusta).

## Format plików

- Kodowanie UTF-8. Znak BOM na wejściu jest przyjmowany, na wyjściu nigdy nie jest zapisywany.
- Separator pól: średnik. Znak cytowania: cudzysłów prosty; cudzysłów wewnątrz pola jest podwajany.
- Wyjście: wszystkie pola w cudzysłowach, koniec wiersza `\n`, plik kończy się znakiem `\n`.
- Pierwszy wiersz to nagłówek, dokładnie jak niżej (nazwy i kolejność).

### Rejestr możliwości (`--rodzaj mozliwosci`)

Nagłówek: `id;mozliwosc;obszar;zrodlo;data_zrodla;kotwica;stare_studio;dowod_stare_studio;poziom_waznosci;test_odbioru;kandydaci;status;partia;uwagi`

- `id`: wzorzec `M-` i cztery cyfry (na przykład `M-0001`).
- `mozliwosc`: wymagane, od 10 do 300 znaków.
- `obszar`: wymagane, jedna z wartości: `asystent codzienny`, `praca nocna i samodzielna`, `pisanie i redakcja`, `gra fabularna`, `media`, `kod i gry`, `wiedza i notatki`, `telefon i nadzór`, `bezpieczeństwo i kopie`, `sprzęt i system`, `firma`, `dziesiątka`, `jakość i testy`, `inne`.
- `zrodlo`: wymagane.
- `data_zrodla`: wymagane, data w postaci `RRRR-MM-DD`.
- `kotwica`: najwyżej 120 znaków.
- `stare_studio`: wymagane, jedna z wartości: `tak`, `częściowo`, `nie`, `nie wiadomo`.
- `dowod_stare_studio`: wymagane, gdy `stare_studio` to `tak` albo `częściowo`.
- `poziom_waznosci`: puste albo jedna z wartości: `rdzeń`, `pierwszy miesiąc`, `później`, `odrzucone`.
- `kandydaci`: puste albo lista identyfikatorów kandydatów (`K-` i cztery cyfry) rozdzielonych przecinkiem, ze spacjami lub bez.
- `status`: wymagane, jedna z wartości: `zebrane`, `scalone`, `ocenione`.
- `partia`: wymagane.
- `test_odbioru`, `uwagi`: dowolne.

### Rejestr kandydatów (`--rodzaj kandydaci`)

Nagłówek: `id;nazwa;rodzaj;mozliwosci;zrodlo;data_zrodla;poprzedni_werdykt;data_werdyktu;stan_dzis;koszt;ryzyko;dowod;poziom_waznosci;poziom_dostepu;wspolgranie;werdykt;status;partia;uwagi`

- `id`: wzorzec `K-` i cztery cyfry.
- `nazwa`: wymagane, od 2 do 120 znaków.
- `rodzaj`: wymagane, jedna z wartości: `model`, `wtyczka`, `narzędzie`, `system`, `metoda`, `własny składnik`.
- `mozliwosci`: puste albo lista identyfikatorów możliwości (`M-` i cztery cyfry) rozdzielonych przecinkiem.
- `zrodlo`: wymagane.
- `data_zrodla`: wymagane, data `RRRR-MM-DD`.
- `data_werdyktu`: data `RRRR-MM-DD`; wymagane, gdy `poprzedni_werdykt` nie jest pusty.
- `dowod`: puste albo jedna z wartości: `sprawdzone na PC`, `z dokumentacji`, `nieznane`.
- `poziom_waznosci`: jak w rejestrze możliwości.
- `poziom_dostepu`: puste albo jedna z wartości: `tylko Qba`, `agent za zgodą`, `agent w piaskownicy`, `agent z siecią`.
- `status`: wymagane, jedna z wartości: `zebrane`, `scalone`, `ocenione`.
- `partia`: wymagane.
- pozostałe pola: dowolne.

Wartości słownikowe porównuje się dokładnie (wielkość liter i polskie znaki mają znaczenie). Białe znaki na początku i końcu pola nie są obcinane: pole `" tak"` jest błędem słownika.

## Kryteria odbioru

Każde kryterium musi mieć co najmniej jeden test, którego nazwa zaczyna się od `test_kNN_` (na przykład `test_k03_powtorzone_id`).

- **K01 — nagłówek.** Plik z nagłówkiem innym niż wzorzec (brak kolumny, kolumna nadmiarowa, inna kolejność) jest niepoprawny; komunikat wymienia nazwy kolumn brakujących i nadmiarowych. Plik pusty jest niepoprawny. Plik z samym poprawnym nagłówkiem jest poprawny i ma 0 wierszy.
- **K02 — pola wymagane i długości.** Brak wartości w polu wymaganym, zbyt krótka albo zbyt długa wartość dają błąd ze wskazaniem wiersza i kolumny. Wszystkie błędy pliku są zgłaszane w jednym przebiegu, nie tylko pierwszy.
- **K03 — identyfikatory.** Zły wzorzec identyfikatora to błąd. Powtórzony identyfikator to błąd zgłaszany przy drugim i każdym kolejnym wystąpieniu, z numerem wiersza pierwszego wystąpienia w opisie. Pusty identyfikator jest dozwolony tylko z opcją `--partia` (w bibliotece `partia=True`); bez niej jest błędem.
- **K04 — słowniki.** Wartość spoza słownika w polach słownikowych obu rejestrów to błąd; pola, które mogą być puste, przyjmują wartość pustą.
- **K05 — zależności między polami.** `dowod_stare_studio` wymagane przy `tak` i `częściowo`; `data_werdyktu` wymagane przy niepustym `poprzedni_werdykt`; listy identyfikatorów w polach `kandydaci` i `mozliwosci` muszą mieć poprawne wzorce, a pusty element listy (na przykład `K-0001,,K-0002`) to błąd.
- **K06 — daty.** Data musi mieć postać `RRRR-MM-DD` i istnieć w kalendarzu (`2026-02-30` to błąd, `2024-02-29` jest poprawna).
- **K07 — scalanie: nadawanie numerów.** Wiersze bez identyfikatora dostają kolejne wolne numery: o jeden większe od najwyższego numeru obecnego w istniejącym rejestrze i we wszystkich partiach, w kolejności podania plików, a w pliku w kolejności wierszy. Wiersze z identyfikatorem go zachowują.
- **K08 — scalanie: konflikty.** Ten sam identyfikator z identyczną treścią w dwóch wejściach daje jeden wiersz bez błędu. Ten sam identyfikator z różną treścią to błąd wymieniający oba pliki i oba wiersze. Gdy są błędy, plik wyjściowy nie powstaje, a istniejący plik o tej nazwie pozostaje bez zmian.
- **K09 — scalanie: wynik.** Wyjście jest posortowane rosnąco po identyfikatorze, przechodzi `sprawdz` bez opcji `--partia` i zachowuje wszystkie pola wierszy bez zmian poza nadanym identyfikatorem. Scalenie samego istniejącego rejestru bez partii daje plik identyczny bajt w bajt z rejestrem zapisanym w formacie wyjściowym.
- **K10 — ostrzeżenia o powtórzonej treści.** Wiersze, których pole kluczowe (`mozliwosc` albo `nazwa`) jest takie samo po sprowadzeniu do małych liter, zwinięciu białych znaków i usunięciu końcowej kropki, dają ostrzeżenie wskazujące oba wiersze. Ostrzeżenie nie zmienia kodu wyjścia. Opcja `--raport` zapisuje ostrzeżenia do pliku tekstowego, po jednym w wierszu.
- **K11 — format.** BOM na wejściu jest przyjmowany i nie trafia na wyjście. Pola ze średnikiem, cudzysłowem i znakiem nowego wiersza przechodzą przez `scal` bez zmiany treści. Wyjście ma wszystkie pola w cudzysłowach i końce wierszy `\n`.
- **K12 — kody wyjścia i JSON.** Kody `0`, `1`, `2` zgodnie z opisem; nieistniejący plik wejściowy i nieznany `--rodzaj` dają kod `2`. Z `--json` standardowe wyjście zawiera dokładnie jeden poprawny obiekt JSON o opisanych polach, także przy błędach danych.
- **K13 — bez zależności zewnętrznych.** Kod w `src/fabruna/rejestry` importuje wyłącznie moduły biblioteki standardowej i własnego pakietu.

## Dowód wykonania

Wyrok sędziego w trybie `kod` dla tego zlecenia: testy zlecenia zielone i stabilne, cały zestaw projektu zielony, wynik testów mutacyjnych co najmniej 70%, skan sekretów czysty, żadnej zmiany poza zakresem plików wykonawcy.
