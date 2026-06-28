# PP Channel Sync

**PP Channel Sync** to wtyczka dla **Enigma2 Python 3** do kontroli i bezpiecznej korekty posiadanej listy kanałów.

Autor: **by Paweł Pawełek**  
Kontakt: **aio-iptv@wp.pl**

## Główne możliwości

- kontrola posiadanej listy kanałów,
- korekta techniczna list SAT,
- pomijanie DVB-T / DVB-C,
- wybór źródła kontroli: **Standard / Alternatywne**,
- dopisywanie nowych kanałów do pasujących istniejących bukietów,
- zachowanie układu i kolejności listy użytkownika,
- kopia bezpieczeństwa przed zapisem,
- raport skrócony i szczegółowy,
- QR wsparcia projektu,
- aktywna aktualizacja wtyczki z GitHub przez `update.json`.

## Instalacja jednym poleceniem

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh | /bin/sh
```

Po instalacji wykonaj restart GUI.

## Instalacja ręczna

Pobierz plik IPK z katalogu `packages/`, skopiuj do `/tmp`, a następnie uruchom:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-ppchannelsync_1.0.17_all.ipk
```

## Aktualizacja z poziomu wtyczki

Od wersji **1.0.17** działa przycisk:

```text
Aktualizuj wtyczkę z GitHub
```

Wtyczka pobiera plik `update.json`, porównuje wersję, pobiera najnowszą paczkę IPK i instaluje aktualizację.

## Struktura repozytorium

```text
packages/   - gotowe paczki IPK
usr/        - pliki źródłowe wtyczki do Enigma2
assets/     - grafiki pomocnicze
update.json - manifest aktualizacji
installer.sh - instalator online
```

## Licencja

GNU General Public License v2.0.
