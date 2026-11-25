#!/bin/sh
# Oddaje gałąź usłudze sędziego na PC (konto `sedzia`). Jedyna droga gałęzi do GitHuba.
# SZKIC AI — do pracy autora.
#
# Użycie (w klonie repozytorium):  sh sedzia/pc/zglos.sh GAŁĄŹ [--czekaj]
# Wynik: /srv/sedzia/wyniki/<gałąź z „/” zamienionym na „_”>.txt
set -eu
galaz=${1:?podaj nazwę gałęzi, na przykład kod/0002-poprawki-rejestrow}
czekaj=${2:-}
kolejka=/srv/sedzia/kolejka
wynik="/srv/sedzia/wyniki/$(printf %s "$galaz" | tr / _).txt"

git rev-parse --verify -q "refs/heads/$galaz" >/dev/null || { echo "Brak lokalnej gałęzi $galaz" >&2; exit 2; }
[ -z "$(git status --porcelain)" ] || echo "Uwaga: zmiany niezatwierdzone NIE trafią do zgłoszenia." >&2
git fetch -q https://github.com/EdSkamor/fabruna-studio-NEW.git +refs/heads/main:refs/remotes/github/main

tymczasowy=$(mktemp -d)
trap 'rm -rf "$tymczasowy"' EXIT
id="$(date +%Y%m%d-%H%M%S)-$$"
git bundle create -q "$tymczasowy/$id.bundle" "refs/heads/$galaz" ^refs/remotes/github/main
chmod 644 "$tymczasowy/$id.bundle"
mv "$tymczasowy/$id.bundle" "$kolejka/$id.bundle"
echo "Zgłoszono $galaz jako $id. Wynik: $wynik"

[ "$czekaj" = "--czekaj" ] || exit 0
i=0
while [ $i -lt 2160 ]; do  # do 3 godzin
  if [ -f "$wynik" ] && grep -q "^zgłoszenie: $id\$" "$wynik"; then
    cat "$wynik"
    grep -q "^WYNIK: POZYTYWNY" "$wynik" && exit 0 || exit 1
  fi
  sleep 5; i=$((i + 1))
done
echo "Brak wyniku po 3 godzinach" >&2; exit 2
