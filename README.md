# Fabruna Studio

SZKIC AI — do pracy autora.

Nowe repozytorium Fabruna Studio. Na razie zawiera wyłącznie szkielet pętli inżynierskiej: sędziego (skrypt, który wydaje wyrok o każdej zmianie), jego testy, zasady dla agentów i wzór zlecenia. Kod zadań dojdzie zleceniami, do pakietu `src/fabruna/`.

## Zasada

Program nie sprawdza sam siebie. Zlecenie, testy, kod i recenzja powstają w osobnych sesjach, a o tym, czy praca jest zrobiona, rozstrzyga sędzia-skrypt. Autor kodu nie może zmienić testów ani sędziego.

- Zasady dla agentów: `AGENTS.md`
- Mechanizm, definicje bramek, ograniczenia: `dokumentacja/PETLA_INZYNIERSKA.md`
- Wzór zlecenia: `zlecenia/WZOR.md`

## Układ repozytorium

| Ścieżka | Zawartość |
|---|---|
| `sedzia/` | sędzia; tylko biblioteka standardowa, narzędzia woła przez podproces |
| `testy/sedzia/` | testy samego sędziego |
| `testy/zlecenie_NNNN/` | testy zlecenia NNNN (pisze autor testów) |
| `testy/conftest.py` | wspólne fixture testów zleceń |
| `src/fabruna/` | pakiet z kodem zadań (na razie pusty) |
| `zlecenia/` | zlecenia i ich wzór |
| `dokumentacja/` | opis pętli inżynierskiej |
| `.github/` | przepływ CI „sedzia” i właściciele ścieżek |
| `pyproject.toml` | pakiet, przypięte zależności deweloperskie, konfiguracja pytest i mutmut |

## Jak uruchomić sędziego

Wymagany Python 3.13 i git.

    python3.13 -m venv .venv
    .venv/bin/python -m pip install --upgrade pip
    .venv/bin/python -m pip install --group dev

    .venv/bin/python -m sedzia testy  --zlecenie 0001 --baza main    # na gałęzi testy/0001-opis
    .venv/bin/python -m sedzia kod    --zlecenie 0001 --baza main    # na gałęzi kod/0001-opis
    .venv/bin/python -m sedzia zasady --baza main                    # na gałęzi zasady/opis
    .venv/bin/python -m sedzia calosc --mutacje                      # stan całego repozytorium, jak w nocy

Kody wyjścia: `0` — wyrok pozytywny, `1` — negatywny, `2` — błąd użycia albo wewnętrzny. Sędzia wypisuje podsumowanie kroków i zapisuje `wyrok.json` (plik nie trafia do repozytorium). Wyrok wiążący wydaje CI; przebieg lokalny jest pomocniczy.

Testy samego sędziego:

    .venv/bin/python -m pytest testy/sedzia -q                   # około minuty
    .venv/bin/python -m pytest testy/sedzia -q -m "not wolny"    # bez testów mutacyjnych

## Stan

Szkielet. Przepływ CI nie był jeszcze uruchomiony na GitHubie; lista rzeczy niesprawdzonych jest w `dokumentacja/PETLA_INZYNIERSKA.md`, punkt 11.
