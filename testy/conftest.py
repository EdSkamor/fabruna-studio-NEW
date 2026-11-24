"""Wspólne fixture testów zleceń. Plik zmienia wyłącznie gałąź typu „zasady”."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

KATALOG_SRC = Path(__file__).resolve().parent.parent / "src"


@pytest.fixture
def srodowisko_podprocesu() -> dict[str, str]:
    """Środowisko dla testów, które uruchamiają kod podprocesem (na przykład `python -m fabruna.…`).

    PYTHONPATH wskazuje katalog src/ tego samego drzewa, w którym leżą testy — także
    w piaskownicy testów mutacyjnych. Uwaga: mutanta zabija tylko test, który woła kod
    w tym samym procesie; test przez podproces nie podnosi wyniku mutacyjnego.
    """
    dotychczasowa = os.environ.get("PYTHONPATH")
    sciezka = str(KATALOG_SRC) if not dotychczasowa else str(KATALOG_SRC) + os.pathsep + dotychczasowa
    return {**os.environ, "PYTHONPATH": sciezka}


@pytest.fixture
def katalog_src() -> Path:
    """Katalog src/ dla testów statycznych, czyli takich, które czytają pliki źródłowe.

    W piaskownicy testów mutacyjnych pliki z src/ są przepisane przez mutmut (dochodzą
    funkcje pomocnicze i importy), więc test statyczny jest tam pomijany; mutanta i tak
    by nie zabił. W zwykłym przebiegu sędziego test działa normalnie.
    """
    if "MUTANT_UNDER_TEST" in os.environ:
        pytest.skip("test statyczny nie działa na kodzie przepisanym przez mutmut")
    return KATALOG_SRC
