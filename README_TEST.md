# Test PP Channel Sync 2.1.0

1. Zainstaluj IPK ręcznie i wykonaj restart GUI.
2. Żółtym przyciskiem zaznacz co najmniej dwie używane satelity.
3. Ustaw `Raport bez zapisu` i uruchom synchronizację.
4. Sprawdź, czy raport pokazuje osobny wynik oraz liczbę nowych kanałów dla każdej pozycji.
5. Ustaw `Bezpieczna korekta` i uruchom ponownie.
6. Otwórz bukiety, które mają odpowiedniki w bazie kontrolnej.
7. Nowe kanały powinny znajdować się na samym dole pod markerem `nowe kanały - PP Channel Sync`.
8. Na dole widoku listy bukietów powinny być aktualna data i wpis `@ PP Channel Sync`.
9. Uruchom korektę drugi raz. Kanały i markery nie mogą się zdublować.
10. W razie problemu utwórz `Przygotuj raport do wysłania` i pobierz `/tmp/ppchannelsync_support.zip`.
