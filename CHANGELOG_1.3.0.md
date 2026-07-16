# PP Channel Sync 1.3.0

Wydanie naprawcze przygotowane po powtarzających się zgłoszeniach komunikatu:

> W paczce kontrolnej nie znaleziono pliku lamedb.

Przyczyną było wymaganie pliku o dokładnej nazwie `lamedb`, mimo że część aktualnych paczek i obrazów Enigma2 używa `lamedb5` albo umieszcza bazę w zagnieżdżonym archiwum.

## Co zmieniono

- pełna obsługa `lamedb` i `lamedb5`,
- walidacja bazy przed wykonaniem korekty,
- obsługa zagnieżdżonych ZIP/TAR,
- lżejsze pobieranie GioppyGio,
- szczegółowa diagnostyka paczki,
- atomowa i sprawdzana kopia bezpieczeństwa,
- automatyczny rollback po błędzie zapisu,
- bezpieczne rozpakowywanie archiwów,
- kontrola SHA256 podczas aktualizacji.

## Instalacja

```sh
wget -q -O - https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/installer.sh | /bin/sh
```

Po instalacji wykonaj restart GUI Enigma2.
