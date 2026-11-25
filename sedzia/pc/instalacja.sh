#!/bin/bash
# Instalacja usługi sędziego na PC. Uruchamia właściciel przez sudo; nigdy sesja AI.
# SZKIC AI — do pracy autora.
#
# Pliki usługi pobiera z GitHuba z podanego commitu `main` — nie z lokalnego klonu,
# do którego mają dostęp sesje AI.
#
# Użycie:  sudo bash instalacja.sh <pełny skrót commitu main>
set -euo pipefail
sha=${1:?podaj pełny skrót commitu main (40 znaków)}
[[ $sha =~ ^[0-9a-f]{40}$ ]] || { echo "To nie jest pełny skrót commitu" >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo "Uruchom przez sudo" >&2; exit 2; }
wlasciciel=${SUDO_USER:?uruchom przez sudo z konta właściciela}
zrodlo="https://raw.githubusercontent.com/EdSkamor/fabruna-studio-NEW/$sha/sedzia/pc"
pliki=(kolejka.py fabruna-sedzia.service fabruna-sedzia.path fabruna-sedzia.timer)

tymczasowy=$(mktemp -d)
trap 'rm -rf "$tymczasowy"' EXIT
for plik in "${pliki[@]}"; do
  curl -fsSL "$zrodlo/$plik" -o "$tymczasowy/$plik"
done
python3 -I -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$tymczasowy/kolejka.py"

echo "1/6 Konto systemowe sedzia"
id sedzia >/dev/null 2>&1 || useradd --system --user-group --create-home --home-dir /home/sedzia --shell /usr/sbin/nologin sedzia
chmod 700 /home/sedzia

echo "2/6 Katalogi /srv/sedzia (kolejka: zapis dla $wlasciciel, bez odczytu cudzych zgłoszeń)"
install -d -o root -g root -m 755 /srv/sedzia
install -d -o sedzia -g "$wlasciciel" -m 1730 /srv/sedzia/kolejka
install -d -o sedzia -g sedzia -m 755 /srv/sedzia/wyniki /srv/sedzia/stan /srv/sedzia/venv

echo "3/6 Środowisko Pythona sędziego (zależności doinstaluje usługa z main:pyproject.toml)"
[[ -x /srv/sedzia/venv/bin/python ]] || sudo -u sedzia python3 -m venv /srv/sedzia/venv

echo "4/6 Pliki usługi"
install -d -o root -g root -m 755 /usr/local/lib/fabruna-sedzia
install -o root -g root -m 644 "$tymczasowy/kolejka.py" /usr/local/lib/fabruna-sedzia/kolejka.py
for jednostka in fabruna-sedzia.service fabruna-sedzia.path fabruna-sedzia.timer; do
  install -o root -g root -m 644 "$tymczasowy/$jednostka" "/etc/systemd/system/$jednostka"
done
echo "$sha" > /usr/local/lib/fabruna-sedzia/WERSJA

echo "5/6 Token GitHuba (widzi go tylko konto sedzia)"
install -d -o sedzia -g sedzia -m 700 /home/sedzia/.config /home/sedzia/.config/fabruna
if [[ ! -s /home/sedzia/.config/fabruna/token || ${NOWY_TOKEN:-} == 1 ]]; then
  read -rsp "Wklej token (fine-grained, tylko repozytorium fabruna-studio-NEW) i naciśnij Enter: " token; echo
  [[ -n $token ]] || { echo "Pusty token" >&2; exit 2; }
  printf '%s' "$token" | install -o sedzia -g sedzia -m 600 /dev/stdin /home/sedzia/.config/fabruna/token
  unset token
fi
sudo -u sedzia python3 -I - <<'PY'
import json, urllib.request
token = open("/home/sedzia/.config/fabruna/token").read().strip()
z = urllib.request.Request("https://api.github.com/repos/EdSkamor/fabruna-studio-NEW",
                           headers={"Authorization": f"Bearer {token}", "User-Agent": "fabruna-sedzia"})
uprawnienia = json.load(urllib.request.urlopen(z, timeout=30)).get("permissions", {})
print("   token działa; zapis do repozytorium:", "tak" if uprawnienia.get("push") else "NIE")
PY

echo "6/6 Piaskownica i uruchomienie"
sudo -u sedzia bwrap --unshare-all --die-with-parent --ro-bind / / --dev /dev --proc /proc --tmpfs /home /bin/true \
  && echo "   piaskownica bwrap działa na koncie sedzia"
systemctl daemon-reload
systemctl enable --now fabruna-sedzia.path fabruna-sedzia.timer
systemctl --no-pager --lines=0 status fabruna-sedzia.path | head -3
echo "Gotowe. Wersja usługi: $sha"
