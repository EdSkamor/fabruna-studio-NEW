# AGENTS.md — zasady pętli inżynierskiej

SZKIC AI — do pracy autora.

Obowiązuje każdą sesję AI pracującą w tym repozytorium. Mechanizm i dokładne definicje bramek: `dokumentacja/PETLA_INZYNIERSKA.md`.

## Zasada nadrzędna

Program nie sprawdza sam siebie. Wyrok wydaje sędzia-skrypt (`python -m sedzia`), nigdy sesja, która wykonała pracę. „Zrobione” znaczy wyłącznie: wyrok sędziego pozytywny. Wiążący jest wyrok z CI, a dopóki CI nie działa — wyrok uruchomiony ponownie przez sesję prowadzącą na czystym klonie. Wyrok ogłoszony przez sesję, która wykonała pracę, jest tylko zapowiedzią.

## Role (każda w osobnej sesji)

| Rola | Co oddaje | Gdzie pracuje |
|---|---|---|
| Zlecający | zlecenie z kryteriami odbioru K01… | `zlecenia/NNNN-opis.md` (gałąź `zasady/…`) |
| Autor testów | testy, które bez kodu są czerwone | gałąź `testy/NNNN-opis`, tylko nowe pliki w `testy/zlecenie_NNNN/` |
| Wykonawca | kod, który przechodzi testy | gałąź `kod/NNNN-opis`, tylko `src/` |
| Sędzia-skrypt | wyrok w `wyrok.json` | `sedzia/` — nie jest sesją AI |
| Recenzent | recenzję zmiany i wyroku | niezależna sesja; nie pisał ani testów, ani kodu |
| Właściciel | zgodę na scalenie | zatwierdza pull request |

Autor testów, wykonawca i recenzent to trzy różne sesje. Wykonawca nie może zmienić testów ani sędziego.

## Kolejność pracy nad zleceniem

1. Zlecenie: cel, zakres plików, budżet, interfejs, kryteria K01…, dowód wykonania (`zlecenia/WZOR.md`).
2. Testy: gałąź `testy/NNNN-opis`. Wyrok `python -m sedzia testy --zlecenie NNNN --baza main` musi być pozytywny: testy czerwone na obecnym kodzie, stabilne, każde kryterium pokryte. Scalenie przez właściciela.
3. Kod: gałąź `kod/NNNN-opis` od aktualnego `main`. Praca do pozytywnego wyroku `python -m sedzia kod --zlecenie NNNN --baza main` albo do limitu podejść ze zlecenia.
4. Recenzja z niezależnej sesji: zmiana, wyrok, zgodność ze zleceniem (także węższy zakres plików ze zlecenia).
5. Scalenie przez właściciela.

Po wyczerpaniu limitu podejść sesja oddaje raport z diagnozą (co próbowała, co pokazał sędzia, gdzie widzi przyczynę), a nie „zrobione”.

## Zakazy

- Wykonawca nie dotyka `testy/`, `sedzia/`, `.github/`, `zlecenia/`, `dokumentacja/`, `pyproject.toml`, `AGENTS.md`, `.gitignore`, `.secrets.baseline`. Sędzia odrzuca każdą taką zmianę, także niezatwierdzoną i w pliku nieśledzonym.
- Nikt nie osłabia ani nie usuwa istniejących testów bez osobnej zmiany typu „zasady” i zgody właściciela. Gałąź `testy/…` może wyłącznie dodawać pliki.
- Nikt nie omija bramek: żadnego `pragma: no mutate`, żadnego `pragma: allowlist secret`, żadnego kodu, który rozpoznaje, że jest testowany albo mutowany (odwołania do pytest i mutmut w `src/` sędzia odrzuca).
- Zmiany sędziego, jego testów, CI, zleceń, dokumentacji i konfiguracji robi tylko sesja prowadząca na gałęzi `zasady/opis`, za zgodą właściciela.
- W repozytorium nie ma sekretów, danych klientów ani treści fabularnych. Dane w testach są fikcyjne.
- Bez `git push --force` na `main`, bez wyłączania kroków CI, bez instalowania narzędzi spoza przypiętych.

## Testy zlecenia — konwencje wymuszane przez sędziego

- Nazwa testu zaczyna się od `test_kNN_` (na przykład `test_k03_powtorzone_id`); każde kryterium ma co najmniej jeden taki test.
- Plik testów musi dać się zebrać bez kodu zlecenia: importy testowanego kodu wewnątrz testu albo w fixture, nie na górze pliku.
- Testy są deterministyczne: bez sieci, zegara i losowości; trzy przebiegi muszą dać ten sam wynik każdego testu.
- Testy zależą wyłącznie od `src/` i `testy/` (tylko te katalogi trafiają do piaskownicy testów mutacyjnych).
- Mutanta zabija tylko test, który woła kod w tym samym procesie. Test przez podproces (fixture `srodowisko_podprocesu`) sprawdza zachowanie z wiersza poleceń, ale nie podnosi wyniku mutacyjnego.
- Test czytający pliki źródłowe bierze katalog z fixture `katalog_src`.
- Bez własnych znaczników pytest (`--strict-markers`), bez `skip` i `xfail`: w trybie „kod” każdy test zlecenia musi mieć wynik „passed”.
- Każdy naprawiony błąd zostawia test, który go odtwarza.

## Kod

- Kod zadań trafia do pakietu `src/fabruna/`. Sędzia pilnuje całego `src/`; węższy zakres ze zlecenia sprawdza recenzent.
- Próg wyniku mutacyjnego: 70% na plikach zmienionych względem bazy, liczony testami zlecenia.

## Wyniki AI

Wszystko, co wytworzy AI, jest szkicem z oznaczeniem „SZKIC AI — do pracy autora”. Status materiału poza „szkic AI” zmienia wyłącznie właściciel.

## Polecenia

    python -m pip install --group dev                      # przypięte: pytest, mutmut, detect-secrets
    python -m sedzia testy  --zlecenie NNNN --baza main    # gałąź testy/NNNN-opis
    python -m sedzia kod    --zlecenie NNNN --baza main    # gałąź kod/NNNN-opis
    python -m sedzia zasady --baza main                    # gałąź zasady/opis
    python -m pytest testy/sedzia -q                       # testy samego sędziego

Kody wyjścia sędziego: 0 — wyrok pozytywny, 1 — negatywny, 2 — błąd użycia albo wewnętrzny.
