# PP Channel Sync 1.3.0

**PP Channel Sync** to wtyczka Enigma2 dla Python 2 i Python 3, która porównuje istniejącą listę kanałów z aktualną bazą kontrolną i wykonuje wyłącznie bezpieczne korekty techniczne.

Autor: **by Paweł Pawełek**  
Kontakt: **aio-iptv@wp.pl**

## Co robi wtyczka

- sprawdza kanały w istniejących bukietach,
- koryguje wyłącznie pewne parametry techniczne,
- zachowuje lokalny `lamedb` i wpisy istotne dla EPG oraz piconów,
- może dopisać nowe kanały zgodnie z ustawieniem użytkownika,
- tworzy raport przed lub po korekcie,
- wykonuje kopię bezpieczeństwa przed każdym zapisem,
- chroni listy DVB-T, DVB-C, IPTV i strumienie.

## Najważniejsze zasady bezpieczeństwa

- Nie usuwa automatycznie poprawnych kanałów użytkownika.
- Nie zmienia kolejności istniejących kanałów w bukietach.
- Nie wgrywa całych obcych bukietów w miejsce listy użytkownika.
- Nie zmienia konfiguracji głowicy, sieci, skina ani rozdzielczości.
- W razie błędu zapisu automatycznie przywraca kopię wykonaną przed korektą.

## Nowości w wersji 1.3.0

Wersja 1.3.0 usuwa powtarzający się błąd „W paczce kontrolnej nie znaleziono pliku lamedb”. Wtyczka:

- rozpoznaje `lamedb` i `lamedb5`,
- sprawdza, czy baza rzeczywiście zawiera usługi i transpondery,
- przeszukuje zagnieżdżone archiwa,
- pobiera z GioppyGio tylko potrzebne pliki,
- zapisuje pełną diagnostykę do `/tmp/ppchannelsync_error.txt`,
- weryfikuje kopię bezpieczeństwa i automatycznie cofa nieudaną operację,
- weryfikuje SHA256 aktualizacji IPK.

Pełna lista zmian znajduje się w [CHANGELOG.md](CHANGELOG.md).

## Instalacja on-line

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh | /bin/sh
```

Następnie wykonaj restart GUI.

## Instalacja z pliku IPK

Skopiuj plik z katalogu `packages` do `/tmp`, a następnie wykonaj:

```sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-ppchannelsync_1.3.0_all.ipk
```

## Aktualizacja z poziomu wtyczki

W menu PP Channel Sync wybierz **Aktualizuj wtyczkę z GitHub**. Aktualizator odczytuje `update.json`, pobiera paczkę IPK i sprawdza jej sumę SHA256 przed instalacją.

## Pliki diagnostyczne

- `/tmp/ppchannelsync_error.txt` — szczegóły błędu paczki lub pobierania,
- `/tmp/ppchannelsync_report.txt` — raport skrócony,
- `/tmp/ppchannelsync_details.txt` — raport szczegółowy,
- `/tmp/ppchannelsync_update_info.txt` — log aktualizacji,
- `/etc/enigma2/ppchannelsync_backups/` — kopie bezpieczeństwa.

## Zgodność

- Enigma2,
- Python 2.7 i Python 3,
- obrazy korzystające z `lamedb /4/` oraz `lamedb /5/`,
- architektura pakietu: `all`.

## Testy przed publikacją

Kod został sprawdzony przez kompilację Python 3 i testy regresyjne poza tunerem obejmujące:

- wykrycie paczki zawierającej wyłącznie `lamedb5`,
- odrzucenie uszkodzonego `lamedb` i wybór poprawnego `lamedb5`,
- zagnieżdżony ZIP,
- ochronę przed zapisem poza katalogiem rozpakowania,
- kompletność kopii TV/radio,
- automatyczny rollback po symulowanym błędzie zapisu,
- brak kopiowania danych pomiędzy formatami `lamedb` i `lamedb5`.

Przed szeroką publikacją zalecany jest krótki test na jednym tunerze Python 2 i jednym tunerze Python 3.

## Licencja

GPL-2.0.
