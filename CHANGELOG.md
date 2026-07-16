# Changelog — PP Channel Sync

## 1.3.0 — 2026-07-16

### Najważniejsza poprawka
- Naprawiono błąd „W paczce kontrolnej nie znaleziono pliku lamedb”.
- Wtyczka obsługuje teraz oba formaty bazy Enigma2: `lamedb` oraz `lamedb5`.
- Jeżeli paczka zawiera kolejne archiwum ZIP/TAR, wtyczka przeszukuje również paczki zagnieżdżone.
- Niepoprawny lub pusty plik bazy jest odrzucany przed rozpoczęciem korekty.

### Bezpieczeństwo
- Kopia bezpieczeństwa jest tworzona atomowo i weryfikowana przed zapisem zmian.
- Kopia obejmuje `lamedb`, `lamedb5`, listy TV, listy radiowe i pliki główne bukietów.
- W razie błędu zapisu korekta jest automatycznie cofana z utworzonej kopii.
- Zachowywanych jest 10 najnowszych kopii, aby nie zapełniać pamięci tunera.
- Zablokowano niebezpieczne ścieżki w rozpakowywanych archiwach.
- Wprowadzono limit wielkości pobieranych paczek oraz wykrywanie stron błędu zamiast archiwum.
- Aktualizator wtyczki weryfikuje sumę SHA256 paczki IPK.
- Nie jest już kopiowana zawartość pomiędzy `lamedb` i `lamedb5`, ponieważ są to różne formaty.

### Źródła baz kontrolnych
- GioppyGio pobiera wyłącznie potrzebne pliki zamiast całego repozytorium.
- Dodano walidację plików pobranych przez GitHub API.
- Źródło Ciefp wybiera najnowszą pasującą paczkę przez GitHub API.
- Zaktualizowano awaryjną datę paczki Ciefp.

### Diagnostyka
- `/tmp/ppchannelsync_error.txt` zawiera teraz źródło, URL/API, listę znalezionych plików, odrzucone bazy i dokładną przyczynę zatrzymania.
- Raport podaje użyty format bazy oraz liczbę usług i transponderów w paczce kontrolnej.
- Błąd zapisu pojedynczego bukietu nie jest już ignorowany.

### Zasady działania pozostają bez zmian
- brak automatycznego usuwania poprawnych kanałów użytkownika,
- brak zmiany kolejności istniejących kanałów,
- ochrona lokalnego EPG i wpisów `lamedb`,
- ochrona DVB-T, DVB-C, IPTV i strumieni,
- brak zmian ustawień głowicy, sieci, skina i rozdzielczości.
