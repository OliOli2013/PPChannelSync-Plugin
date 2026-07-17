# PP Channel Sync 2.1.0

Wydanie przywraca dwie funkcje, których brakowało w gałęzi 2.0.x: dopisywanie nowych kanałów na końcu właściwych bukietów oraz aktualizację podpisu i daty w widoku listy bukietów.

## Najważniejsze zmiany

- pobieranie bukietów kontrolnych razem z `lamedb`/`lamedb5`;
- dopasowanie lokalnych i kontrolnych bukietów po nazwie oraz wspólnych kanałach;
- obsługa nowych kanałów osobno dla każdej zaznaczonej satelity;
- jeden blok `nowe kanały - PP Channel Sync` z markerem końcowym;
- brak duplikatów po kolejnym uruchomieniu;
- zachowanie kanałów dopisanych wcześniej przez wtyczkę;
- aktualna data i `@ PP Channel Sync` na dole `bouquets.tv`;
- brak automatycznego usuwania zwykłych kanałów;
- kopia i rollback przed każdym zapisem.
