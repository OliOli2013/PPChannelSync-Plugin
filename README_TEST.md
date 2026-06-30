# Test PP Channel Sync 1.2.1

Instalacja testowa:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-ppchannelsync_1.2.1_all.ipk
init 4
sleep 2
init 3
```

Po wejściu do wtyczki sprawdź najpierw:

1. Źródło kontroli: Standard
2. Pakiet kontrolny: Hot Bird 13E albo Dual Feed
3. Tryb: Raport bez zapisu
4. Zielony przycisk

Dopiero potem przełącz źródło kontroli na GioppyGio i uruchom Raport bez zapisu.

Wersja 1.2.1 nie pobiera całego repozytorium GioppyGio. Pobiera tylko pliki z wybranego katalogu przez GitHub Contents API.
