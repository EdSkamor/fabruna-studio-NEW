# Zlecenie NNNN — tytuł

SZKIC AI — do pracy autora.

<!-- Plik: zlecenia/NNNN-krotki-opis.md. Numer to cztery cyfry; gałęzie: testy/NNNN-opis i kod/NNNN-opis. -->

- **Zlecający:** kto i kiedy (rola albo sesja, data).
- **Cel:** jedno–dwa zdania: co ma powstać i po co.
- **Zakres plików autora testów:** `testy/zlecenie_NNNN/**`
- **Zakres plików wykonawcy:** `src/fabruna/<pakiet>/**`
- **Poza zakresem:** czego to zlecenie nie obejmuje.
- **Budżet:** autor testów — najwyżej N podejść do sędziego; wykonawca — najwyżej M; limit zużycia na sesję (na przykład liczba tokenów). Po wyczerpaniu limitu sesja oddaje raport z diagnozą, nie „zrobione”.

## Interfejs

Co dokładnie powstaje: nazwy modułów i funkcji, argumenty, wartości zwracane, kody wyjścia, format wejścia i wyjścia. Testy powstają wyłącznie z tego opisu i z kryteriów, więc musi być jednoznaczny.

Każde zachowanie dostępne z wiersza poleceń powinno mieć też funkcję, którą test wywoła bezpośrednio: mutanta zabija tylko test wołający kod w tym samym procesie.

## Kryteria odbioru

Każde kryterium musi mieć co najmniej jeden test, którego nazwa zaczyna się od `test_kNN_` (na przykład `test_k01_pusty_plik`). Sędzia czyta identyfikatory z wierszy w tej postaci:

- **K01 — krótka nazwa.** Sprawdzalne zdanie: wejście, oczekiwany wynik, przypadki brzegowe.
- **K02 — krótka nazwa.** …

## Dowód wykonania

Wyrok sędziego w trybie `kod` dla tego zlecenia: testy zlecenia zielone i stabilne, cały zestaw projektu zielony, wynik testów mutacyjnych co najmniej 70%, skan sekretów czysty, żadnej zmiany poza zakresem plików wykonawcy.
