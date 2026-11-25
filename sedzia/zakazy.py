"""Statyczne zakazy w kodzie gałęzi: konstrukcje, którymi kod pod testem mógłby podrobić wyrok.

Kod wykonawcy i testy działają w tym samym procesie co pytest, więc mogłyby zmienić raport
(na przykład `atexit` + `os._exit`), rozpoznać testy mutacyjne albo zarejestrować hooki pytest.
Sędzia odrzuca takie konstrukcje przed uruchomieniem czegokolwiek. To nie jest pełna piaskownica:
ostatnią bramką na obejścia, których reguły nie przewidziały, jest recenzja.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

# Moduły, których kod gałęzi nie importuje (dowolny podmoduł też).
MODULY_WSPOLNE = {
    "atexit", "ctypes", "importlib", "builtins", "gc", "inspect", "marshal", "pickle", "shelve", "socket", "ssl",
    "urllib", "http", "ftplib", "smtplib", "signal", "faulthandler", "code", "codeop", "runpy", "pty", "mmap",
    "_thread", "threading", "multiprocessing", "site", "sysconfig", "tracemalloc", "_pytest", "pluggy", "mutmut",
    "sedzia", "asyncio", "concurrent", "webbrowser", "xmlrpc", "zipimport", "pkgutil",
}
MODULY_SRC = MODULY_WSPOLNE | {"subprocess", "pytest", "shutil"}
# Wywołania wbudowanych funkcji, które pozwalają ukryć, co kod robi.
FUNKCJE = {"exec", "eval", "compile", "__import__", "globals", "vars", "locals", "breakpoint", "help", "input"}
FUNKCJE_ATRYBUTOWE = {"getattr", "setattr", "delattr", "hasattr"}  # dozwolone tylko ze stałą nazwą atrybutu
# Atrybuty dające dostęp do procesu, interpretera albo pytest.
ATRYBUTY_WSPOLNE = {
    "_exit", "_getframe", "argv", "orig_argv", "modules", "meta_path", "path_hooks", "environ", "environb", "getenv",
    "putenv", "unsetenv", "settrace", "setprofile", "addaudithook", "excepthook", "__dict__", "__globals__",
    "__code__", "__builtins__", "__subclasses__", "__bases__", "__mro__", "__loader__", "__spec__", "f_back",
    "f_locals", "f_globals", "f_builtins", "tb_frame", "gi_frame", "cr_frame", "system", "popen", "fork",
    "forkpty", "kill", "killpg", "abort", "execv", "execve", "execl", "execlp", "execvp", "execvpe", "spawnv",
    "spawnl", "posix_spawn", "register_at_fork", "stdout_fd", "dup2", "settrace_all_threads",
}
ATRYBUTY_TESTOW = ATRYBUTY_WSPOLNE | {"config", "pluginmanager", "hook", "stash", "_store", "session", "ihook"}
ZAKAZANE_NAPISY = re.compile(r"mutant|mutmut|junit|pytest_|xmlpath|sitecustomize|usercustomize|conftest", re.I)


def _modul_glowny(nazwa: str) -> str:
    return nazwa.split(".")[0]


def naruszenia_pliku(sciezka: str, tekst: str, rodzaj: str) -> list[str]:
    """Lista naruszeń w jednym pliku; `rodzaj` to „src” (kod wykonawcy) albo „testy” (testy zlecenia)."""
    try:
        drzewo = ast.parse(tekst, filename=sciezka)
    except (SyntaxError, ValueError) as blad:
        return [f"{sciezka}: nie da się sparsować ({blad})"]
    moduly = MODULY_SRC if rodzaj == "src" else MODULY_WSPOLNE
    atrybuty = ATRYBUTY_WSPOLNE if rodzaj == "src" else ATRYBUTY_TESTOW
    bledy: list[str] = []

    def zle(wezel: ast.AST, opis: str) -> None:
        bledy.append(f"{sciezka}:{getattr(wezel, 'lineno', 0)}: {opis}")

    for wezel in ast.walk(drzewo):
        if isinstance(wezel, ast.Import):
            for alias in wezel.names:
                if _modul_glowny(alias.name) in moduly:
                    zle(wezel, f"import {alias.name} — niedozwolony")
        elif isinstance(wezel, ast.ImportFrom):
            if wezel.level == 0 and wezel.module and _modul_glowny(wezel.module) in moduly:
                zle(wezel, f"from {wezel.module} import … — niedozwolony")
            for alias in wezel.names:
                if alias.name in atrybuty or alias.name in FUNKCJE or alias.name == "*":
                    zle(wezel, f"import nazwy {alias.name} — niedozwolony")
        elif isinstance(wezel, ast.Name):
            if wezel.id in FUNKCJE or wezel.id in ("__builtins__", "pytest_plugins"):
                zle(wezel, f"użycie {wezel.id} — niedozwolone")
        elif isinstance(wezel, ast.Attribute):
            if wezel.attr in atrybuty:
                zle(wezel, f"atrybut .{wezel.attr} — niedozwolony")
        elif isinstance(wezel, ast.Call) and isinstance(wezel.func, ast.Name) and wezel.func.id in FUNKCJE_ATRYBUTOWE:
            nazwa = wezel.args[1] if len(wezel.args) > 1 else None
            if not (isinstance(nazwa, ast.Constant) and isinstance(nazwa.value, str)):
                zle(wezel, f"{wezel.func.id} z nazwą atrybutu liczoną w locie — niedozwolone")
            elif nazwa.value in atrybuty:
                zle(wezel, f"{wezel.func.id}(…, {nazwa.value!r}) — niedozwolone")
        elif isinstance(wezel, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if wezel.name.startswith("pytest_"):
                zle(wezel, f"definicja {wezel.name} (hook pytest) — niedozwolona")
        elif isinstance(wezel, ast.Constant) and isinstance(wezel.value, str):
            if ZAKAZANE_NAPISY.search(wezel.value) and not _docstring(drzewo, wezel):
                zle(wezel, f"napis zawierający „{ZAKAZANE_NAPISY.search(wezel.value).group(0)}” — niedozwolony")
    return bledy


def _docstring(drzewo: ast.AST, stala: ast.Constant) -> bool:
    """Czy stała jest docstringiem (sam opis — nie trafia do kodu wykonywanego)."""
    for wezel in ast.walk(drzewo):
        if isinstance(wezel, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and wezel.body:
            pierwszy = wezel.body[0]
            if isinstance(pierwszy, ast.Expr) and pierwszy.value is stala:
                return True
    return False


def sprawdz(korzen: Path, sciezki: list[str], rodzaj: str) -> list[str]:
    bledy: list[str] = []
    for sciezka in sciezki:
        plik = korzen / sciezka
        if plik.is_symlink():
            bledy.append(f"{sciezka}: dowiązanie symboliczne — niedozwolone")
        elif plik.is_file() and sciezka.endswith(".py"):
            bledy += naruszenia_pliku(sciezka, plik.read_text("utf-8", errors="replace"), rodzaj)
    return bledy
