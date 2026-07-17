# PP Channel Sync 2.1.0

**PP Channel Sync** to wtyczka Enigma2 służąca do bezpiecznej korekty parametrów kanałów satelitarnych oraz dopisywania pewnych nowych kanałów do istniejących bukietów użytkownika.

Autor: **by Paweł Pawełek**  
Kontakt: **aio-iptv@wp.pl**

## Zasady działania

- wybór jednej, dwóch lub większej liczby pozycji orbitalnych;
- osobna analiza każdej zaznaczonej satelity;
- wykrywanie satelitów z bukietów, `lamedb`/`lamedb5` i konfiguracji głowic;
- korekta istniejących wpisów DVB-S/DVB-S2 bez zmiany ich kolejności;
- dopisywanie nowych kanałów wyłącznie na końcu pewnie dopasowanego, istniejącego bukietu;
- jeden czytelny blok `nowe kanały - PP Channel Sync` w każdym zmienionym bukiecie;
- brak automatycznego usuwania kanałów;
- zachowanie nazw oraz układu bukietów użytkownika;
- aktualizacja podpisu i daty na dole widoku bukietów;
- natywna obsługa `lamedb /4/` i `lamedb5 /5/`;
- pełna kopia bezpieczeństwa i automatyczny rollback po błędzie zapisu;
- zgodność z Enigma2 Python 2.7 oraz Python 3.

## Co zmieniono w 2.1.0

W 2.0.x silnik był zbyt mocno ograniczony i nie wykonywał dwóch funkcji znanych z wcześniejszych wydań. W 2.1.0 przywrócono je w bezpiecznej formie:

- nowe kanały są wykrywane na podstawie bukietów z bazy kontrolnej i dopisywane na dół odpowiadającego im bukietu;
- kanały z wcześniejszego bloku wtyczki są zachowywane i nie są dublowane przy kolejnej synchronizacji;
- jeżeli użytkownik przeniesie kanał z bloku do zwykłej części bukietu, wtyczka nie dopisze jego kopii;
- usuwane są stare podpisy twórcy listy zapisane jako markery, a na dole `bouquets.tv` pojawia się aktualna data i `@ PP Channel Sync`;
- obsługa wielu satelitów obejmuje także wykrywanie nowych kanałów osobno dla każdej pozycji.

## Instalacja

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh | /bin/sh
```

Po instalacji wykonaj restart GUI Enigma2.

## Raporty

- raport główny: `/tmp/ppchannelsync_report.txt`
- raport techniczny: `/tmp/ppchannelsync_details.txt`
- raport błędu: `/tmp/ppchannelsync_error.txt`
- diagnostyka: `/tmp/ppchannelsync_diagnostics.txt`
- paczka wsparcia: `/tmp/ppchannelsync_support.zip`
- kopie: `/etc/enigma2/ppchannelsync_backups/`
