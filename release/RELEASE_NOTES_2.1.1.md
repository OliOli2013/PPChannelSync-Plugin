# PP Channel Sync 2.1.1

Wydanie naprawcze dla użytkowników, u których synchronizacja była cofana mimo poprawnej lokalnej listy.

## Przyczyna

Wersja 2.1.0 kontrolowała po zapisie cały bukiet, łącznie z wpisami zastanymi. Niektóre listy i obrazy Enigma2 używają własnych technicznych referencji, np. `1:0:0:1E:0:0:0:0:0:0:`. Wtyczka ich nie tworzyła ani nie zmieniała, ale uznawała je za błąd i cofała operację.

## Poprawki

- istniejące niestandardowe wpisy są przepuszczane bez zmian;
- analiza kanałów nadal pomija wpisy, których nie można bezpiecznie powiązać z `lamedb`;
- kontrolowane są wyłącznie referencje nowe lub zmienione przez PP Channel Sync;
- niepoprawne dane wygenerowane przez wtyczkę nadal blokują zapis i uruchamiają rollback;
- `update.json` zawiera pola zgodne z aktualizatorami 1.x oraz 2.x;
- `postinst` usuwa stare pliki skompilowanego Pythona.

SHA256 IPK: `e38ab22f780cd0a9faaf71357ab6831e10f813be8086a3dfc85d0f61b9904388`
