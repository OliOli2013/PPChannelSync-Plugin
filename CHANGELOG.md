# Changelog

## 2.1.1

- naprawiono błąd występujący tylko na części list i obrazów Enigma2;
- lokalne, niestandardowe referencje techniczne są traktowane jako dane zastane i pozostają nietknięte;
- walidator kontroluje wyłącznie referencje wygenerowane lub zmienione przez wtyczkę;
- dodano test regresyjny dla wpisu `1:0:0:1E:0:0:0:0:0:0:`;
- przygotowano wstecznie zgodny `update.json` dla aktualizatorów 1.x i 2.x;
- instalator oraz `postinst` czyszczą skompilowany kod poprzednich wersji.

## 2.1.0

- przywrócono dopisywanie nowych kanałów na końcu pasujących, istniejących bukietów;
- źródło kontrolne pobiera teraz również bukiety TV, a nie tylko `lamedb`/`lamedb5`;
- dodano ostrożne dopasowanie bukietu po nazwie i wspólnych kanałach;
- nowe kanały są filtrowane osobno dla każdej zaznaczonej satelity;
- dodano jeden kontrolowany blok `nowe kanały - PP Channel Sync` z markerem końcowym;
- kolejne uruchomienie nie dubluje kanałów ani separatorów;
- zachowywane są kanały dopisane przez wcześniejsze wykonanie wtyczki;
- kanał ręcznie przeniesiony z bloku do właściwej części bukietu nie jest ponownie dopisywany;
- każdy nowy kanał otrzymuje wcześniej zweryfikowany wpis w lokalnym `lamedb`/`lamedb5`;
- przywrócono aktualizację daty i podpisu `@ PP Channel Sync` na dole listy bukietów;
- stary podpis twórcy listy jest usuwany wyłącznie wtedy, gdy jest markerem informacyjnym, a nie prawdziwym wpisem bukietu;
- raport pokazuje liczbę dopisanych kanałów oraz wynik osobno dla każdej satelity;
- zachowano kopię bezpieczeństwa i automatyczny rollback.

## 2.0.1

- naprawiono GSOD po anulowaniu ekranu wyboru satelitów;
- poprawiono wykrywanie wielu pozycji orbitalnych;
- przywrócono czytelny interfejs i funkcje diagnostyczne.

## 2.0.0

- nowy wielosatelitarny silnik synchronizacji;
- natywna obsługa `lamedb /4/` oraz `lamedb5 /5/`.
