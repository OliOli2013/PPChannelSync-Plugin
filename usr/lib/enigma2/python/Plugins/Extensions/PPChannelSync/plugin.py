# -*- coding: utf-8 -*-
# PP Channel Sync for Enigma2 Python 2/3
# Author: by Paweł Pawełek

from __future__ import print_function, unicode_literals

import os
import re
import time
import shutil
import tarfile
import zipfile
import tempfile
import json
import traceback
import hashlib
import subprocess
from collections import OrderedDict

try:
    from urllib.request import Request, urlopen
except Exception:
    try:
        from urllib2 import Request, urlopen
    except Exception:
        Request = None
        urlopen = None

try:
    from urllib.parse import quote as url_quote
except Exception:
    try:
        from urllib import quote as url_quote
    except Exception:
        url_quote = None

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

PLUGIN_VERSION = "1.2.1"
PLUGIN_NAME = "PP Channel Sync"
AUTHOR = "by Paweł Pawełek"
CONTACT = "aio-iptv@wp.pl"
SUPPORT_TEXT = "Wesprzyj twórczość, pomóż rozwijać lokalne projekty"
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync"
E2_PATH = "/etc/enigma2"
BACKUP_DIR = "/etc/enigma2/ppchannelsync_backups"
WORK_DIR = "/tmp/ppchannelsync"
REPORT_PATH = "/tmp/ppchannelsync_report.txt"
DETAIL_REPORT_PATH = "/tmp/ppchannelsync_details.txt"
ERROR_PATH = "/tmp/ppchannelsync_error.txt"
AUTO_SUMMARY_PATH = "/tmp/ppchannelsync_auto_summary.txt"
USER_REPORT_PATH = "/tmp/ppchannelsync_user_report.txt"
DIAGNOSTIC_PATH = "/tmp/ppchannelsync_diagnostics.txt"
SUPPORT_ZIP_PATH = "/tmp/ppchannelsync_support_report.zip"
HISTORY_PATH = "/etc/enigma2/ppchannelsync_history.log"
CONFIG_PATH = "/etc/enigma2/ppchannelsync.conf"
STATE_PATH = "/etc/enigma2/ppchannelsync_state.conf"
UPDATE_INFO_PATH = "/tmp/ppchannelsync_update_info.txt"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/update.json"
MANAGED_PREFIX = "ppcs_"

SOURCE_STANDARD = 0
SOURCE_ALTERNATIVE = 1
SOURCE_GIOPPYGIO = 2
SOURCE_OPTIONS = [
    ("Standard", "Podstawowe źródło kontroli. Dobre jako pierwszy wybór dla większości list."),
    ("Alternatywne", "Drugie źródło kontroli oparte o paczki Ciefp z GitHub. Przydatne, gdy standardowe źródło gorzej dopasowuje Twoją listę."),
    ("GioppyGio", "Trzecie źródło kontroli z OpenVisionE2/GioppyGio-settings. Pobiera tylko wybrany katalog, bez całego repozytorium."),
]

STANDARD_PACKAGES = [
    ("Hot Bird 13E", "https://www.vhannibal.net/download_setting.php?id=1&action=download"),
    ("Dual Feed 13E + 19.2E", "https://www.vhannibal.net/download_setting.php?id=2&action=download"),
    ("Motor 70E - 45W", "https://www.vhannibal.net/download_setting.php?id=3&action=download"),
    ("Quadri 9E + 13E + 16E + 19E + 23E + 28E", "https://www.vhannibal.net/download_setting.php?id=4&action=download"),
    ("Quadri 13E + 19E + 23E + 28E", "https://www.vhannibal.net/download_setting.php?id=5&action=download"),
    ("Quadri 7E + 13E + 19E + 42E", "https://www.vhannibal.net/download_setting.php?id=6&action=download"),
    ("Quadri 13E + 19E + 5E + 1W", "https://www.vhannibal.net/download_setting.php?id=7&action=download"),
    ("Quadri 13E + 19E + 9E + 5W", "https://www.vhannibal.net/download_setting.php?id=8&action=download"),
    ("Trial 13E + 19E + 30W", "https://www.vhannibal.net/download_setting.php?id=9&action=download"),
    ("Trial 13E + 19E + 5W", "https://www.vhannibal.net/download_setting.php?id=10&action=download"),
]

# Alternatywne źródło korzysta z repo ciefp/ciefpsettings-enigma2-zipped.
# Wtyczka wyszukuje najnowszy plik ZIP po prefiksie, więc nie trzeba zmieniać
# kodu przy każdej nowej dacie paczki.
CIEFP_API_URL = "https://api.github.com/repos/ciefp/ciefpsettings-enigma2-zipped/contents/"
CIEFP_RAW_BASE = "https://raw.githubusercontent.com/ciefp/ciefpsettings-enigma2-zipped/master/"
CIEFP_FALLBACK_DATE = "27.06.2026"
ALTERNATIVE_PACKAGES = [
    ("Hot Bird 13E", "ciefp-E2-2satA-19E-13E-"),
    ("Dual Feed 13E + 19.2E", "ciefp-E2-2satA-19E-13E-"),
    ("Motor 75E - 34W", "ciefp-E2-75E-34W-"),
    ("Multi 39E + 28E + 23E + 19E + 16E + 13E + 9E + 4.8E + 1.9E + 0.8W", "ciefp-E2-10sat-39E-28E-23E-19E-16E-13E-9E-4.8E-1.9E-0.8W-"),
    ("Multi 28E + 23E + 19E + 16E + 13E + 4.8E + 1.9E + 0.8W", "ciefp-E2-8sat-28E-23E-19E-16E-13E-4.8E-1.9E-0.8W-"),
    ("Multi 42E + 39E + 28E + 23E + 19E + 16E + 13E + 9E + 7E + 4.8E + 1.9E + 0.8W + 5W", "ciefp-E2-13sat-42E-39E-28E-23E-19E-16E-13E-9E-7E-4.8E-1.9E-0.8w-5w-"),
    ("Multi 19E + 16E + 13E + 1.9E + 0.8W", "ciefp-E2-5sat-19E-16E-13E-1.9E-0.8W-"),
    ("Multi 28E + 23E + 19E + 16E + 13E + 9E + 1.9E + 0.8W + 5W", "ciefp-E2-9sat-28E-23E-19E-16E-13E-9E-1.9E-0.8W-5W-"),
    ("Trial 28E + 19E + 13E + 30W", "ciefp-E2-4satA-28E-19E-13E-30W-"),
    ("Multi 19E + 16E + 13E", "ciefp-E2-3satB-19E-16E-13E-"),
]

# GioppyGio/OpenVisionE2.
# Uwaga: nie pobieramy całego master.zip, bo na tunerach Enigma2 może to blokować GUI.
# Pobierane są tylko pliki z wybranego katalogu: lamedb, bouquets i userbouquet.*.
GIOPPYGIO_API_BASE = "https://api.github.com/repos/OpenVisionE2/GioppyGio-settings/contents/"
GIOPPYGIO_RAW_BASE = "https://raw.githubusercontent.com/OpenVisionE2/GioppyGio-settings/master/"
GIOPPYGIO_PACKAGES = [
    ("Mono 13E", "GioppyGio_E2_Mono_13E"),
    ("Dual 13E + 16E", "GioppyGio_E2_Dual_13E+16E"),
    ("Dual 13E + 19E", "GioppyGio_E2_Dual_13E+19E"),
    ("Dual 5W + 13E", "GioppyGio_E2_Dual_5W+13E"),
    ("Dual 9E + 13E", "GioppyGio_E2_Dual_9E+13E"),
    ("Trial 13E + 16E + 19E", "GioppyGio_E2_Trial_13E+16E+19E"),
    ("Trial 13E + 19E + 28E", "GioppyGio_E2_Trial_13E+19E+28E"),
    ("Trial 13E + 19E + 30W", "GioppyGio_E2_Trial_13E+19E+30W"),
    ("Trial 5W + 13E + 19E", "GioppyGio_E2_Trial_5W+13E+19E"),
    ("Trial 9E + 13E + 19E", "GioppyGio_E2_Trial_9E+13E+19E"),
    ("Quadri 13E + 16E + 19E + 30W", "GioppyGio_E2_Quadri_13E+16E+19E+30W"),
    ("Quadri 13E + 19E + 23E + 28E", "GioppyGio_E2_Quadri_13E+19E+23E+28E"),
    ("Quadri 13E + 19E + 9E + 5W", "GioppyGio_E2_Quadri_13E+19E+9E+5W"),
    ("Quadri 9E + 13E + 16E + 19E", "GioppyGio_E2_Quadri_9E+13E+16E+19E"),
    ("Motor 75E - 45W", "GioppyGio_E2_Motor_75E-45W"),
]

# Zgodność z wcześniejszymi funkcjami.
ONLINE_PACKAGES = STANDARD_PACKAGES

def packages_for_source(source_index):
    try:
        source_index = int(source_index or 0)
    except Exception:
        source_index = SOURCE_STANDARD
    if source_index == SOURCE_ALTERNATIVE:
        return ALTERNATIVE_PACKAGES
    if source_index == SOURCE_GIOPPYGIO:
        return GIOPPYGIO_PACKAGES
    return STANDARD_PACKAGES

def clamp_package_index(source_index, package_index):
    packages = packages_for_source(source_index)
    if not packages:
        return 0
    try:
        idx = int(package_index)
    except Exception:
        idx = 0
    if idx < 0 or idx >= len(packages):
        idx = 0
    return idx

MODE_REPORT = 0
MODE_CORRECT = 1
SYNC_MODES = [
    ("Raport bez zapisu", "Tylko sprawdza Twoją listę i zapisuje raport. Nic nie zmienia w tunerze."),
    ("Bezpieczna korekta techniczna", "Aktualizuje lamedb bazą kontrolną z ochroną lokalnych wpisów, poprawia tylko pewne reference i zachowuje kolejność kanałów w bukietach."),
]

ADD_NEW_MODES = [
    ("Nie", "Nie dopisuje nowych kanałów; wykonuje tylko kontrolę i bezpieczne korekty."),
    ("Tak - na koniec pasujących bukietów", "Dopisuje nowe kanały tylko na końcu pasujących, już istniejących bukietów. Nie zmienia kolejności obecnych kanałów i nie tworzy nowych bukietów."),
    ("Tak - osobny bukiet Nowe kanały", "Dopisuje nowe kanały do osobnego bukietu PP Channel Sync - Nowe kanały. Dzięki temu łatwo je później ręcznie przenieść lub usunąć."),
]

REMOVE_OFF = 0
REMOVE_REPORT = 1
REMOVE_DELETE = 2
REMOVE_MODES = [
    ("Nie", "Nie usuwa kanałów z Twoich bukietów. Kanały niepewne zostają tylko w raporcie."),
    ("Tylko raport", "Wykrywa kanały, których nie ma w bazie kontrolnej, ale nie usuwa ich z listy."),
    ("Tylko raport", "Wtyczka nie usuwa istniejących kanałów. Niepewne pozycje trafiają tylko do raportu."),
]

MATCH_SAFE = 0
MATCH_EXACT = 1
MATCH_MODERATE = 2
MATCH_MODES = [
    ("Tylko ten sam service reference", "Najbezpieczniej: nie zmienia referencji w bukietach, a brakujące wpisy lamedb dopisuje tylko dla tego samego SID/TSID/ONID/namespace."),
    ("Dokładna nazwa kanału", "Poprawia także reference w bukietach, ale tylko gdy nazwa kanału pasuje dokładnie i jednoznacznie."),
    ("Dokładna + bezpieczne warianty HD", "Dodatkowo uwzględnia ostrożne różnice typu HD/SD/UHD, gdy nie ma ryzyka pomyłki."),
]

SKIP_SERVICE_TYPES = set(["64", "7", "134", "832"])

AUTO_UPDATE_MODES = [
    ("Wyłączona", "Automatyczna aktualizacja jest wyłączona."),
    ("Raz w tygodniu", "Wtyczka raz w tygodniu sama pobiera bazę kontrolną, wykonuje korektę i pokazuje krótkie podsumowanie."),
    ("Po wykryciu nowej bazy", "Wtyczka okresowo sprawdza, czy baza kontrolna zmieniła się od ostatniego sprawdzenia. Jeśli tak, wykonuje korektę i pokazuje podsumowanie."),
]

AUTO_OFF = 0
AUTO_WEEKLY = 1
AUTO_ON_NEW_BASE = 2
AUTO_INTERVAL_SECONDS = 24 * 60 * 60
WEEK_SECONDS = 7 * 24 * 60 * 60



def _system_lang():
    lang = "pl"
    try:
        from Components.config import config
        lang = str(config.osd.language.value or "pl")
    except Exception:
        try:
            st = read_text("/etc/enigma2/settings")
            for line in st.splitlines():
                if line.startswith("config.osd.language="):
                    lang = line.split("=", 1)[1].strip()
                    break
        except Exception:
            pass
    return "pl" if str(lang).lower().startswith("pl") else "en"

_LANG = _system_lang()

_TR_EN = {
    "Standard": "Standard",
    "Alternatywne": "Alternative",
    "Podstawowe źródło kontroli. Dobre jako pierwszy wybór dla większości list.": "Primary control source. Recommended as the first choice for most lists.",
    "Drugie źródło kontroli oparte o paczki Ciefp z GitHub. Przydatne, gdy standardowe źródło gorzej dopasowuje Twoją listę.": "Alternative control source based on Ciefp packages from GitHub. Useful when the standard source does not match your list well.",
    "GioppyGio": "GioppyGio",
    "Trzecie źródło kontroli z OpenVisionE2/GioppyGio-settings. Pobiera tylko wybrany katalog, bez całego repozytorium.": "Third control source from OpenVisionE2/GioppyGio-settings. It downloads only the selected folder, not the whole repository.",
    "Raport bez zapisu": "Report only",
    "Tylko sprawdza Twoją listę i zapisuje raport. Nic nie zmienia w tunerze.": "Checks your list and saves a report. Nothing is changed on the receiver.",
    "Bezpieczna korekta techniczna": "Safe technical correction",
    "Aktualizuje lamedb bazą kontrolną z ochroną lokalnych wpisów, poprawia tylko pewne reference i zachowuje kolejność kanałów w bukietach.": "Updates lamedb using the control base while protecting local entries. Only safe references are corrected and bouquet order is kept.",
    "Nie": "No",
    "Nie dopisuje nowych kanałów; wykonuje tylko kontrolę i bezpieczne korekty.": "Does not add new channels; only checks and performs safe corrections.",
    "Tak - na koniec pasujących bukietów": "Yes - at the end of matching bouquets",
    "Dopisuje nowe kanały tylko na końcu pasujących, już istniejących bukietów. Nie zmienia kolejności obecnych kanałów i nie tworzy nowych bukietów.": "Adds new channels only at the end of matching existing bouquets. Existing channel order is not changed and no new bouquets are created.",
    "Tylko raport": "Report only",
    "Nie usuwa kanałów z Twoich bukietów. Kanały niepewne zostają tylko w raporcie.": "Does not remove channels from your bouquets. Uncertain channels are reported only.",
    "Wykrywa kanały, których nie ma w bazie kontrolnej, ale nie usuwa ich z listy.": "Detects channels missing from the control base but does not remove them.",
    "Usuń pewne": "Remove confirmed",
    "Usuwa wyłącznie pozycje jednoznacznie oznaczone jako nieaktualne w pasującym bukiecie. Używać ostrożnie.": "Removes only entries clearly detected as outdated in a matching bouquet. Use carefully.",
    "Wyłączona": "Disabled",
    "Automatyczna aktualizacja jest wyłączona.": "Automatic update is disabled.",
    "Raz w tygodniu": "Once a week",
    "Wtyczka raz w tygodniu sama pobiera bazę kontrolną, wykonuje korektę i pokazuje krótkie podsumowanie.": "Once a week the plugin downloads the control base, performs the correction and shows a short summary.",
    "Po wykryciu nowej bazy": "When a new base is detected",
    "Wtyczka okresowo sprawdza, czy baza kontrolna zmieniła się od ostatniego sprawdzenia. Jeśli tak, wykonuje korektę i pokazuje podsumowanie.": "The plugin periodically checks whether the control base has changed. If yes, it performs the correction and shows a summary.",
    "Standard / Alternatywne przełączasz OK albo Lewo/Prawo.": "Switch Standard / Alternative with OK or Left/Right.",
    "Źródło kontroli": "Control source",
    "Pakiet kontrolny": "Control package",
    "Tryb pracy zielonego": "Green button mode",
    "Dopisywanie nowych kanałów": "Add new channels",
    "Usuwanie nieaktualnych kanałów": "Remove outdated channels",
    "Automatyczna aktualizacja": "Automatic update",
    "Utwórz kopię bezpieczeństwa teraz": "Create backup now",
    "Przywróć ostatnią kopię bezpieczeństwa": "Restore last backup",
    "Pokaż ostatni raport": "Show last report",
    "Pokaż szczegółowy raport zmian": "Show detailed change report",
    "Aktualizuj wtyczkę z GitHub": "Update plugin from GitHub",
    "Informacje o działaniu wtyczki": "Plugin information",
    "Informacje": "Information",
    "Opis opcji": "Option description",
    "Wesprzyj": "Support",
    "Pomóż rozwijać\nlokalne projekty": "Help develop\nlocal projects",
    "OK wykonuje funkcję z listy, a zielony przycisk uruchamia ustawione zadanie korekty listy": "OK runs the selected list function; the green button starts the configured list correction task",
    "OK - opcja / funkcja  |  Zielony - korekta listy  |  MENU - raport  |  EXIT - wyjście": "OK - option / function  |  Green - list correction  |  MENU - report  |  EXIT - close",
    "Czerwony: wyjście": "Red: exit",
    "Zielony: korekta listy": "Green: correct list",
    "Żółty: kopia": "Yellow: backup",
    "Niebieski: przywróć": "Blue: restore",
    "Wybierz zakres kontroli zgodny z listą, którą masz na tunerze.\n\nPakiet służy tylko jako punkt porównania.": "Choose a control range matching the list on your receiver.\n\nThe package is only used as a comparison point.",
    "Zielony przycisk uruchamia tylko ustawione zadanie korekty listy. Funkcje z menu uruchamiasz przyciskiem OK.": "The green button starts only the configured channel list correction task. Menu functions are run with OK.",
    "Tworzy kopię lamedb, lamedb5, bouquets.tv i wszystkich userbouquet.*.tv.": "Creates a backup of lamedb, lamedb5, bouquets.tv and all userbouquet.*.tv files.",
    "Przywraca ostatnią kopię wykonaną przez PP Channel Sync.": "Restores the last backup created by PP Channel Sync.",
    "Pokazuje ostatni raport skrócony. MENU działa tak samo z każdego miejsca ekranu.": "Shows the last short report. MENU works the same from anywhere on this screen.",
    "Pokazuje szczegółowy raport: dodane, usunięte, poprawione i pominięte kanały.": "Shows the detailed report: added, removed, corrected and skipped channels.",
    "Sprawdza update.json na GitHub, porównuje wersję, pobiera najnowszy plik IPK i instaluje aktualizację.": "Checks update.json on GitHub, compares versions, downloads the newest IPK and installs the update.",
    "Autor: by Paweł Pawełek\nKontakt: aio-iptv@wp.pl\n\nDVB-T/DVB-C jest pomijane. Wtyczka nie zmienia głowicy, sieci, skina ani rozdzielczości.": "Author: by Paweł Pawełek\nContact: aio-iptv@wp.pl\n\nDVB-T/DVB-C is skipped. The plugin does not change tuner, network, skin or resolution settings.",
    "Wesprzyj twórczość, pomóż rozwijać lokalne projekty": "Support creativity, help develop local projects",
}

def _(txt):
    try:
        if _LANG == "en":
            return _TR_EN.get(txt, txt)
    except Exception:
        pass
    return txt


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def read_text(path):
    with open(path, "rb") as f:
        data = f.read()
    for enc in ("utf-8", "latin-1", "cp1250"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", "ignore")


def write_text(path, text):
    tmp = path + ".ppcs.tmp"
    with open(tmp, "wb") as f:
        f.write(text.encode("utf-8", "ignore"))
    os.rename(tmp, path)

def read_kv(path):
    data = {}
    if not os.path.isfile(path):
        return data
    try:
        for line in read_text(path).splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    except Exception:
        pass
    return data


def write_kv(path, data):
    lines = []
    for key in sorted(data.keys()):
        lines.append("%s=%s" % (key, data[key]))
    write_text(path, "\n".join(lines) + "\n")


def load_settings():
    cfg = read_kv(CONFIG_PATH)
    def as_int(name, default, max_value=None):
        try:
            value = int(cfg.get(name, default))
        except Exception:
            value = default
        if value < 0:
            value = default
        if max_value is not None and value > max_value:
            value = default
        return value
    source_index = as_int("source_index", SOURCE_STANDARD, len(SOURCE_OPTIONS) - 1)
    package_index = clamp_package_index(source_index, as_int("package_index", 0, None))
    return {
        "source_index": source_index,
        "package_index": package_index,
        "mode": as_int("mode", MODE_CORRECT, len(SYNC_MODES) - 1),
        "add_new_mode": as_int("add_new_mode", 1, len(ADD_NEW_MODES) - 1),
        "remove_mode": as_int("remove_mode", REMOVE_REPORT, len(REMOVE_MODES) - 1),
        "auto_mode": as_int("auto_mode", AUTO_OFF, len(AUTO_UPDATE_MODES) - 1),
        # v1.1.1: zapisujemy także opcje dodane w v1.1.0.
        # Bez tego wtyczka po każdym uruchomieniu wracała do trybu Zaawansowany
        # i domyślnych ustawień kreatorów.
        "ui_mode": as_int("ui_mode", 1, 1),
        "profile_mode": as_int("profile_mode", 1, 4),
        "skip_iptv": as_int("skip_iptv", 0, 1),
        "keep_names": as_int("keep_names", 0, 1),
        "new_filter": as_int("new_filter", 0, 3),
        "new_target": as_int("new_target", 0, 2),
        "name_mode": as_int("name_mode", 0, 2),
        "operator_profile": as_int("operator_profile", 0, 4),
    }


def save_settings(data):
    cfg = read_kv(CONFIG_PATH)
    keys = (
        "source_index", "package_index", "mode", "add_new_mode", "remove_mode", "auto_mode",
        "ui_mode", "profile_mode", "skip_iptv", "keep_names", "new_filter", "new_target",
        "name_mode", "operator_profile"
    )
    for key in keys:
        if key in data:
            cfg[key] = str(data[key])
    write_kv(CONFIG_PATH, cfg)


def load_state():
    return read_kv(STATE_PATH)


def save_state(data):
    state = read_kv(STATE_PATH)
    for k, v in data.items():
        state[k] = str(v)
    write_kv(STATE_PATH, state)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def norm_hex(value):
    value = (value or "0").strip().lower().replace("0x", "")
    value = value.lstrip("0")
    return value or "0"


def service_key_from_parts(stype, sid, tsid, onid, namespace):
    return "1:0:%s:%s:%s:%s:%s" % (
        norm_hex(stype), norm_hex(sid), norm_hex(tsid), norm_hex(onid), norm_hex(namespace)
    )


def lamedb_type_to_service_ref_hex(value):
    """Konwersja typu usługi z lamedb /4/ na typ service reference.
    W lamedb /4/ pole service_type jest zapisywane dziesiętnie, np.:
      25 = 0x19, 31 = 0x1F.
    W #SERVICE Enigma2 używa wartości szesnastkowej. Bez tej konwersji listy
    typu bzyk83 są błędnie rozpoznawane i po korekcie mogą pokazać <n/a>.
    """
    v = (value or "0").strip().lower().replace("0x", "")
    if re.match(r"^[0-9]+$", v):
        try:
            return format(int(v, 10), "x")
        except Exception:
            pass
    return norm_hex(v)


def service_ref_type_to_lamedb_decimal(value):
    """Konwersja typu z #SERVICE do lamedb /4/.
    Przykład: 0x19 -> 25, 0x1F -> 31.
    """
    try:
        return str(int(norm_hex(value), 16))
    except Exception:
        return str(value or "0").strip() or "0"


def service_key_from_lamedb_parts(stype_decimal, sid, tsid, onid, namespace):
    return "1:0:%s:%s:%s:%s:%s" % (
        lamedb_type_to_service_ref_hex(stype_decimal),
        norm_hex(sid), norm_hex(tsid), norm_hex(onid), norm_hex(namespace)
    )


def service_key(ref):
    if not ref:
        return ""
    ref = ref.strip()
    if "FROM BOUQUET" in ref:
        return ""
    parts = ref.split(":")
    if len(parts) >= 7:
        return "%s:%s:%s:%s:%s:%s:%s" % (
            parts[0].strip().lower(),
            parts[1].strip().lower(),
            norm_hex(parts[2]),
            norm_hex(parts[3]),
            norm_hex(parts[4]),
            norm_hex(parts[5]),
            norm_hex(parts[6]),
        )
    return ref.strip().lower()


def ref_from_key(key):
    # key: 1:0:type:sid:tsid:onid:namespace
    parts = key.split(":")
    if len(parts) != 7:
        return ""
    return "1:0:%s:%s:%s:%s:%s:0:0:0:" % (parts[2], parts[3], parts[4], parts[5], parts[6])


def transponder_key_from_service_key(key):
    parts = (key or "").split(":")
    if len(parts) != 7:
        return None
    # lamedb transponder key: namespace:tsid:onid
    return ":".join([norm_hex(parts[6]), norm_hex(parts[4]), norm_hex(parts[5])])


def service_core_key(key):
    """SID/TSID/ONID/namespace bez service type.
    To jest najważniejsze dla DVB i EPG: ten sam kanał może mieć w listach różny
    service type, np. 1/19/25, a EPG/picony użytkownika mogą być mapowane na
    lokalny typ. Dlatego v1.0.10 nie wymusza typu z bazy kontrolnej.
    """
    parts = (key or "").split(":")
    if len(parts) != 7:
        return ""
    return ":".join([norm_hex(parts[3]), norm_hex(parts[4]), norm_hex(parts[5]), norm_hex(parts[6])])


def service_type_from_key(key):
    parts = (key or "").split(":")
    if len(parts) == 7:
        return norm_hex(parts[2])
    return ""


def key_with_local_service_type(local_key, remote_key):
    """Zwraca remote SID/TSID/ONID/namespace, ale zachowuje lokalny service type.
    Dzięki temu korekta parametrów nie rozrywa mapowania EPG/piconów używanego przez
    listę użytkownika albo EPGImport.
    """
    lp = (local_key or "").split(":")
    rp = (remote_key or "").split(":")
    if len(lp) != 7 or len(rp) != 7:
        return remote_key
    return "1:0:%s:%s:%s:%s:%s" % (norm_hex(lp[2]), norm_hex(rp[3]), norm_hex(rp[4]), norm_hex(rp[5]), norm_hex(rp[6]))


def build_remote_core_index(remote_services):
    by_core = {}
    # preferencja tylko gdy w bazie są duplikaty tej samej usługi z innym service type
    pref = {"1": 0, "19": 1, "25": 2, "16": 3, "11": 4, "1f": 5}
    for key in (remote_services or {}).keys():
        core = service_core_key(key)
        if not core:
            continue
        old = by_core.get(core)
        if old is None or pref.get(service_type_from_key(key), 99) < pref.get(service_type_from_key(old), 99):
            by_core[core] = key
    return by_core


def valid_service_key(key):
    return len((key or "").split(":")) == 7


def valid_dvb_service_ref(ref):
    if not ref or "FROM BOUQUET" in ref:
        return False
    parts = ref.strip().split(":")
    if len(parts) < 7:
        return False
    if parts[0] != "1" or parts[1] != "0":
        return False
    if norm_hex(parts[2]) in SKIP_SERVICE_TYPES:
        return False
    if norm_hex(parts[3]) == "0":
        return False
    return True


def is_terrestrial_namespace(namespace):
    """Rozpoznaje DVB-T/DVB-C, których wtyczka nie ma ruszać."""
    ns = norm_hex(namespace)
    return ns.startswith("eeee") or ns.startswith("ffff")


def is_terrestrial_service_key(key):
    parts = (key or "").split(":")
    if len(parts) != 7:
        return False
    return is_terrestrial_namespace(parts[6])


def is_terrestrial_service_ref(ref):
    if not ref or "FROM BOUQUET" in ref:
        return False
    parts = ref.strip().split(":")
    if len(parts) < 7:
        return False
    return is_terrestrial_namespace(parts[6])


def is_dvbt_ref(ref):
    """Alias zgodności dla narzędzi diagnostycznych v1.1.x.
    Rozpoznaje wpisy DVB-T/DVB-C, których wtyczka nie powinna analizować
    jako satelitarne. Brak tej funkcji powodował błędy w duplikatach i
    kontroli EPG/piconów.
    """
    return is_terrestrial_service_ref(ref)


def is_dvbt_bouquet_title(title):
    n = normalize_basic(title)
    patterns = ("dvb-t", "dvb t", "dvbt", "dtt", "naziemna", "naziemne", "mux", "terrestrial")
    return any(p in n for p in patterns)


def normalize_basic(name):
    name = name or ""
    name = name.strip()
    name = name.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    name = name.replace("\xc2\x86", "").replace("\xc2\x87", "")
    name = name.lower()
    repl = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z",
        "ä": "a", "ö": "o", "ü": "u", "ß": "ss", "é": "e", "è": "e", "à": "a", "ì": "i", "ò": "o", "ù": "u",
        "á": "a", "í": "i", "ú": "u", "ý": "y", "č": "c", "ř": "r", "š": "s", "ť": "t", "ž": "z"
    }
    for src, dst in repl.items():
        name = name.replace(src, dst)
    name = re.sub(r"[\t\r\n]+", " ", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def normalize_strict(name):
    return normalize_basic(name)


def normalize_variant(name):
    name = normalize_basic(name)
    # Ostrożna normalizacja: nie usuwa rdzenia nazwy, tylko końcowe znaczniki jakości.
    name = re.sub(r"\b(hevc|mpeg4|mpeg-4|dvb-s2)\b", "", name)
    name = re.sub(r"\b(uhd|4k|hd|sd)\b", "", name)
    name = re.sub(r"\s+", " ", name)
    return name.strip()


def name_is_usable(name):
    n = normalize_basic(name)
    return bool(n and n not in ("n/a", "<n/a>", "na", "brak", "none"))


def bouquet_files(path):
    if not os.path.isdir(path):
        return []
    out = []
    for name in os.listdir(path):
        if name.startswith("userbouquet.") and name.endswith(".tv"):
            out.append(os.path.join(path, name))
    out.sort()
    return out


def is_managed_bouquet(path):
    base = os.path.basename(path)
    return base.startswith("userbouquet." + MANAGED_PREFIX) or base.startswith("userbouquet.pp_channel_sync")


def local_user_bouquet_files():
    return [fn for fn in bouquet_files(E2_PATH) if not is_managed_bouquet(fn)]


def managed_bouquet_files():
    return [fn for fn in bouquet_files(E2_PATH) if is_managed_bouquet(fn)]


def find_file(root, filename):
    for base, _dirs, files in os.walk(root):
        for name in files:
            if name == filename:
                return os.path.join(base, name)
    return None


def find_remote_bouquets(root):
    out = []
    for base, _dirs, files in os.walk(root):
        for name in files:
            if name.startswith("userbouquet.") and name.endswith(".tv"):
                out.append(os.path.join(base, name))
    out.sort()
    return out


def transponder_key_from_line(line):
    s = (line or "").strip()
    if not s or s == "/":
        return None
    if s.startswith("t:"):
        parts = s.split(":")
        if len(parts) >= 4:
            return ":".join([norm_hex(parts[1]), norm_hex(parts[2]), norm_hex(parts[3])])
    if re.match(r"^[0-9A-Fa-f]+:[0-9A-Fa-f]+:[0-9A-Fa-f]+$", s):
        p = s.split(":")
        return ":".join([norm_hex(p[0]), norm_hex(p[1]), norm_hex(p[2])])
    return None


def service_key_from_lamedb_line(line):
    s = (line or "").strip()
    if not s or s == "/":
        return None
    raw = s
    # lamedb /5/ bywa zapisywany jako pełny service reference z prefiksem s:
    # s:1:0:19:3DCD:640:13E:820000:0:0:0:
    if raw.startswith("s:1:0:"):
        return service_key(raw[2:])
    # albo jako pełny service reference bez prefiksu:
    # 1:0:19:3DCD:640:13E:820000:0:0:0:
    parts_ref = raw.split(":")
    if len(parts_ref) >= 7 and parts_ref[0] == "1" and parts_ref[1] == "0":
        return service_key(raw)
    # lamedb /4/ zapisuje usługę jako:
    # sid:namespace:tsid:onid:service_type:flags...
    if raw.startswith("s:"):
        raw = raw[2:]
    parts = raw.split(":")
    if len(parts) >= 5 and re.match(r"^[0-9A-Fa-f]+$", parts[0] or ""):
        return service_key_from_lamedb_parts(parts[4], parts[0], parts[2], parts[3], parts[1])
    return None


def split_lamedb_sections(text):
    lines = text.splitlines()
    trans_idx = None
    trans_end = None
    serv_idx = None
    serv_end = None

    # Obsługa lamedb /4/ i /5/. Różne obrazy mają drobne różnice w nagłówku,
    # dlatego szukamy tylko realnych znaczników sekcji.
    for i, line in enumerate(lines):
        if line.strip().lower() == "transponders":
            trans_idx = i
            break
    if trans_idx is not None:
        for i in range(trans_idx + 1, len(lines)):
            if lines[i].strip() == "/":
                trans_end = i
                break

    search_from = (trans_end + 1) if trans_end is not None else 0
    for i in range(search_from, len(lines)):
        if lines[i].strip().lower() == "services":
            serv_idx = i
            break
    if serv_idx is None:
        # Awaryjnie: spotykane są lamedb z nietypowym układem po ręcznych edycjach.
        for i, line in enumerate(lines):
            if line.strip().lower() == "services":
                serv_idx = i
                break

    if serv_idx is not None:
        for i in range(serv_idx + 1, len(lines)):
            st = lines[i].strip().lower()
            if st == "/" or st == "end":
                serv_end = i
                break

    if trans_idx is None or trans_end is None or serv_idx is None or serv_end is None:
        return None
    return {
        "lines": lines,
        "trans_idx": trans_idx,
        "trans_end": trans_end,
        "serv_idx": serv_idx,
        "serv_end": serv_end,
        "header": lines[:trans_idx + 1],
        "transponders": lines[trans_idx + 1:trans_end],
        "services_header_index": serv_idx,
        "services": lines[serv_idx + 1:serv_end],
        "footer": lines[serv_end:],
    }


def parse_blocks(section_lines, key_func):
    blocks = OrderedDict()
    cur_key = None
    cur = []
    for line in section_lines:
        key = key_func(line)
        if key is not None and not line.startswith(" ") and not line.startswith("\t"):
            if cur_key is not None:
                blocks[cur_key] = cur
            cur_key = key
            cur = [line]
        else:
            if cur_key is not None:
                cur.append(line)
    if cur_key is not None:
        blocks[cur_key] = cur
    return blocks


def parse_lamedb(path):
    data = {"path": path, "sections": None, "transponders": OrderedDict(), "services": OrderedDict(), "names": {}}
    if not path or not os.path.isfile(path):
        return data
    text = read_text(path)
    sections = split_lamedb_sections(text)
    data["sections"] = sections
    if not sections:
        return data
    data["transponders"] = parse_blocks(sections["transponders"], transponder_key_from_line)
    data["services"] = parse_blocks(sections["services"], service_key_from_lamedb_line)
    for key, block in data["services"].items():
        nm = service_name_from_block(block)
        if nm:
            data["names"][key] = nm
    return data


def parse_local_lamedb():
    # Podstawowy plik to lamedb. Część obrazów trzyma jednak aktywną bazę jako lamedb5.
    primary = parse_lamedb(os.path.join(E2_PATH, "lamedb"))
    if primary.get("sections"):
        return primary
    alt = parse_lamedb(os.path.join(E2_PATH, "lamedb5"))
    if alt.get("sections"):
        return alt
    return primary

def load_local_lamedb():
    # Alias zgodności dla narzędzi dodanych w v1.1.x.
    # Część funkcji diagnostycznych korzysta z tej nazwy, a właściwy parser
    # lokalnego lamedb to parse_local_lamedb().
    return parse_local_lamedb()


def service_name_from_block(block):
    if not block or len(block) < 2:
        return ""
    for line in block[1:]:
        s = line.strip()
        if not s or s == "/":
            continue
        if s.startswith("c:") or s.startswith("C:") or s.startswith("p:") or s.startswith("P:") or s.startswith("f:") or s.startswith("F:"):
            continue
        return s
    return ""


def remote_ref_from_service_key(key):
    return ref_from_key(key)


def cleanup_workdir():
    if os.path.isdir(WORK_DIR):
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    ensure_dir(WORK_DIR)


def download_url(url, dest, min_size=1024):
    if Request is None or urlopen is None:
        raise Exception("Brak obsługi urllib w systemie Python.")
    req = Request(url, headers={"User-Agent": "PPChannelSync/%s Enigma2" % PLUGIN_VERSION})
    response = urlopen(req, timeout=60)
    data = response.read()
    if not data or len(data) < int(min_size or 1):
        raise Exception("Pobrany plik jest pusty albo za mały.")
    ensure_dir(os.path.dirname(dest))
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def fetch_json(url):
    if Request is None or urlopen is None:
        raise Exception("Brak obsługi urllib w systemie Python.")
    req = Request(url, headers={"User-Agent": "PPChannelSync/%s Enigma2" % PLUGIN_VERSION, "Accept": "application/vnd.github+json"})
    data = urlopen(req, timeout=30).read()
    return json.loads(data.decode("utf-8", "ignore"))


def quote_url_path(path):
    path = str(path or "")
    if url_quote is None:
        return path.replace(" ", "%20").replace("+", "%2B")
    try:
        return url_quote(path, safe="/")
    except Exception:
        try:
            return url_quote(path.encode("utf-8"), safe="/")
        except Exception:
            return path.replace(" ", "%20").replace("+", "%2B")


def sha256_many(paths):
    h = hashlib.sha256()
    for path in sorted(paths):
        try:
            h.update(os.path.basename(path).encode("utf-8", "ignore"))
            with open(path, "rb") as f:
                while True:
                    data = f.read(65536)
                    if not data:
                        break
                    h.update(data)
        except Exception:
            pass
    return h.hexdigest()


def is_gioppygio_needed_file(name):
    n = (name or "").strip()
    low = n.lower()
    if n in ("lamedb", "lamedb5", "bouquets.tv", "bouquets.radio"):
        return True
    if low.startswith("userbouquet.") and (low.endswith(".tv") or low.endswith(".radio")):
        return True
    return False


def download_gioppygio_package(dirname):
    dirname = str(dirname or "").strip().strip("/")
    if not dirname or "/" in dirname or ".." in dirname:
        raise Exception("Nieprawidłowy katalog GioppyGio: %s" % dirname)
    target_dir = os.path.join(WORK_DIR, "gioppygio", dirname)
    ensure_dir(target_dir)
    api_url = GIOPPYGIO_API_BASE + quote_url_path(dirname)
    items = fetch_json(api_url)
    if not isinstance(items, list):
        raise Exception("GioppyGio nie zwrócił listy plików dla: %s" % dirname)
    downloaded = []
    for item in items:
        try:
            if item.get("type") != "file":
                continue
            name = item.get("name", "")
            if not is_gioppygio_needed_file(name):
                continue
            url = item.get("download_url") or (GIOPPYGIO_RAW_BASE + quote_url_path(dirname + "/" + name))
            dest = os.path.join(target_dir, name)
            download_url(url, dest, min_size=1)
            downloaded.append(dest)
        except Exception:
            # Jeden problematyczny bukiet nie może zatrzymać całej bazy; lamedb sprawdzamy niżej.
            continue
    lamedb = os.path.join(target_dir, "lamedb")
    if not os.path.isfile(lamedb):
        raise Exception("W katalogu GioppyGio nie pobrano pliku lamedb: %s" % dirname)
    bouquets = find_remote_bouquets(target_dir)
    return target_dir, lamedb, bouquets, sha256_many(downloaded), api_url


def _date_key_from_filename(name):
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})\.zip$", name or "", re.I)
    if not m:
        return (0, 0, 0, name or "")
    d, mo, y = m.groups()
    return (int(y), int(mo), int(d), name or "")


def resolve_ciefp_url(prefix):
    # Pobiera listę plików z GitHub API i wybiera najnowszy ZIP po prefiksie.
    # Gdy API jest niedostępne, zostaje awaryjny link z ostatnią znaną datą.
    try:
        data = fetch_json(CIEFP_API_URL)
        matches = []
        for item in data:
            name = item.get("name", "")
            if name.startswith(prefix) and name.lower().endswith(".zip"):
                matches.append(item)
        if matches:
            matches.sort(key=lambda x: _date_key_from_filename(x.get("name", "")))
            item = matches[-1]
            return item.get("download_url") or (CIEFP_RAW_BASE + item.get("name", "")), item.get("name", prefix)
    except Exception:
        pass
    filename = prefix + CIEFP_FALLBACK_DATE + ".zip"
    return CIEFP_RAW_BASE + filename, filename


def _safe_target(base_dir, member_name):
    target = os.path.abspath(os.path.join(base_dir, member_name))
    base = os.path.abspath(base_dir)
    if not (target == base or target.startswith(base + os.sep)):
        raise Exception("Archiwum zawiera niebezpieczną ścieżkę: %s" % member_name)
    return target


def extract_archive(archive_path, dest_dir):
    ensure_dir(dest_dir)
    try:
        with zipfile.ZipFile(archive_path, "r") as z:
            for member in z.infolist():
                _safe_target(dest_dir, member.filename)
            z.extractall(dest_dir)
            return dest_dir
    except zipfile.BadZipFile:
        pass
    try:
        with tarfile.open(archive_path, "r:*") as tar:
            for member in tar.getmembers():
                _safe_target(dest_dir, member.name)
            tar.extractall(dest_dir)
            return dest_dir
    except Exception:
        raise Exception("Nie udało się rozpakować paczki kontrolnej. To nie jest poprawny ZIP/TAR.")


def load_online_package(pkg_index, source_index=SOURCE_STANDARD):
    cleanup_workdir()
    try:
        source_index = int(source_index or 0)
    except Exception:
        source_index = SOURCE_STANDARD
    if source_index < 0 or source_index >= len(SOURCE_OPTIONS):
        source_index = SOURCE_STANDARD
    pkg_index = clamp_package_index(source_index, pkg_index)
    packages = packages_for_source(source_index)
    label, value = packages[pkg_index]
    source_label = SOURCE_OPTIONS[source_index][0]
    if source_index == SOURCE_ALTERNATIVE:
        url, resolved_name = resolve_ciefp_url(value)
        resolved_label = "%s / %s" % (label, resolved_name)
    elif source_index == SOURCE_GIOPPYGIO:
        root, lamedb, bouquets, archive_hash, url = download_gioppygio_package(value)
        resolved_label = "%s / %s" % (label, value)
        return {"label": label, "resolved_label": resolved_label, "source_label": source_label, "source_index": source_index, "url": url, "hash": archive_hash, "root": root, "lamedb": lamedb, "bouquets": bouquets}
    else:
        url = value
        resolved_label = label
    archive_path = os.path.join(WORK_DIR, "settings.zip")
    download_url(url, archive_path)
    archive_hash = sha256_file(archive_path)
    extract_dir = os.path.join(WORK_DIR, "extracted")
    extract_archive(archive_path, extract_dir)
    lamedb = find_file(extract_dir, "lamedb")
    bouquets = find_remote_bouquets(extract_dir)
    if not lamedb:
        raise Exception("W paczce kontrolnej nie znaleziono pliku lamedb.")
    return {"label": label, "resolved_label": resolved_label, "source_label": source_label, "source_index": source_index, "url": url, "hash": archive_hash, "root": extract_dir, "lamedb": lamedb, "bouquets": bouquets}


def make_backup():
    ensure_dir(BACKUP_DIR)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = os.path.join(BACKUP_DIR, "PPChannelSync_%s.tar.gz" % stamp)
    with tarfile.open(backup_name, "w:gz") as tar:
        for name in os.listdir(E2_PATH):
            if name in ("lamedb", "lamedb5", "bouquets.tv") or (name.startswith("userbouquet.") and name.endswith(".tv")):
                full = os.path.join(E2_PATH, name)
                if os.path.isfile(full):
                    tar.add(full, arcname=name)
    return backup_name


def latest_backup():
    if not os.path.isdir(BACKUP_DIR):
        return None
    backups = [os.path.join(BACKUP_DIR, n) for n in os.listdir(BACKUP_DIR) if n.startswith("PPChannelSync_") and n.endswith(".tar.gz")]
    backups.sort()
    return backups[-1] if backups else None


def restore_backup(path):
    if not path or not os.path.isfile(path):
        raise Exception("Brak kopii bezpieczeństwa.")
    with tarfile.open(path, "r:gz") as tar:
        tar.extractall(E2_PATH)
    reload_enigma_bouquets()


def parse_bouquet_entries(path, local_names=None):
    local_names = local_names or {}
    try:
        lines = read_text(path).splitlines()
    except Exception:
        return [], []
    entries = []
    pending_idx = None
    pending_ref = None
    for idx, line in enumerate(lines):
        if line.startswith("#SERVICE "):
            ref = line[len("#SERVICE "):].strip()
            if "FROM BOUQUET" in ref or not valid_dvb_service_ref(ref):
                pending_idx = None
                pending_ref = None
                continue
            pending_idx = idx
            pending_ref = ref
            # wpis bez DESCRIPTION też będzie obsłużony, jeśli kolejna linia nie jest description
            entries.append({
                "path": path,
                "service_index": idx,
                "desc_index": None,
                "ref": ref,
                "key": service_key(ref),
                "name": local_names.get(service_key(ref), ""),
                "source": "lamedb",
            })
            continue
        if line.startswith("#DESCRIPTION ") and pending_idx is not None and pending_ref:
            desc = line[len("#DESCRIPTION "):].strip()
            if entries and entries[-1].get("service_index") == pending_idx:
                entries[-1]["desc_index"] = idx
                if name_is_usable(desc):
                    entries[-1]["name"] = desc
                    entries[-1]["source"] = "description"
            pending_idx = None
            pending_ref = None
            continue
        if not line.startswith("#DESCRIPTION "):
            pending_idx = None
            pending_ref = None
    return lines, entries


def remote_names_from_bouquets(remote):
    names = {}
    all_candidates = {}
    for fn in remote.get("bouquets", []):
        lines, entries = parse_bouquet_entries(fn, {})
        for e in entries:
            if not e.get("name"):
                # spróbuj DESCRIPTION z kolejnej linii w pliku źródłowym; parse_bouquet_entries już to robi, jeśli jest.
                pass
            if not name_is_usable(e.get("name")):
                continue
            key = e["key"]
            ref = e["ref"]
            strict = normalize_strict(e["name"])
            variant = normalize_variant(e["name"])
            all_candidates.setdefault(("strict", strict), {})[key] = {"name": e["name"], "ref": ref, "key": key}
            all_candidates.setdefault(("variant", variant), {})[key] = {"name": e["name"], "ref": ref, "key": key}
    return all_candidates


def build_remote_index(remote):
    rdb = parse_lamedb(remote["lamedb"])
    candidates = remote_names_from_bouquets(remote)
    for key, name in rdb["names"].items():
        if not name_is_usable(name):
            continue
        ref = remote_ref_from_service_key(key)
        strict = normalize_strict(name)
        variant = normalize_variant(name)
        candidates.setdefault(("strict", strict), {})[key] = {"name": name, "ref": ref, "key": key}
        candidates.setdefault(("variant", variant), {})[key] = {"name": name, "ref": ref, "key": key}
    strict_unique = {}
    variant_unique = {}
    for (kind, name), by_key in candidates.items():
        if len(by_key) == 1:
            if kind == "strict":
                strict_unique[name] = list(by_key.values())[0]
            elif kind == "variant":
                variant_unique[name] = list(by_key.values())[0]
    return rdb, strict_unique, variant_unique


def find_match_for_entry(entry, remote_services, strict_unique, variant_unique, match_mode):
    cur_key = entry.get("key")
    if cur_key in remote_services:
        return {"kind": "same_ref", "key": cur_key, "ref": entry.get("ref"), "name": entry.get("name", "")}
    if match_mode < MATCH_EXACT:
        return None
    name = entry.get("name") or ""
    if not name_is_usable(name):
        return None
    strict = normalize_strict(name)
    cand = strict_unique.get(strict)
    if cand:
        return {"kind": "exact_name", "key": cand["key"], "ref": cand["ref"], "name": cand.get("name", name)}
    if match_mode >= MATCH_MODERATE:
        variant = normalize_variant(name)
        cand = variant_unique.get(variant)
        if cand:
            return {"kind": "variant_name", "key": cand["key"], "ref": cand["ref"], "name": cand.get("name", name)}
    return None



def extract_bouquet_channels(path, local_names=None):
    lines, entries = parse_bouquet_entries(path, local_names or {})
    out = []
    for e in entries:
        if not valid_dvb_service_ref(e.get("ref")):
            continue
        name = e.get("name") or ""
        if not name_is_usable(name):
            continue
        out.append({
            "path": path,
            "ref": e.get("ref"),
            "key": e.get("key"),
            "name": name,
            "service_line": "#SERVICE %s" % e.get("ref"),
            "description_line": "#DESCRIPTION %s" % name,
        })
    return lines, out


def remote_bouquet_index(remote, remote_db):
    items = []
    for fn in remote.get("bouquets", []):
        lines, entries = extract_bouquet_channels(fn, remote_db.get("names") or {})
        title = bouquet_name_from_lines(lines, os.path.basename(fn).replace("userbouquet.", "").replace(".tv", ""))
        if not entries:
            continue
        items.append({"path": fn, "title": title, "key": bouquet_match_key(title), "entries": entries})
    return items


def find_remote_bouquet_for_local(local_title, remote_items):
    for item in remote_items:
        if bouquet_titles_similar(local_title, item.get("title", "")):
            return item
    lk = bouquet_match_key(local_title)
    if lk:
        for item in remote_items:
            rk = item.get("key", "")
            if lk == rk:
                return item
    return None


def find_remote_bouquet_for_local_entries(local_title, local_entries, remote_items):
    # Najpierw tytuł, a jeżeli tytuły się różnią, wybierz bukiet z największym
    # pokryciem nazw kanałów. To jest ważne dla list typu "Polskie", gdy baza
    # kontrolna nazywa odpowiednik np. Canal+Polska albo Polsat Box.
    by_title = find_remote_bouquet_for_local(local_title, remote_items)
    if by_title:
        return by_title
    local_names = set()
    for e in local_entries or []:
        if name_is_usable(e.get("name")):
            local_names.add(normalize_strict(e.get("name")))
    if not local_names:
        return None
    best = None
    best_score = 0
    best_remote_count = 0
    for item in remote_items or []:
        remote_names = set([normalize_strict(r.get("name")) for r in item.get("entries", []) if name_is_usable(r.get("name"))])
        if not remote_names:
            continue
        score = len(local_names.intersection(remote_names))
        if score > best_score:
            best = item
            best_score = score
            best_remote_count = len(remote_names)
    # Minimalny próg ostrożności: co najmniej 5 wspólnych kanałów albo 20% lokalnego bukietu.
    threshold = max(5, int(max(1, len(local_names)) * 0.20))
    if best and best_score >= threshold:
        return best
    return None


def candidate_from_global_name(entry, strict_unique):
    name = entry.get("name") or ""
    if not name_is_usable(name):
        return None
    return strict_unique.get(normalize_strict(name))


def local_service_block_for_key(local_db, key):
    if not local_db or not key:
        return None
    block = (local_db.get("services") or {}).get(key)
    if block:
        return block
    return None


def local_transponder_block_for_service_key(local_db, key):
    tkey = transponder_key_from_service_key(key)
    if not tkey:
        return None, None
    block = (local_db.get("transponders") or {}).get(tkey)
    return tkey, block


def add_local_protection(plan, key):
    """Zachowuje lokalny wpis lamedb dla kanałów nierozpoznanych.
    Od v1.0.12 bazą zapisu jest lokalny lamedb, więc zwykle nie trzeba nic
    dopisywać. Funkcja zostaje jako zabezpieczenie dla nietypowych przypadków.
    """
    local_db = plan.get("local_db") or {}
    if not key:
        return
    block = local_service_block_for_key(local_db, key)
    if block:
        # Jeżeli lokalny lamedb jest bazą, ten wpis już zostanie zachowany.
        return


def add_remote_service_for_key(plan, key, source_key=None):
    """Dopisuje do lokalnego lamedb brakujący service/transponder z bazy kontrolnej.
    To jest kluczowe dla list typu bzyk83: nie wolno podmieniać całego lamedb,
    ale nowe kanały i pewne korekty muszą mieć swoje wpisy techniczne.
    key        - klucz, który ma istnieć w lamedb po korekcie,
    source_key - klucz z bazy kontrolnej, z którego bierzemy nazwę/C/PID/CAID.
    """
    remote_db = plan.get("remote_db") or {}
    local_db = plan.get("local_db") or {}
    source_key = source_key or key
    if not key or not source_key:
        return
    if key in (local_db.get("services") or {}):
        return
    block = (remote_db.get("services") or {}).get(source_key)
    if block:
        plan["service_appends"][key] = block
    tkey = transponder_key_from_service_key(key)
    source_tkey = transponder_key_from_service_key(source_key)
    if tkey and tkey not in (local_db.get("transponders") or {}):
        tblock = (remote_db.get("transponders") or {}).get(source_tkey)
        if tblock:
            plan["transponder_updates"][tkey] = tblock


def find_remote_bouquet_for_new_channels(local_title, local_entries, remote_items):
    """Dopasowanie bukietu tylko do wykrywania NOWYCH kanałów.
    Nie wolno na jego podstawie przebudowywać ani usuwać obecnej listy.
    """
    by_title = find_remote_bouquet_for_local(local_title, remote_items)
    if by_title:
        return by_title
    local_names = set()
    for e in local_entries or []:
        if name_is_usable(e.get("name")):
            local_names.add(normalize_strict(e.get("name")))
    if not local_names:
        return None
    best = None
    best_score = 0
    best_ratio = 0.0
    for item in remote_items or []:
        remote_names = set([normalize_strict(r.get("name")) for r in item.get("entries", []) if name_is_usable(r.get("name"))])
        if not remote_names:
            continue
        score = len(local_names.intersection(remote_names))
        ratio = float(score) / float(max(1, len(local_names)))
        if score > best_score or (score == best_score and ratio > best_ratio):
            best = item
            best_score = score
            best_ratio = ratio
    # Wyższy próg niż w poprzednich wersjach: nowe kanały tylko przy mocnym dopasowaniu.
    threshold = max(8, int(max(1, len(local_names)) * 0.35))
    if best and best_score >= threshold:
        return best
    return None


def build_plan(remote, match_mode=None, add_new=True, remove_mode=REMOVE_REPORT):
    local_db = parse_local_lamedb()
    remote_db, strict_unique, variant_unique = build_remote_index(remote)
    remote_services = remote_db["services"]
    remote_core_index = build_remote_core_index(remote_services)
    user_files = local_user_bouquet_files()
    remote_items = remote_bouquet_index(remote, remote_db)

    plan = {
        "remote": remote,
        "local_db": local_db,
        "remote_db": remote_db,
        "remote_items": remote_items,
        "files": {},
        "checked": 0,
        "same_ref": 0,
        "ref_fixes": [],
        "service_appends": OrderedDict(),
        "service_replacements_blocked": [],
        "epg_type_aliases": [],
        "transponder_updates": OrderedDict(),
        "unmatched": [],
        "no_name": [],
        "new_channels": OrderedDict(),
        "new_channels_available": 0,
        "new_channels_added": 0,
        "new_channels_skipped": [],
        "removed_channels": [],
        "removed_count": 0,
        "remove_candidates": [],
        "remote_total_services": len(remote_services),
        "local_user_files": len(user_files),
        "marker_updates": 0,
        "add_new": bool(add_new),
        "remove_mode": remove_mode,
        "replace_lamedb": True,
        "protected_local_services": 0,
        "skipped_dvbt_bouquets": [],
        "skipped_dvbt_channels": 0,
    }

    for fn in user_files:
        lines, entries = parse_bouquet_entries(fn, local_db["names"])
        local_title = bouquet_name_from_lines(lines, os.path.basename(fn).replace("userbouquet.", "").replace(".tv", ""))
        if is_dvbt_bouquet_title(local_title) or any(is_terrestrial_service_key(e.get("key")) for e in entries):
            plan["skipped_dvbt_bouquets"].append(local_title or os.path.basename(fn))
            plan["skipped_dvbt_channels"] += len(entries)
            continue
        file_plan = {
            "lines": lines,
            "entries": entries,
            "changes": {},
            "remove_indices": set(),
            "title": local_title,
            "remote_title": "",
        }
        plan["files"][fn] = file_plan

        used_remote_keys = set()
        used_names = set()

        for e in entries:
            plan["checked"] += 1
            cur_key = e.get("key")
            name = e.get("name") or ""
            if not cur_key:
                plan["no_name"].append(e)
                continue
            if is_terrestrial_service_key(cur_key):
                plan["skipped_dvbt_channels"] += 1
                continue
            if name_is_usable(name):
                used_names.add(normalize_strict(name))

            local_services = local_db.get("services") or {}
            if cur_key in local_services:
                # Najważniejsza zasada v1.2.0:
                # jeżeli kanał istnieje w lokalnym lamedb użytkownika, NIE podmieniamy jego
                # #SERVICE, nawet jeśli baza kontrolna ma inny wariant. To chroni EPG, picony
                # i autorski układ listy. Baza kontrolna służy wtedy tylko do dopisania nowych
                # kanałów oraz raportu.
                plan["same_ref"] += 1
                if cur_key in remote_services:
                    used_remote_keys.add(cur_key)
                continue

            if cur_key in remote_services:
                # Wpis jest w bazie kontrolnej, ale brakuje go lokalnie. Dopisujemy go do lamedb
                # bez zmiany pozycji w bukiecie.
                plan["same_ref"] += 1
                add_remote_service_for_key(plan, cur_key, cur_key)
                used_remote_keys.add(cur_key)
                continue

            # v1.2.0: dopiero gdy wpisu nie ma ani w lokalnym lamedb, ani w bazie po identycznym
            # kluczu, próbujemy bezpiecznych aliasów/naprawy.
            # Najpierw sprawdzamy ten sam SID/TSID/ONID/namespace z innym service type.
            # To był powód braków EPG w części kanałów: baza kontrolna miała np. typ 25,
            # a lista/EPG użytkownika pracowała na typie 1 albo 19. W takiej sytuacji
            # NIE zmieniamy #SERVICE w bukiecie, tylko dopisujemy alias service do lamedb.
            core_key = service_core_key(cur_key)
            remote_same_core = remote_core_index.get(core_key)
            if remote_same_core:
                remote_block = remote_services.get(remote_same_core)
                if remote_block:
                    add_remote_service_for_key(plan, cur_key, remote_same_core)
                    plan["epg_type_aliases"].append({
                        "file": fn,
                        "bouquet": local_title,
                        "name": name,
                        "local_key": cur_key,
                        "remote_key": remote_same_core,
                        "local_type": service_type_from_key(cur_key),
                        "remote_type": service_type_from_key(remote_same_core),
                    })
                    used_remote_keys.add(remote_same_core)
                    continue

            # Reference nie istnieje w bazie kontrolnej i nie ma tego samego SID/TSID/ONID/namespace.
            # Szukamy wyłącznie jednoznacznego odpowiednika po dokładnej nazwie globalnej, ale
            # przy zmianie zachowujemy LOKALNY service type, żeby nie zerwać mapowania EPG.
            cand = candidate_from_global_name(e, strict_unique)
            if cand and cand.get("key") and cand.get("ref"):
                remote_key = cand.get("key")
                new_key = key_with_local_service_type(cur_key, remote_key)
                new_ref = ref_from_key(new_key)
                if new_ref and new_ref != e.get("ref"):
                    file_plan["changes"][e.get("service_index")] = "#SERVICE %s" % new_ref
                    plan["ref_fixes"].append({
                        "file": fn,
                        "service_index": e.get("service_index"),
                        "old_ref": e.get("ref"),
                        "new_ref": new_ref,
                        "old_key": cur_key,
                        "new_key": new_key,
                        "remote_key": remote_key,
                        "name": name,
                        "bouquet": local_title,
                        "remote_bouquet": "dokładna nazwa + zachowany lokalny service type",
                    })
                # Zapewnij wpis lamedb dla nowego klucza z lokalnym service type.
                remote_block = remote_services.get(remote_key)
                if remote_block:
                    add_remote_service_for_key(plan, new_key, remote_key)
                    plan["epg_type_aliases"].append({
                        "file": fn,
                        "bouquet": local_title,
                        "name": name,
                        "local_key": new_key,
                        "remote_key": remote_key,
                        "local_type": service_type_from_key(new_key),
                        "remote_type": service_type_from_key(remote_key),
                    })
                used_remote_keys.add(remote_key)
            else:
                # Brak pewnego odpowiednika: NIE usuwamy i NIE zmieniamy.
                # Chronimy stary wpis przez doscalenie lokalnego service do nowego lamedb.
                add_local_protection(plan, cur_key)
                plan["unmatched"].append(e)
                plan["remove_candidates"].append({"bouquet": local_title, "name": name or e.get("ref"), "ref": e.get("ref")})

        # Nowe kanały: opcjonalnie, wyłącznie na końcu mocno dopasowanego istniejącego bukietu.
        remote_item = find_remote_bouquet_for_new_channels(local_title, entries, remote_items)
        if remote_item:
            file_plan["remote_title"] = remote_item.get("title") or ""
            local_keys_after = set(used_remote_keys)
            # uwzględnij również obecne lokalne klucze, aby nie dublować kanałów, których nie zmieniamy
            for e in entries:
                if e.get("key"):
                    local_keys_after.add(e.get("key"))
            to_add = []
            for r in remote_item.get("entries", []):
                rkey = r.get("key")
                rname = r.get("name") or ""
                if not rkey or not r.get("ref"):
                    continue
                if rkey in local_keys_after:
                    continue
                if name_is_usable(rname) and normalize_strict(rname) in used_names:
                    continue
                plan["new_channels_available"] += 1
                if add_new:
                    to_add.append(r)
                    add_remote_service_for_key(plan, rkey, rkey)
                else:
                    plan["new_channels_skipped"].append({"bouquet": local_title, "name": rname, "ref": r.get("ref")})
            if to_add:
                plan["new_channels"][fn] = to_add
                plan["new_channels_added"] += len(to_add)
        else:
            file_plan["remote_title"] = "brak mocnego dopasowania - bez dopisywania nowych kanałów"

        # Usuwanie istniejących kanałów jest w tej gałęzi celowo wyłączone.
        # Nawet jeśli kanał wygląda na nieaktualny, trafia do raportu jako kandydat,
        # ale nie jest usuwany z bukietu. Usuwanie poprawnych pozycji było zbyt ryzykowne.
        # Docelowo można dodać osobny ekran ręcznego zatwierdzania usunięć.
        if False and remove_mode == REMOVE_DELETE:
            pass

    plan["protected_local_services"] = len(plan["service_appends"])
    return plan

def report_header_lines():
    return [
        "by Paweł Pawełek * %s" % CONTACT,
        "%s." % _(SUPPORT_TEXT),
        "",
    ]


def write_report(plan, mode, match_mode=None):
    report = []
    details = []
    report.extend(report_header_lines())
    report.append("PP Channel Sync v%s" % PLUGIN_VERSION)
    report.append("Źródło kontroli: %s" % plan["remote"].get("source_label", "Standard"))
    report.append("Pakiet kontrolny: %s" % plan["remote"].get("resolved_label", plan["remote"]["label"]))
    report.append("Tryb: %s" % SYNC_MODES[mode][0])
    report.append("Dopisywanie nowych kanałów: %s" % ("TAK - tylko na końcu mocno dopasowanych bukietów" if plan.get("add_new") else "NIE"))
    report.append("Usuwanie kanałów: %s" % REMOVE_MODES[plan.get("remove_mode", REMOVE_REPORT)][0])
    report.append("")
    report.append("Zasada działania v1.0.17:")
    report.append("- układ, kolejność i numeracja obecnych kanałów zostają zachowane,")
    report.append("- wtyczka nie synchronizuje całych bukietów z bazą kontrolną,")
    report.append("- lamedb jest budowany na bazie lokalnego lamedb użytkownika + brakujące wpisy z bazy kontrolnej,")
    report.append("- typ usługi w lamedb /4/ jest liczony poprawnie: 25=0x19, 31=0x1F, co chroni listy bzyk83 przed <n/a>,")
    report.append("- service reference zmieniany jest tylko przy jednoznacznym dopasowaniu po dokładnej nazwie,")
    report.append("- przy korekcie zachowywany jest lokalny service type, żeby nie zerwać EPG/piconów,")
    report.append("- nowe kanały mogą być dopisane tylko na końcu pasujących bukietów,")
    report.append("- DVB-T/DVB-C jest całkowicie pomijane i nie jest modyfikowane,")
    report.append("- usuwanie jest opcjonalne; domyślnie kanały niepewne trafiają tylko do raportu,")
    report.append("- stare podpisy/listowe reklamy są czyszczone z widoku bukietów, a podpis PP Channel Sync z datą trafia na dół listy.")
    report.append("")
    report.append("Podsumowanie:")
    report.append("- lokalny lamedb odczytany: %s" % ("tak (%s)" % os.path.basename(plan["local_db"].get("path") or "lamedb") if plan["local_db"].get("sections") else "nie - nietypowy format"))
    report.append("- sprawdzone prywatne bukiety: %d" % plan["local_user_files"])
    report.append("- sprawdzone wpisy kanałów: %d" % plan["checked"])
    report.append("- kanały zgodne z bazą po service reference: %d" % plan["same_ref"])
    report.append("- pewne korekty service reference: %d" % len(plan["ref_fixes"]))
    report.append("- aliasy service type dla zgodności EPG/piconów: %d" % len(plan.get("epg_type_aliases", [])))
    report.append("- lokalne wpisy services chronione w lamedb: %d" % plan.get("protected_local_services", 0))
    report.append("- lokalne transpondery chronione w lamedb: %d" % len(plan["transponder_updates"]))
    report.append("- nowe kanały dostępne do dopisania: %d" % plan["new_channels_available"])
    report.append("- nowe kanały zaplanowane do dopisania: %d" % plan["new_channels_added"])
    report.append("- kanały do usunięcia: %d" % plan.get("removed_count", 0))
    report.append("- kanały niepewne / tylko raport: %d" % len(plan.get("remove_candidates", [])))
    report.append("- wpisy bez nazwy/<n/a> do ręcznej kontroli: %d" % len(plan["no_name"]))
    report.append("- wpisy bez pewnego dopasowania: %d" % len(plan["unmatched"]))
    report.append("- pominięte bukiety DVB-T/DVB-C: %d" % len(plan.get("skipped_dvbt_bouquets", [])))
    report.append("- pominięte kanały DVB-T/DVB-C: %d" % plan.get("skipped_dvbt_channels", 0))
    report.append("")
    report.append("Raport szczegółowy: %s" % DETAIL_REPORT_PATH)
    report.append("Raport skrócony: %s" % REPORT_PATH)

    details.extend(report)
    details.append("\n=== Dopasowanie bukietów do dopisywania nowych kanałów ===")
    for fn, fdata in plan["files"].items():
        details.append("* %s  ->  %s" % (fdata.get("title") or os.path.basename(fn), fdata.get("remote_title") or "nie użyto"))

    if plan["ref_fixes"]:
        details.append("\n=== Pewne korekty service reference ===")
        for fix in plan["ref_fixes"]:
            details.append("* [%s] %s" % (fix.get("bouquet"), fix.get("name")))
            details.append("  stare: %s" % fix.get("old_ref"))
            details.append("  nowe: %s" % fix.get("new_ref"))

    if plan.get("epg_type_aliases"):
        details.append("\n=== Aliasy service type dla zgodności EPG/piconów ===")
        for item in plan.get("epg_type_aliases", []):
            details.append("* [%s] %s" % (item.get("bouquet"), item.get("name") or "bez nazwy"))
            details.append("  lokalny typ: %s | typ z bazy: %s" % (item.get("local_type"), item.get("remote_type")))
            details.append("  lokalny key: %s" % item.get("local_key"))
            details.append("  baza key:    %s" % item.get("remote_key"))

    if plan["service_appends"]:
        details.append("\n=== Services dopisane do lamedb / ochrona lokalna / aliasy EPG ===")
        for key, block in plan["service_appends"].items():
            details.append("* %s | %s" % (service_name_from_block(block) or key, key))

    if plan["transponder_updates"]:
        details.append("\n=== Lokalne transpondery chronione w nowym lamedb ===")
        for key in plan["transponder_updates"].keys():
            details.append("* %s" % key)

    if plan["new_channels"]:
        details.append("\n=== Nowe kanały do dopisania na końcu bukietów ===")
        for fn, items in plan["new_channels"].items():
            title = plan["files"].get(fn, {}).get("title") or os.path.basename(fn)
            details.append("\n[%s]" % title)
            for ch in items:
                details.append("+ %s | %s" % (ch.get("name"), ch.get("ref")))

    if plan.get("removed_channels"):
        details.append("\n=== Kanały do usunięcia z listy ===")
        for item in plan.get("removed_channels", []):
            details.append("- [%s] %s | %s" % (item.get("bouquet"), item.get("name"), item.get("ref")))

    if plan.get("remove_candidates"):
        details.append("\n=== Kanały niepewne / kandydaci do usunięcia, pozostawione bez zmian ===")
        for item in plan.get("remove_candidates", []):
            details.append("? [%s] %s | %s" % (item.get("bouquet"), item.get("name"), item.get("ref")))

    if plan["unmatched"]:
        details.append("\n=== Bez pewnego dopasowania, pozostawione bez zmian i zabezpieczone lokalnym lamedb jeśli możliwe ===")
        for e in plan["unmatched"]:
            details.append("* %s | %s" % (e.get("name") or "bez nazwy", e.get("ref")))

    if plan["no_name"]:
        details.append("\n=== Wpisy bez nazwy/<n/a> do ręcznej kontroli ===")
        for e in plan["no_name"]:
            details.append("* %s" % e.get("ref"))

    write_text(REPORT_PATH, "\n".join(report) + "\n")
    write_text(DETAIL_REPORT_PATH, "\n".join(details) + "\n")
    return "\n".join(report)

def normalize_block_for_compare(block):
    out = []
    for line in block or []:
        st = (line or "").strip().lower()
        if not st or st == "/":
            continue
        st = re.sub(r"\s+", " ", st)
        out.append(st)
    return out



def clean_bouquet_title(name):
    base = (name or "").strip()
    base = re.sub(r"\s*[-–—|]+\s*PP\s+Channel\s+Sync\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4}.*$", "", base, flags=re.I)
    base = re.sub(r"\b(by\s+)?(bzyk83|bzyk3|vhannibal|vannibal|hannibal|jaki\s*taki|jakitaki|anom|matzg|satvenus|e2settings)\b", "", base, flags=re.I)
    base = re.sub(r"[@©]\s*[A-Za-z0-9_. -]+$", "", base).strip()
    base = re.sub(r"[.·]{3,}\s*\d{1,2}\s+[A-Za-ząćęłńóśżź]+\s+\d{4}\s*[.·]{3,}", "", base, flags=re.I)
    base = re.sub(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", "", base)
    base = re.sub(r"\s*[-–—|,;]+\s*", " - ", base)
    base = re.sub(r"\s+", " ", base).strip(" -–—|,;")
    return base or "Lista kanałów"


def bouquet_name_from_lines(lines, fallback=""):
    for line in lines or []:
        if line.startswith("#NAME"):
            nm = line[5:].strip()
            if nm:
                return clean_bouquet_title(nm)
    return clean_bouquet_title(fallback)


def bouquet_match_key(name):
    n = normalize_basic(clean_bouquet_title(name))
    n = n.replace("+", " plus ")
    n = re.sub(r"\bpolska\b", "polskie", n)
    n = re.sub(r"\bpolish\b", "polskie", n)
    n = re.sub(r"\bcanal\s*plus\b", "canalplus", n)
    n = re.sub(r"\bcyfra\s*plus\b", "canalplus", n)
    n = re.sub(r"\bpolsat\s*box\b", "polsatbox", n)
    n = re.sub(r"\bpolsat\b", "polsatbox", n)
    n = n.replace("13.0e", "13e").replace("13,0e", "13e")
    n = re.sub(r"[^a-z0-9]+", "", n)
    return n


def bouquet_titles_similar(a, b):
    ak = bouquet_match_key(a)
    bk = bouquet_match_key(b)
    if not ak or not bk:
        return False
    if ak == bk:
        return True
    # Ostrożne mapowania najczęstszych polskich bukietów.
    synonyms = {
        "canalplus": set(["canalpluspolskie", "canalpolska", "canalpluspolska", "canal"]),
        "polskie": set(["polska", "pl", "poland"]),
        "polsatbox": set(["polsat", "cyfrowypolsat"]),
        "wiadomosci": set(["notizie", "info", "informacyjne"]),
        "filmy": set(["film", "cinema", "kino"]),
        "dzieci": set(["bambini", "kids"]),
        "muzyka": set(["musica", "music"]),
        "sport": set(["sports"]),
    }
    for k, vals in synonyms.items():
        if (ak == k and bk in vals) or (bk == k and ak in vals):
            return True
    return False


def is_credit_description(txt):
    t = normalize_basic(txt or "")
    if not t:
        return False
    if re.search(r"\b(bzyk83|bzyk3|vhannibal|vannibal|hannibal|jakitaki|jaki taki|anom|matzg|satvenus|e2settings)\b", t):
        return True
    if re.search(r"\bpp channel sync\b", t):
        return True
    if re.search(r"\b\d{1,2}\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|wrzesnia|pazdziernika|listopada|grudnia)\s+\d{4}\b", t):
        return True
    if re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", t):
        return True
    if t.startswith("@ ") or t.startswith("© "):
        return True
    return False


def is_marker_service(line):
    if not line.startswith("#SERVICE "):
        return False
    ref = line[len("#SERVICE "):].strip()
    if "FROM BOUQUET" in ref:
        return False
    parts = ref.split(":")
    if len(parts) >= 3 and norm_hex(parts[2]) in ("64", "832"):
        return True
    return False


def polish_date_stamp():
    months = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]
    try:
        return "%d %s %s" % (int(time.strftime("%d")), months[int(time.strftime("%m")) - 1], time.strftime("%Y"))
    except Exception:
        return time.strftime("%d.%m.%Y")


def clean_bouquet_name_lines(files):
    # Nie zmieniamy nazw list użytkownika. Usuwamy wyłącznie wcześniejszy dopisek PP Channel Sync,
    # jeśli starsza wersja dopisała go bezpośrednio do #NAME.
    changed = 0
    pp_suffix = re.compile(r"\s*[-–—|]+\s*PP\s+Channel\s+Sync\s+\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\s*$", re.I)
    for fn in files or []:
        try:
            lines = read_text(fn).splitlines()
            dirty = False
            for idx, line in enumerate(lines):
                if line.startswith("#NAME"):
                    old = line[5:].strip()
                    new = pp_suffix.sub("", old).strip()
                    if new and new != old:
                        lines[idx] = "#NAME %s" % new
                        dirty = True
                    break
            if dirty:
                write_text(fn, "\n".join(lines) + "\n")
                changed += 1
        except Exception:
            pass
    return changed


def update_main_bouquet_marker():
    # Aktualizuje widok list bukietów w /etc/enigma2/bouquets.tv.
    # v1.0.17: usuwa WSZYSTKIE wcześniejsze wpisy informacyjne PP Channel Sync
    # oraz stare podpisy/listowe reklamy, a na końcu dodaje tylko jeden aktualny wpis.
    path = os.path.join(E2_PATH, "bouquets.tv")
    if not os.path.isfile(path):
        return 0
    try:
        lines = read_text(path).splitlines()
    except Exception:
        return 0
    out = []
    removed = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        next_desc = ""
        if i + 1 < len(lines) and lines[i + 1].startswith("#DESCRIPTION "):
            next_desc = lines[i + 1][len("#DESCRIPTION "):].strip()

        # Prawdziwy bukiet w bouquets.tv ma FROM BOUQUET.
        # Nie wolno usuwać takiej pary nawet gdy opis zawiera PP Channel Sync,
        # bo wtedy znika wejście do osobnego bukietu „Nowe kanały”.
        if line.startswith("#SERVICE ") and "FROM BOUQUET" in line:
            out.append(line)
            if next_desc:
                out.append(lines[i + 1])
                i += 2
            else:
                i += 1
            continue

        # Standardowy blok markerowy: #SERVICE 1:64... + #DESCRIPTION ...
        if line.startswith("#SERVICE ") and next_desc:
            if is_marker_service(line) and is_credit_description(next_desc):
                removed += 1
                i += 2
                continue
            # Dodatkowe zabezpieczenie po starych wersjach: jeśli opis jest naszym podpisem,
            # kasujemy parę tylko wtedy, gdy to NIE jest wpis FROM BOUQUET.
            if "FROM BOUQUET" not in line and re.search(r"pp\s*channel\s*sync", normalize_basic(next_desc)):
                removed += 1
                i += 2
                continue

        # Osierocone opisy po nietypowych edycjach pliku.
        if line.startswith("#DESCRIPTION "):
            desc = line[len("#DESCRIPTION "):].strip()
            if is_credit_description(desc):
                removed += 1
                i += 1
                continue

        out.append(line)
        i += 1

    stamp = polish_date_stamp()
    marker = [
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:",
        "#DESCRIPTION ........ %s ........" % stamp,
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:",
        "#DESCRIPTION @ PP Channel Sync",
    ]
    out.extend(marker)
    write_text(path, "\n".join(out) + "\n")
    return removed + 1

def update_bouquet_markers(files):
    names = clean_bouquet_name_lines(files)
    marker = update_main_bouquet_marker()
    return names + marker


def _first_real_line(lines):
    for line in lines or []:
        st = (line or "").strip()
        if st and st != "/" and not st.startswith("#"):
            return st
    return ""


def local_lamedb_style(local_db):
    sections = local_db.get("sections") or {}
    header = "\n".join(sections.get("header") or []).lower()
    first_service = _first_real_line(sections.get("services") or [])
    first_transponder = _first_real_line(sections.get("transponders") or [])
    service_v5 = ("/5/" in header) or first_service.startswith("s:1:0:") or first_service.startswith("1:0:")
    service_prefix = "s" if (first_service.startswith("s:1:0:") or ("/5/" in header and not first_service.startswith("1:0:"))) else "plain"
    transponder_v5 = ("/5/" in header) or first_transponder.startswith("t:")
    return {
        "service_v5": service_v5,
        "service_prefix": service_prefix,
        "transponder_v5": transponder_v5,
    }


def convert_service_block_to_local_format(key, remote_block, local_db):
    # Tworzy blok service w formacie lokalnego lamedb, zamiast wklejać blok z bazy online 1:1.
    # To jest zabezpieczenie przed mieszaniem lamedb /4/ i /5/, które dawało <n/a>.
    parts = (key or "").split(":")
    if len(parts) != 7:
        return list(remote_block or [])
    stype, sid, tsid, onid, namespace = parts[2], parts[3], parts[4], parts[5], parts[6]
    style = local_lamedb_style(local_db)
    if style["service_v5"]:
        base_ref = "1:0:%s:%s:%s:%s:%s:0:0:0:" % (stype, sid, tsid, onid, namespace)
        first = "s:" + base_ref if style.get("service_prefix") == "s" else base_ref
    else:
        first = "%s:%s:%s:%s:%s:0:0" % (sid, namespace, tsid, onid, service_ref_type_to_lamedb_decimal(stype))
    rest = []
    for line in list(remote_block or [])[1:]:
        # Nie przenosimy końcowego separatora, jeśli jakiś nietypowy archiwizer go włożył do bloku.
        if (line or "").strip() == "/":
            continue
        rest.append(line)
    if not rest:
        rest = ["unknown", "p:unknown"]
    return [first] + rest


def convert_transponder_block_to_local_format(tkey, remote_block, local_db):
    parts = (tkey or "").split(":")
    if len(parts) != 3:
        return list(remote_block or [])
    namespace, tsid, onid = parts[0], parts[1], parts[2]
    style = local_lamedb_style(local_db)
    first = "t:%s:%s:%s" % (namespace, tsid, onid) if style["transponder_v5"] else "%s:%s:%s" % (namespace, tsid, onid)
    rest = []
    for line in list(remote_block or [])[1:]:
        st = (line or "").strip()
        if not st or st == "/":
            continue
        if style["transponder_v5"]:
            # lamedb5 zwykle używa składni s:... w parametrach transpondera.
            if st.startswith("s "):
                st = "s:" + st[2:].strip()
                rest.append(st)
            else:
                rest.append(line)
        else:
            # lamedb4 zwykle używa tabulatora i składni:  s 11488000:27500000...
            if st.startswith("s:") or st.startswith("c:") or st.startswith("t:"):
                st = st[0] + " " + st[2:]
                rest.append("\t" + st)
            elif st.startswith("s ") or st.startswith("c ") or st.startswith("t "):
                rest.append("\t" + st)
            else:
                rest.append(line)
    return [first] + rest



def write_bouquet_channel_changes(plan):
    changed_files = 0
    added_channels = 0
    ref_changes = 0
    removed_channels = 0
    for fn, fdata in plan.get("files", {}).items():
        try:
            lines = list(fdata.get("lines") or read_text(fn).splitlines())
            dirty = False
            changes = fdata.get("changes") or {}
            remove_indices = set(fdata.get("remove_indices") or [])

            for idx, new_line in changes.items():
                if idx is not None and 0 <= idx < len(lines) and idx not in remove_indices and lines[idx] != new_line:
                    lines[idx] = new_line
                    dirty = True
                    ref_changes += 1

            if remove_indices:
                new_lines = []
                for idx, line in enumerate(lines):
                    if idx in remove_indices:
                        removed_channels += 1 if line.startswith("#SERVICE ") else 0
                        dirty = True
                        continue
                    new_lines.append(line)
                lines = new_lines

            new_items = plan.get("new_channels", {}).get(fn, [])
            if new_items:
                # Dopisujemy WYŁĄCZNIE na końcu istniejącego bukietu, po separatorze.
                # Nie dublujemy kanałów, które już są w pliku.
                existing_services = set([ln.strip() for ln in lines if ln.startswith("#SERVICE ")])
                filtered = []
                for item in new_items:
                    svc = item.get("service_line") or ("#SERVICE %s" % item.get("ref"))
                    if svc.strip() in existing_services:
                        continue
                    filtered.append(item)
                    existing_services.add(svc.strip())
                if filtered:
                    lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:")
                    lines.append("#DESCRIPTION ........ nowe kanały - PP Channel Sync ........")
                    for item in filtered:
                        lines.append(item.get("service_line") or ("#SERVICE %s" % item.get("ref")))
                        lines.append(item.get("description_line") or ("#DESCRIPTION %s" % item.get("name", "")))
                        added_channels += 1
                    dirty = True
            if dirty:
                write_text(fn, "\n".join(lines) + "\n")
                changed_files += 1
        except Exception:
            pass
    return changed_files, added_channels, ref_changes, removed_channels

def rebuild_lamedb(local_db, remote_db, service_appends=None, transponder_updates=None):
    # v1.0.12: bazą zapisu jest LOKALNY lamedb użytkownika.
    # Poprzedni model: "remote lamedb + lokalne wyjątki" działał dla części list,
    # ale na listach bzyk83 usuwał autorskie aliasy usług i kończyło się masowym <n/a>.
    # Nowy model: zachowaj cały lokalny lamedb i dopisz tylko brakujące wpisy
    # wymagane przez nowe kanały albo pewne korekty service reference.
    if not local_db or not local_db.get("sections"):
        raise Exception("Nie można odczytać lokalnego lamedb. Bezpieczna korekta została zatrzymana.")
    source_path = local_db.get("path") or os.path.join(E2_PATH, "lamedb")
    sections = local_db.get("sections")
    lines = list(sections["lines"])

    local_transponders = local_db.get("transponders") or {}
    local_services = local_db.get("services") or {}

    trans_inserts = []
    for key, block in (transponder_updates or {}).items():
        if key not in local_transponders:
            trans_inserts.extend(convert_transponder_block_to_local_format(key, block, local_db))

    serv_inserts = []
    for key, block in (service_appends or {}).items():
        if key not in local_services:
            serv_inserts.extend(convert_service_block_to_local_format(key, block, local_db))

    if trans_inserts:
        insert_at = sections["trans_end"]
        lines[insert_at:insert_at] = trans_inserts
        shift = len(trans_inserts)
        serv_end = sections["serv_end"] + shift
    else:
        serv_end = sections["serv_end"]

    if serv_inserts:
        lines[serv_end:serv_end] = serv_inserts

    target = source_path if source_path else os.path.join(E2_PATH, "lamedb")
    write_text(target, "\n".join(lines) + "\n")

    # Dla obrazów, które równolegle posiadają lamedb i lamedb5, synchronizujemy drugi plik,
    # ale nie tworzymy go na siłę, jeśli go nie było.
    other = os.path.join(E2_PATH, "lamedb5") if os.path.basename(target) == "lamedb" else os.path.join(E2_PATH, "lamedb")
    if os.path.exists(other):
        try:
            shutil.copy2(target, other)
        except Exception:
            pass
    return True

def apply_plan(plan, mode):
    backup = make_backup()

    lamedb_written = rebuild_lamedb(plan["local_db"], plan["remote_db"], plan["service_appends"], plan["transponder_updates"])
    changed_files, added_channels, ref_changes, removed_channels = write_bouquet_channel_changes(plan)
    marker_updates = update_bouquet_markers(plan["files"].keys())
    reload_ok = reload_enigma_bouquets()

    result = []
    result.append("Korekta wykonana.")
    result.append("")
    result.append("Kopia: %s" % backup)
    result.append("Dogrywanie gotowych bukietów: NIE")
    result.append("Tworzenie nowych bukietów: NIE")
    result.append("Nowe kanały dopisane do istniejących bukietów: %d" % added_channels)
    result.append("Kanały usunięte z bukietów: %d (automatyczne usuwanie wyłączone)" % removed_channels)
    result.append("Bezpieczne korekty service reference: %d" % ref_changes)
    result.append("Aliasy service type dla EPG/piconów: %d" % len(plan.get("epg_type_aliases", [])))
    result.append("Lamedb zachowany lokalnie + dopisane brakujące wpisy kontrolne: %s" % ("TAK" if lamedb_written else "NIE"))
    result.append("Zmienione pliki bukietów: %d" % changed_files)
    result.append("Pominięte bukiety DVB-T/DVB-C: %d" % len(plan.get("skipped_dvbt_bouquets", [])))
    result.append("Pominięte kanały DVB-T/DVB-C: %d" % plan.get("skipped_dvbt_channels", 0))
    result.append("Wyczyszczone/podpisane informacje w widoku bukietów: %d" % marker_updates)
    result.append("Odświeżenie listy: %s" % ("OK" if reload_ok else "wymagany restart GUI"))
    result.append("")
    result.append("Raport: %s" % REPORT_PATH)
    result.append("Szczegóły: %s" % DETAIL_REPORT_PATH)
    return "\n".join(result)

def reload_enigma_bouquets():
    try:
        from enigma import eDVBDB
        db = eDVBDB.getInstance()
        db.reloadServicelist()
        db.reloadBouquets()
        return True
    except Exception:
        return False

_PPCS_AUTO_TIMER = None
_PPCS_AUTO_TIMER_CONN = None
_PPCS_SESSION = None


def _timer_start(timer, seconds):
    try:
        timer.startLongTimer(int(seconds))
    except Exception:
        try:
            timer.start(int(seconds) * 1000, True)
        except Exception:
            pass


def _should_auto_run(cfg, remote_hash=None):
    state = load_state()
    now = int(time.time())
    mode = cfg.get("auto_mode", AUTO_OFF)
    if mode == AUTO_OFF:
        return False, "auto wyłączone"
    try:
        last_run = int(state.get("last_auto_run", "0") or "0")
    except Exception:
        last_run = 0
    try:
        last_check = int(state.get("last_auto_check", "0") or "0")
    except Exception:
        last_check = 0

    if mode == AUTO_WEEKLY:
        if now - last_run >= WEEK_SECONDS:
            return True, "termin tygodniowy"
        return False, "jeszcze nie minął tydzień"

    if mode == AUTO_ON_NEW_BASE:
        if now - last_check < AUTO_INTERVAL_SECONDS:
            return False, "sprawdzano mniej niż dobę temu"
        old_hash = state.get("last_base_hash", "")
        if not old_hash:
            save_state({"last_base_hash": remote_hash or "", "last_auto_check": now})
            return False, "pierwszy zapis kontrolny bazy"
        if remote_hash and remote_hash != old_hash:
            return True, "wykryto nową bazę"
        save_state({"last_auto_check": now})
        return False, "brak nowej bazy"

    return False, "nieznany tryb"


def run_auto_update(session):
    cfg = load_settings()
    if cfg.get("auto_mode", AUTO_OFF) == AUTO_OFF:
        return
    try:
        remote = load_online_package(cfg.get("package_index", 0), cfg.get("source_index", SOURCE_STANDARD))
        run, reason = _should_auto_run(cfg, remote.get("hash"))
        if not run:
            return
        plan = build_plan(remote, None, cfg.get("add_new_mode", 1) > 0, cfg.get("remove_mode", REMOVE_REPORT))
        write_report(plan, MODE_CORRECT, None)
        result = apply_plan(plan, MODE_CORRECT)
        now = int(time.time())
        save_state({
            "last_auto_run": now,
            "last_auto_check": now,
            "last_base_hash": remote.get("hash", ""),
            "last_auto_reason": reason,
        })
        header = "by Paweł Pawełek * %s\n%s.\n\n" % (CONTACT, SUPPORT_TEXT)
        summary = header + (
            "PP Channel Sync - automatyczna aktualizacja wykonana.\n\n"
            "Powód: %s\n"
            "Nowe kanały dopisane: %d\n"
            "Kanały usunięte: %d\n"
            "Reference poprawione: %d\n"
            "Lamedb zaktualizowany: TAK\n\n"
            "Szczegóły: %s"
        ) % (reason, plan.get("new_channels_added", 0), plan.get("removed_count", 0), len(plan.get("ref_fixes", [])), DETAIL_REPORT_PATH)
        write_text(AUTO_SUMMARY_PATH, summary + "\n\n" + result + "\n")
        if session:
            session.open(MessageBox, summary, type=MessageBox.TYPE_INFO, timeout=15)
    except Exception as e:
        try:
            write_text(ERROR_PATH, "%s\n\n%s" % (str(e), traceback.format_exc()))
        except Exception:
            pass
        if session:
            session.open(MessageBox, "PP Channel Sync: błąd automatycznej aktualizacji.\n%s\n\nSzczegóły: %s" % (str(e), ERROR_PATH), type=MessageBox.TYPE_ERROR, timeout=15)


def _auto_timer_tick():
    global _PPCS_AUTO_TIMER, _PPCS_SESSION
    try:
        run_auto_update(_PPCS_SESSION)
    finally:
        if _PPCS_AUTO_TIMER is not None:
            _timer_start(_PPCS_AUTO_TIMER, AUTO_INTERVAL_SECONDS)


def start_auto_timer(session):
    global _PPCS_AUTO_TIMER, _PPCS_AUTO_TIMER_CONN, _PPCS_SESSION
    _PPCS_SESSION = session
    if _PPCS_AUTO_TIMER is not None:
        return
    try:
        from enigma import eTimer
        _PPCS_AUTO_TIMER = eTimer()
        try:
            _PPCS_AUTO_TIMER.callback.append(_auto_timer_tick)
        except Exception:
            _PPCS_AUTO_TIMER_CONN = _PPCS_AUTO_TIMER.timeout.connect(_auto_timer_tick)
        _timer_start(_PPCS_AUTO_TIMER, 180)
    except Exception:
        _PPCS_AUTO_TIMER = None


def autostart(reason, **kwargs):
    if reason == 0:
        session = kwargs.get("session")
        if session is not None:
            start_auto_timer(session)



def parse_version_tuple(value):
    parts = []
    for item in re.findall(r"\d+", str(value or "0"))[:4]:
        try:
            parts.append(int(item))
        except Exception:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(remote_version, local_version):
    return parse_version_tuple(remote_version) > parse_version_tuple(local_version)


def _manifest_value(manifest, *names):
    for name in names:
        if name in manifest and manifest.get(name):
            return manifest.get(name)
    return ""


def download_update_ipk(manifest):
    url = _manifest_value(manifest, "ipk_url", "package_url", "download_url", "url")
    if not url:
        raise Exception("Brak linku do paczki IPK w update.json.")
    dest = "/tmp/enigma2-plugin-extensions-ppchannelsync_%s_all.ipk" % _manifest_value(manifest, "version", "latest_version")
    download_url(url, dest)
    expected = _manifest_value(manifest, "sha256", "checksum", "hash")
    if expected:
        got = sha256_file(dest)
        if got.lower() != str(expected).lower():
            try:
                os.remove(dest)
            except Exception:
                pass
            raise Exception("Błędna suma SHA256 pobranej paczki.\nOczekiwano: %s\nPobrano: %s" % (expected, got))
    return dest


def install_ipk(path):
    if not os.path.isfile(path):
        raise Exception("Nie znaleziono pobranej paczki IPK: %s" % path)
    cmd = "opkg install --force-reinstall '%s'" % path.replace("'", "'\\''")
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    try:
        out = out.decode("utf-8", "ignore")
    except Exception:
        out = str(out)
    try:
        err = err.decode("utf-8", "ignore")
    except Exception:
        err = str(err)
    log = "CMD: %s\nRET: %s\n\nSTDOUT:\n%s\n\nSTDERR:\n%s\n" % (cmd, p.returncode, out, err)
    write_text(UPDATE_INFO_PATH, log)
    if p.returncode != 0:
        raise Exception("Instalacja IPK nie powiodła się. Szczegóły: %s" % UPDATE_INFO_PATH)
    return log




# ---------------------------------------------------------------------------
# PP Channel Sync v1.1.0 - rozszerzone narzędzia użytkownika
# ---------------------------------------------------------------------------

UI_MODES = [("Prosty", "Pokazuje najważniejsze funkcje dla zwykłych użytkowników."), ("Zaawansowany", "Pokazuje wszystkie narzędzia, raporty i ustawienia.")]
PROFILE_MODES = [("Bezpieczny", "Nie usuwa kanałów i wykonuje wyłącznie ostrożne poprawki."), ("Standardowy", "Poprawia listę i może dopisać nowe kanały zgodnie z ustawieniami."), ("Pełny", "Pozwala również usuwać pewne, nieaktualne pozycje. Używać ostrożnie."), ("Tylko raport", "Nie zapisuje zmian, tylko przygotowuje raport."), ("Pojedynczy bukiet", "Pracuje tylko na wybranym bukiecie.")]
YESNO_OPTIONS = [("Tak", "Włączone."), ("Nie", "Wyłączone.")]
NEW_FILTER_OPTIONS = [("Wszystkie", "Pokaż wszystkie nowe kanały."), ("Tylko FTA", "Dodawanie tylko kanałów FTA - funkcja przygotowana w trybie ostrożnym."), ("Tylko polskie", "Dodawanie tylko kanałów polskich - funkcja przygotowana w trybie ostrożnym."), ("Tylko wybrana satelita", "Dodawanie tylko z wybranego pakietu kontrolnego.")]
BOUQUET_TARGET_OPTIONS = [("Na końcu pasującego bukietu", "Nowe kanały trafią na końce pasujących bukietów."), ("Osobny bukiet Nowe kanały", "Nowe kanały trafią do osobnego bukietu PP Channel Sync - Nowe kanały."), ("Pytaj / raport", "Najpierw pokaż raport, bez automatycznego dopisywania.")]
NAME_MODE_OPTIONS = [("Zachowaj moje nazwy", "Nazwy kanałów z Twojej listy zostają bez zmian."), ("Normalizuj ręcznie", "Dostępna jest osobna funkcja czyszczenia końcówek typu podkreślenie/spacje."), ("Nazwy z bazy", "Tryb informacyjny; domyślnie nie nadpisuje nazw użytkownika.")]
OPERATOR_PROFILES = [("Automatyczny", "Wtyczka rozpoznaje bukiety po nazwie i zawartości."), ("Polska", "Ustawienia preferowane dla polskich bukietów."), ("Canal+", "Profil operatora Canal+."), ("Polsat Box", "Profil operatora Polsat Box."), ("FTA", "Profil kanałów niekodowanych.")]

_TR_EN_EXTRA = {
    "Tryb interfejsu": "Interface mode", "Profil pracy": "Work profile", "Ochrona IPTV/streamów": "Protect IPTV/streams", "Zachowaj moje nazwy kanałów": "Keep my channel names", "Filtr nowych kanałów": "New channels filter", "Miejsce nowych kanałów": "New channels target", "Profil operatora": "Operator profile",
    "Szybka naprawa listy": "Quick list repair", "Sprawdź listę i pokaż ocenę": "Check list and show status", "Aktualizuj wybrany bukiet": "Update selected bouquet", "Napraw pojedynczy kanał": "Repair single channel", "Zmień nazwę bukietu": "Rename bouquet", "Kreator nowych kanałów": "New channels wizard", "Znajdź duplikaty kanałów": "Find duplicate channels", "Szukaj kanału w liście": "Search channel in list", "Sprawdź EPG i picony": "Check EPG and picons", "Raport prosty dla użytkownika": "Simple user report", "Raport techniczny": "Technical report", "Porównaj źródła kontroli": "Compare control sources", "Ustaw typ/kategorię bukietu": "Set bouquet type/category", "Historia aktualizacji": "Update history", "Menedżer kopii bezpieczeństwa": "Backup manager", "Diagnostyka systemu": "System diagnostics", "Przygotuj raport do wysłania": "Prepare support report", "Kreator pierwszego uruchomienia": "First start wizard", "Normalizuj nazwy kanałów": "Normalize channel names",
    "Prosty": "Simple", "Zaawansowany": "Advanced", "Bezpieczny": "Safe", "Standardowy": "Standard", "Pełny": "Full", "Tylko raport": "Report only", "Pojedynczy bukiet": "Single bouquet", "Wszystkie": "All", "Tylko FTA": "FTA only", "Tylko polskie": "Polish only", "Tylko wybrana satelita": "Selected satellite only", "Na końcu pasującego bukietu": "At the end of matching bouquet", "Osobny bukiet Nowe kanały": "Separate New channels bouquet", "Pytaj / raport": "Ask / report", "Zachowaj moje nazwy": "Keep my names", "Normalizuj ręcznie": "Normalize manually", "Nazwy z bazy": "Names from database", "Automatyczny": "Automatic", "Polska": "Poland",
}

def tr2(txt):
    try:
        if _LANG == "en":
            return _TR_EN_EXTRA.get(txt, _(txt))
    except Exception:
        pass
    return _(txt)


def safe_text_line(value):
    return (value or "").replace("\r", " ").replace("\n", " ").strip()


def list_tv_bouquet_files():
    path = os.path.join(E2_PATH, "bouquets.tv")
    files = []
    if os.path.isfile(path):
        try:
            for line in read_text(path).splitlines():
                if "FROM BOUQUET" in line and "userbouquet." in line and ".tv" in line:
                    m = re.search(r'"([^"]*userbouquet\.[^"]+\.tv)"', line)
                    if m:
                        fn = os.path.basename(m.group(1))
                        full = os.path.join(E2_PATH, fn)
                        if os.path.isfile(full) and full not in files:
                            files.append(full)
        except Exception:
            pass
    if not files:
        try:
            for fn in os.listdir(E2_PATH):
                if fn.startswith("userbouquet.") and fn.endswith(".tv"):
                    files.append(os.path.join(E2_PATH, fn))
        except Exception:
            pass
    return files


def bouquet_title_from_file(fn):
    try:
        lines = read_text(fn).splitlines()
        return bouquet_name_from_lines(lines, os.path.basename(fn).replace("userbouquet.", "").replace(".tv", ""))
    except Exception:
        return os.path.basename(fn)


def is_iptv_ref(ref):
    try:
        parts = (ref or "").split(":")
        if len(parts) > 0 and parts[0] in ("4097", "5001", "5002", "8193", "8739"):
            return True
        if "%3a//" in (ref or "").lower() or "://" in (ref or "").lower():
            return True
    except Exception:
        pass
    return False


def is_sat_entry(entry):
    ref = entry.get("ref") or ""
    if is_iptv_ref(ref):
        return False
    if is_dvbt_ref(ref):
        return False
    return valid_dvb_service_ref(ref)


def filter_plan_to_files(plan, selected_files):
    selected = set(selected_files or [])
    if not selected:
        return plan
    plan = dict(plan)
    files = {}
    for k, v in (plan.get("files") or {}).items():
        if k in selected:
            files[k] = v
    plan["files"] = files
    plan["new_channels"] = dict((k, v) for k, v in (plan.get("new_channels") or {}).items() if k in selected)
    plan["selected_bouquet_mode"] = True
    return plan


def ensure_bouquet_in_main_list(filename, title):
    path = os.path.join(E2_PATH, "bouquets.tv")
    if not os.path.isfile(path):
        return False
    lines = read_text(path).splitlines()
    service_line = '#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "%s" ORDER BY bouquet' % filename
    for line in lines:
        if filename in line:
            return False
    lines.append(service_line)
    lines.append("#DESCRIPTION %s" % title)
    write_text(path, "\n".join(lines) + "\n")
    return True



def update_bouquets_tv_description(filename, new_title):
    """Aktualizuje opis bukietu w /etc/enigma2/bouquets.tv.
    To właśnie ten opis często widać w widoku list bukietów Enigma2.
    """
    path = os.path.join(E2_PATH, "bouquets.tv")
    if not os.path.isfile(path):
        return False
    base = os.path.basename(filename)
    lines = read_text(path).splitlines()
    out = []
    changed = False
    i = 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        if "FROM BOUQUET" in line and base in line:
            if i + 1 < len(lines) and lines[i + 1].startswith("#DESCRIPTION"):
                out.append("#DESCRIPTION %s" % safe_text_line(new_title))
                i += 2
                changed = True
                continue
            else:
                out.append("#DESCRIPTION %s" % safe_text_line(new_title))
                changed = True
        i += 1
    if changed:
        write_text(path, "\n".join(out) + "\n")
    return changed


def rename_bouquet_file(path, new_title):
    """Zmienia nazwę pojedynczego bukietu bez ruszania kanałów."""
    new_title = safe_text_line(new_title)
    if not new_title:
        raise Exception("Nowa nazwa bukietu jest pusta.")
    if not os.path.isfile(path):
        raise Exception("Nie znaleziono pliku bukietu.")
    make_backup()
    lines = read_text(path).splitlines()
    changed_name = False
    for i, line in enumerate(lines):
        if line.startswith("#NAME"):
            lines[i] = "#NAME %s" % new_title
            changed_name = True
            break
    if not changed_name:
        lines.insert(0, "#NAME %s" % new_title)
    write_text(path, "\n".join(lines) + "\n")
    update_bouquets_tv_description(os.path.basename(path), new_title)
    reload_enigma_bouquets()
    return True

def append_new_channels_to_separate_bouquet(plan):
    new_map = plan.get("new_channels") or {}
    items = []
    seen = set()
    for fn, arr in new_map.items():
        for item in arr:
            key = item.get("key") or service_key(item.get("ref") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(item)
    if not items:
        return 0
    fn = os.path.join(E2_PATH, "userbouquet.ppchannelsync_new.tv")
    lines = ["#NAME PP Channel Sync - Nowe kanały", "#SERVICE 1:64:0:0:0:0:0:0:0:0:", "#DESCRIPTION ........ nowe kanały - PP Channel Sync ........"]
    for item in items:
        lines.append(item.get("service_line") or ("#SERVICE %s" % item.get("ref")))
        lines.append(item.get("description_line") or ("#DESCRIPTION %s" % item.get("name", "")))
    write_text(fn, "\n".join(lines) + "\n")
    ensure_bouquet_in_main_list("userbouquet.ppchannelsync_new.tv", "PP Channel Sync - Nowe kanały")
    return len(items)


def plan_status_text(plan):
    checked = int(plan.get("checked", 0) or 0)
    fixes = len(plan.get("ref_fixes", []) or [])
    newc = int(plan.get("new_channels_added", 0) or 0)
    rem = int(plan.get("removed_count", 0) or 0)
    score = fixes + newc + rem
    status = "DOBRY"
    if score > 50:
        status = "WYMAGA KOREKTY"
    elif score > 0:
        status = "DROBNE ZMIANY"
    return "Stan listy: %s\n\nSprawdzono kanałów: %d\nDo poprawy: %d\nNowe kanały dostępne: %d\nPrawdopodobnie usunięte: %d\nPominięte DVB-T/DVB-C: %d" % (status, checked, fixes, newc, rem, len(plan.get("skipped_dvbt_bouquets", []) or []))


def write_user_friendly_report(plan, title="PP Channel Sync - raport prosty"):
    lines = []
    lines.append("by Paweł Pawełek * %s" % CONTACT)
    lines.append(SUPPORT_TEXT + ".")
    lines.append("")
    lines.append(title)
    lines.append("")
    lines.append(plan_status_text(plan))
    lines.append("")
    lines.append("Co zrobiono / co można zrobić:")
    lines.append("- gotowe bukiety nie są dogrywane")
    lines.append("- DVB-T/DVB-C oraz IPTV są chronione/pomijane")
    lines.append("- układ i kolejność obecnej listy pozostają nadrzędne")
    lines.append("")
    if plan.get("new_channels"):
        lines.append("Nowe kanały do sprawdzenia:")
        count = 0
        for fn, items in (plan.get("new_channels") or {}).items():
            lines.append("  Bukiet: %s" % bouquet_title_from_file(fn))
            for item in items[:25]:
                lines.append("    + %s" % (item.get("name") or item.get("ref") or ""))
                count += 1
            if len(items) > 25:
                lines.append("    ... oraz %d kolejnych" % (len(items) - 25))
        lines.append("")
    if plan.get("ref_fixes"):
        lines.append("Pewne korekty techniczne: %d" % len(plan.get("ref_fixes") or []))
    write_text(USER_REPORT_PATH, "\n".join(lines) + "\n")
    return USER_REPORT_PATH


def find_duplicate_channels_report():
    local_db = load_local_lamedb()
    names = local_db.get("names") or {}
    dup = {}
    total = 0
    for fn in list_tv_bouquet_files():
        title = bouquet_title_from_file(fn)
        if is_dvbt_bouquet_title(title):
            continue
        lines, entries = parse_bouquet_entries(fn, names)
        for e in entries:
            if not is_sat_entry(e):
                continue
            nm = e.get("name") or ""
            if not name_is_usable(nm):
                continue
            k = normalize_strict(nm)
            dup.setdefault(k, []).append((nm, title, e.get("ref")))
            total += 1
    out = ["by Paweł Pawełek * %s" % CONTACT, SUPPORT_TEXT + ".", "", "Duplikaty kanałów", "Sprawdzono pozycji: %d" % total, ""]
    found = 0
    for k, arr in sorted(dup.items()):
        if len(arr) > 1:
            found += 1
            out.append("%s - %d razy" % (arr[0][0], len(arr)))
            for nm, title, ref in arr[:10]:
                out.append("  - %s" % title)
            out.append("")
    if found == 0:
        out.append("Nie znaleziono oczywistych duplikatów po nazwie kanału.")
    else:
        out.insert(5, "Znaleziono grup duplikatów: %d" % found)
    write_text(DETAIL_REPORT_PATH, "\n".join(out) + "\n")
    return "Znaleziono grup duplikatów: %d\n\nSzczegóły: %s" % (found, DETAIL_REPORT_PATH)


def search_channel_report(query):
    q = normalize_basic(query or "")
    local_db = load_local_lamedb()
    names = local_db.get("names") or {}
    out = ["by Paweł Pawełek * %s" % CONTACT, SUPPORT_TEXT + ".", "", "Szukaj kanału: %s" % query, ""]
    found = 0
    for fn in list_tv_bouquet_files():
        title = bouquet_title_from_file(fn)
        lines, entries = parse_bouquet_entries(fn, names)
        pos = 0
        for e in entries:
            if not is_sat_entry(e):
                continue
            pos += 1
            nm = e.get("name") or ""
            if q and q in normalize_basic(nm):
                found += 1
                out.append("%s - %s, pozycja %d" % (nm, title, pos))
    if found == 0:
        out.append("Brak wyników.")
    write_text(DETAIL_REPORT_PATH, "\n".join(out) + "\n")
    return "Znaleziono: %d\n\nSzczegóły: %s" % (found, DETAIL_REPORT_PATH)


def possible_picon_names(ref):
    base = (ref or "").replace(":", "_").strip("_")
    return [base + ".png", base.lower() + ".png"]


def picon_dirs():
    return ["/usr/share/enigma2/picon", "/media/hdd/picon", "/media/usb/picon", "/picon"]


def check_epg_picons_report():
    local_db = load_local_lamedb()
    names = local_db.get("names") or {}
    missing_picons = []
    total = 0
    for fn in list_tv_bouquet_files():
        title = bouquet_title_from_file(fn)
        if is_dvbt_bouquet_title(title):
            continue
        lines, entries = parse_bouquet_entries(fn, names)
        for e in entries:
            if not is_sat_entry(e):
                continue
            total += 1
            ref = e.get("ref") or ""
            exists = False
            for d in picon_dirs():
                for n in possible_picon_names(ref):
                    if os.path.exists(os.path.join(d, n)):
                        exists = True
                        break
                if exists:
                    break
            if not exists:
                missing_picons.append((e.get("name") or ref, title))
    out = ["by Paweł Pawełek * %s" % CONTACT, SUPPORT_TEXT + ".", "", "Kontrola EPG i piconów", ""]
    out.append("Sprawdzono kanałów SAT: %d" % total)
    out.append("Kanały bez wykrytego piconu: %d" % len(missing_picons))
    out.append("EPG: obecność aktualnych danych EPG można w pełni ocenić tylko na tunerze podczas pracy kanału lub po imporcie EPG.")
    out.append("")
    for nm, title in missing_picons[:120]:
        out.append("- %s [%s]" % (nm, title))
    if len(missing_picons) > 120:
        out.append("... oraz %d kolejnych" % (len(missing_picons)-120))
    write_text(DETAIL_REPORT_PATH, "\n".join(out) + "\n")
    return "Sprawdzono kanałów: %d\nBrak piconów: %d\n\nSzczegóły: %s" % (total, len(missing_picons), DETAIL_REPORT_PATH)


def list_backup_files():
    arr = []
    if os.path.isdir(BACKUP_DIR):
        for fn in os.listdir(BACKUP_DIR):
            if fn.endswith(".tar.gz"):
                full = os.path.join(BACKUP_DIR, fn)
                arr.append((full, os.path.getmtime(full)))
    arr.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in arr]


def history_append(summary):
    try:
        ensure_dir(os.path.dirname(HISTORY_PATH))
        line = time.strftime("%Y-%m-%d %H:%M:%S") + " | " + safe_text_line(summary)
        old = read_text(HISTORY_PATH) if os.path.exists(HISTORY_PATH) else ""
        write_text(HISTORY_PATH, old + line + "\n")
    except Exception:
        pass


def show_history_text():
    if not os.path.isfile(HISTORY_PATH):
        return "Brak historii aktualizacji."
    txt = read_text(HISTORY_PATH)
    return txt[-4000:] if len(txt) > 4000 else txt


def system_diagnostics_report():
    lines = ["by Paweł Pawełek * %s" % CONTACT, SUPPORT_TEXT + ".", "", "Diagnostyka systemu", ""]
    try:
        import sys
        lines.append("Python: %s" % sys.version.replace("\n", " "))
    except Exception:
        pass
    for p in ["/etc/issue", "/etc/image-version"]:
        try:
            if os.path.isfile(p):
                lines.append("%s: %s" % (p, read_text(p)[:300].replace("\n", " | ")))
        except Exception:
            pass
    files = list_tv_bouquet_files()
    lines.append("Bukiety TV: %d" % len(files))
    try:
        local_db = load_local_lamedb()
        lines.append("Lamedb: %s" % (local_db.get("path") or "brak"))
        lines.append("Services w lamedb: %d" % len(local_db.get("services") or {}))
        lines.append("Transpondery w lamedb: %d" % len(local_db.get("transponders") or {}))
    except Exception as e:
        lines.append("Lamedb: błąd odczytu: %s" % str(e))
    dvbt = 0; iptv = 0; sat = 0
    try:
        names = (load_local_lamedb().get("names") or {})
        for fn in files:
            title = bouquet_title_from_file(fn)
            if is_dvbt_bouquet_title(title):
                dvbt += 1
            for e in parse_bouquet_entries(fn, names)[1]:
                if is_iptv_ref(e.get("ref")): iptv += 1
                elif is_dvbt_ref(e.get("ref")): dvbt += 1
                elif valid_dvb_service_ref(e.get("ref")): sat += 1
    except Exception:
        pass
    lines.append("Kanały SAT: %d" % sat)
    lines.append("Pozycje DVB-T/DVB-C: %d" % dvbt)
    lines.append("Pozycje IPTV/stream: %d" % iptv)
    lines.append("Backup dir: %s" % BACKUP_DIR)
    write_text(DIAGNOSTIC_PATH, "\n".join(lines) + "\n")
    return "Diagnostyka zapisana:\n%s" % DIAGNOSTIC_PATH


def export_support_zip():
    system_diagnostics_report()
    try:
        z = zipfile.ZipFile(SUPPORT_ZIP_PATH, "w", zipfile.ZIP_DEFLATED)
        for p in [REPORT_PATH, DETAIL_REPORT_PATH, USER_REPORT_PATH, DIAGNOSTIC_PATH, ERROR_PATH, HISTORY_PATH, UPDATE_INFO_PATH]:
            if os.path.isfile(p):
                z.write(p, os.path.basename(p))
        z.close()
        return SUPPORT_ZIP_PATH
    except Exception:
        raise


def normalize_channel_names_report(do_write=True):
    local_db = load_local_lamedb()
    names = local_db.get("names") or {}
    changed = 0
    details = ["by Paweł Pawełek * %s" % CONTACT, SUPPORT_TEXT + ".", "", "Normalizacja nazw kanałów", ""]
    for fn in list_tv_bouquet_files():
        try:
            title = bouquet_title_from_file(fn)
            if is_dvbt_bouquet_title(title):
                continue
            lines = read_text(fn).splitlines()
            dirty = False
            for i, line in enumerate(lines):
                if line.startswith("#DESCRIPTION "):
                    name = line[len("#DESCRIPTION "):]
                    new = re.sub(r"[_\s]+$", "", name).strip()
                    new = re.sub(r"\s+", " ", new)
                    if new and new != name and not is_credit_description(name):
                        details.append("%s: %s -> %s" % (title, name, new))
                        lines[i] = "#DESCRIPTION %s" % new
                        changed += 1
                        dirty = True
            if dirty and do_write:
                write_text(fn, "\n".join(lines) + "\n")
        except Exception:
            pass
    if changed == 0:
        details.append("Nie znaleziono nazw wymagających prostego czyszczenia.")
    write_text(DETAIL_REPORT_PATH, "\n".join(details) + "\n")
    return "Poprawione nazwy: %d\nSzczegóły: %s" % (changed, DETAIL_REPORT_PATH)


def compare_control_sources_report(package_index):
    std = load_online_package(package_index, SOURCE_STANDARD)
    alt = load_online_package(clamp_package_index(SOURCE_ALTERNATIVE, package_index), SOURCE_ALTERNATIVE)
    p1 = build_plan(std, None, True, REMOVE_REPORT)
    p2 = build_plan(alt, None, True, REMOVE_REPORT)
    out = ["by Paweł Pawełek * %s" % CONTACT, SUPPORT_TEXT + ".", "", "Porównanie źródeł kontroli", ""]
    out.append("Standard: korekty %d, nowe %d, usunięcia/kandydaci %d" % (len(p1.get("ref_fixes") or []), p1.get("new_channels_added", 0), p1.get("removed_count", 0)))
    out.append("Alternatywne: korekty %d, nowe %d, usunięcia/kandydaci %d" % (len(p2.get("ref_fixes") or []), p2.get("new_channels_added", 0), p2.get("removed_count", 0)))
    s1 = set([x.get("new_ref") or x.get("ref") or "" for x in p1.get("ref_fixes", [])])
    s2 = set([x.get("new_ref") or x.get("ref") or "" for x in p2.get("ref_fixes", [])])
    out.append("Zgodne korekty reference: %d" % len(s1.intersection(s2)))
    out.append("Różnice wymagające ręcznej kontroli: %d" % len(s1.symmetric_difference(s2)))
    write_text(DETAIL_REPORT_PATH, "\n".join(out) + "\n")
    return "Porównanie gotowe.\n\n%s" % "\n".join(out[4:])


def set_bouquet_category(title, category):
    state = load_state()
    raw = state.get("bouquet_categories", "{}")
    try:
        data = json.loads(raw)
    except Exception:
        data = {}
    data[title] = category
    save_state({"bouquet_categories": json.dumps(data)})


class PPChannelSyncScreen(Screen):
    skin = """
    <screen name="PPChannelSyncScreen" position="center,center" size="1280,720" title="PP Channel Sync">
        <eLabel position="0,0" size="1280,720" backgroundColor="#08111b" zPosition="-5" />
        <eLabel position="10,10" size="1260,700" backgroundColor="#0f1a27" zPosition="-4" />
        <eLabel position="18,18" size="1244,684" backgroundColor="#121d2b" zPosition="-3" />
        <eLabel position="18,18" size="1244,74" backgroundColor="#123a5a" zPosition="-2" />
        <eLabel position="38,130" size="755,392" backgroundColor="#071016" zPosition="-2" />
        <eLabel position="812,130" size="420,392" backgroundColor="#0c1725" zPosition="-2" />
        <eLabel position="38,550" size="1194,2" backgroundColor="#24618f" zPosition="-1" />
        <widget name="title" position="38,28" size="720,42" font="Regular;35" foregroundColor="#00c8ff" backgroundColor="#123a5a" transparent="1" zPosition="5" />
        <widget name="version" position="940,30" size="290,36" halign="right" font="Regular;28" foregroundColor="#ffffff" backgroundColor="#123a5a" transparent="1" zPosition="5" />
        <widget name="status" position="38,94" size="1190,30" font="Regular;22" foregroundColor="#ffffff" backgroundColor="#121d2b" transparent="1" zPosition="5" />
        <widget name="menu" position="52,142" size="720,365" scrollbarMode="showOnDemand" foregroundColor="#ffffff" foregroundColorSelected="#ffffff" backgroundColor="#071016" backgroundColorSelected="#1f5f95" transparent="1" zPosition="5" />
        <widget name="side_title" position="832,146" size="375,34" font="Regular;27" foregroundColor="#00c8ff" backgroundColor="#0c1725" transparent="1" zPosition="5" />
        <widget name="side_info" position="832,192" size="370,145" font="Regular;22" foregroundColor="#eeeeee" backgroundColor="#0c1725" transparent="1" zPosition="5" />
        <widget name="support_title" position="832,354" size="175,28" font="Regular;23" foregroundColor="#ffe34a" backgroundColor="#0c1725" transparent="1" zPosition="5" />
        <widget name="support_text" position="832,388" size="190,75" font="Regular;18" foregroundColor="#dddddd" backgroundColor="#0c1725" transparent="1" zPosition="5" />
        <ePixmap position="1040,348" size="150,150" pixmap="/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/qr.png" alphatest="on" zPosition="6" />
        <widget name="help" position="38,560" size="1190,30" font="Regular;21" foregroundColor="#dddddd" backgroundColor="#121d2b" transparent="1" zPosition="5" />
        <widget name="footer" position="38,596" size="1190,30" font="Regular;20" foregroundColor="#b8b8b8" backgroundColor="#121d2b" transparent="1" zPosition="5" />
        <eLabel position="38,640" size="250,44" backgroundColor="#421010" zPosition="-1" />
        <eLabel position="302,640" size="250,44" backgroundColor="#0d3818" zPosition="-1" />
        <eLabel position="566,640" size="250,44" backgroundColor="#4b3d08" zPosition="-1" />
        <eLabel position="830,640" size="250,44" backgroundColor="#0e2c5f" zPosition="-1" />
        <widget name="key_red" position="52,649" size="225,28" font="Regular;22" foregroundColor="#ff3030" backgroundColor="#421010" transparent="1" zPosition="5" />
        <widget name="key_green" position="316,649" size="225,28" font="Regular;22" foregroundColor="#25ff61" backgroundColor="#0d3818" transparent="1" zPosition="5" />
        <widget name="key_yellow" position="580,649" size="225,28" font="Regular;22" foregroundColor="#ffe34a" backgroundColor="#4b3d08" transparent="1" zPosition="5" />
        <widget name="key_blue" position="844,649" size="225,28" font="Regular;22" foregroundColor="#5aa2ff" backgroundColor="#0e2c5f" transparent="1" zPosition="5" />
    </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self.session = session
        cfg = load_settings()
        self.source_index = cfg.get("source_index", SOURCE_STANDARD)
        self.package_index = clamp_package_index(self.source_index, cfg.get("package_index", 0))
        self.mode = cfg.get("mode", MODE_CORRECT)
        self.add_new_mode = cfg.get("add_new_mode", 1)
        if self.add_new_mode >= len(ADD_NEW_MODES):
            self.add_new_mode = 1
        self.remove_mode = cfg.get("remove_mode", REMOVE_REPORT)
        self.auto_mode = cfg.get("auto_mode", AUTO_OFF)
        self.ui_mode = cfg.get("ui_mode", 1)
        self.profile_mode = cfg.get("profile_mode", 1)
        self.skip_iptv = cfg.get("skip_iptv", 0)
        self.keep_names = cfg.get("keep_names", 0)
        self.new_filter = cfg.get("new_filter", 0)
        self.new_target = cfg.get("new_target", 0)
        self.name_mode = cfg.get("name_mode", 0)
        self.operator_profile = cfg.get("operator_profile", 0)
        self.match_mode = MATCH_SAFE
        self.last_remote = None
        self.last_plan = None
        self["title"] = Label("PP Channel Sync")
        try:
            self.setTitle("PP Channel Sync v%s" % PLUGIN_VERSION)
        except Exception:
            pass
        self["version"] = Label("v%s" % PLUGIN_VERSION)
        self["status"] = Label(tr2("OK wykonuje funkcję z listy, a zielony przycisk uruchamia ustawione zadanie korekty listy"))
        self["side_title"] = Label(tr2("Informacje"))
        self["side_info"] = Label("")
        self["support_title"] = Label(tr2("Wesprzyj"))
        self["support_text"] = Label(tr2("Pomóż rozwijać\nlokalne projekty"))
        self["help"] = Label(tr2("OK - opcja / funkcja  |  Zielony - korekta listy  |  MENU - raport  |  EXIT - wyjście"))
        self["footer"] = Label("%s  •  %s  •  Enigma2 Python 2/3  •  FB: Enigma 2 Oprogramowanie, dodatki" % (AUTHOR, CONTACT))
        self["key_red"] = Label(tr2("Czerwony: wyjście"))
        self["key_green"] = Label(tr2("Zielony: korekta listy"))
        self["key_yellow"] = Label(tr2("Żółty: kopia"))
        self["key_blue"] = Label(tr2("Niebieski: przywróć"))
        self["menu"] = MenuList([])
        try:
            from enigma import gFont
            self["menu"].l.setFont(0, gFont("Regular", 25))
            self["menu"].l.setItemHeight(38)
        except Exception:
            pass
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
            "ok": self.ok, "cancel": self.close, "red": self.close, "green": self.run_green_mode,
            "yellow": self.backup_now, "blue": self.restore_last, "left": self.left, "right": self.right,
            "menu": self.show_last_report, "up": self.up, "down": self.down,
        }, -1)
        self.refresh_menu()
        try:
            self.onLayoutFinish.append(self.refresh_menu)
        except Exception:
            pass

    def setting_items(self):
        packages = packages_for_source(self.source_index)
        self.package_index = clamp_package_index(self.source_index, self.package_index)
        return [
            ("setting", "ui_mode", "%s: %s" % (tr2("Tryb interfejsu"), tr2(UI_MODES[self.ui_mode][0])), UI_MODES[self.ui_mode][1]),
            ("setting", "profile_mode", "%s: %s" % (tr2("Profil pracy"), tr2(PROFILE_MODES[self.profile_mode][0])), PROFILE_MODES[self.profile_mode][1]),
            ("setting", "source_index", "%s:  %s" % (tr2("Źródło kontroli"), tr2(SOURCE_OPTIONS[self.source_index][0])), SOURCE_OPTIONS[self.source_index][1]),
            ("setting", "package_index", "%s:  %s" % (tr2("Pakiet kontrolny"), packages[self.package_index][0]), tr2("Wybierz zakres kontroli zgodny z listą, którą masz na tunerze.\n\nPakiet służy tylko jako punkt porównania.")),
            ("setting", "mode", "%s: %s" % (tr2("Tryb pracy zielonego"), tr2(SYNC_MODES[self.mode][0])), SYNC_MODES[self.mode][1]),
            ("setting", "add_new_mode", "%s: %s" % (tr2("Dopisywanie nowych kanałów"), tr2(ADD_NEW_MODES[self.add_new_mode][0])), ADD_NEW_MODES[self.add_new_mode][1]),
            ("setting", "remove_mode", "%s: %s" % (tr2("Usuwanie nieaktualnych kanałów"), tr2(REMOVE_MODES[self.remove_mode][0])), REMOVE_MODES[self.remove_mode][1]),
            ("setting", "auto_mode", "%s: %s" % (tr2("Automatyczna aktualizacja"), tr2(AUTO_UPDATE_MODES[self.auto_mode][0])), AUTO_UPDATE_MODES[self.auto_mode][1]),
            ("setting", "skip_iptv", "%s: %s" % (tr2("Ochrona IPTV/streamów"), tr2(YESNO_OPTIONS[self.skip_iptv][0])), "Domyślnie wtyczka pomija streamy IPTV/4097/5001/5002."),
            ("setting", "keep_names", "%s: %s" % (tr2("Zachowaj moje nazwy kanałów"), tr2(YESNO_OPTIONS[self.keep_names][0])), "Wtyczka nie nadpisuje nazw kanałów użytkownika. Normalizacja jest osobną funkcją."),
            ("setting", "new_filter", "%s: %s" % (tr2("Filtr nowych kanałów"), tr2(NEW_FILTER_OPTIONS[self.new_filter][0])), NEW_FILTER_OPTIONS[self.new_filter][1]),
            ("setting", "new_target", "%s: %s" % (tr2("Miejsce nowych kanałów"), tr2(BOUQUET_TARGET_OPTIONS[self.new_target][0])), BOUQUET_TARGET_OPTIONS[self.new_target][1]),
            ("setting", "name_mode", "%s: %s" % (tr2("Zachowaj moje nazwy kanałów"), tr2(NAME_MODE_OPTIONS[self.name_mode][0])), NAME_MODE_OPTIONS[self.name_mode][1]),
            ("setting", "operator_profile", "%s: %s" % (tr2("Profil operatora"), tr2(OPERATOR_PROFILES[self.operator_profile][0])), OPERATOR_PROFILES[self.operator_profile][1]),
        ]

    def action_items(self):
        return [
            ("action", "quick", tr2("Szybka naprawa listy"), "Jedno kliknięcie: kopia, bezpieczna korekta, raport. Nie rusza DVB-T/DVB-C/IPTV."),
            ("action", "status", tr2("Sprawdź listę i pokaż ocenę"), "Pokazuje prostą ocenę stanu listy: dobra, drobne zmiany albo wymaga korekty."),
            ("action", "single_bouquet", tr2("Aktualizuj wybrany bukiet"), "Wybierz jeden bukiet. Wtyczka pracuje tylko na nim i nie rusza reszty listy."),
            ("action", "single_channel", tr2("Napraw pojedynczy kanał"), "Najpierw wybierz bukiet, potem kanał. Wtyczka sprawdzi tylko tę jedną pozycję."),
            ("action", "rename_bouquet", tr2("Zmień nazwę bukietu"), "Zmienia nazwę wybranego bukietu bez ruszania kanałów i kolejności."),
            ("action", "new_wizard", tr2("Kreator nowych kanałów"), "Pokazuje kanały, które można dopisać. Można je dodać na końcu bukietu albo do osobnego bukietu."),
            ("action", "duplicates", tr2("Znajdź duplikaty kanałów"), "Raportuje kanały występujące kilka razy w listach."),
            ("action", "search", tr2("Szukaj kanału w liście"), "Wyszukuje kanał i pokazuje, w jakich bukietach oraz pozycjach występuje."),
            ("action", "epg_picons", tr2("Sprawdź EPG i picony"), "Sprawdza picony i przygotowuje raport kanałów wymagających kontroli EPG/piconów."),
            ("action", "simple_report", tr2("Raport prosty dla użytkownika"), "Krótki raport bez technicznych szczegółów."),
            ("action", "tech_report", tr2("Raport techniczny"), "Szczegółowy raport dla autora lub zaawansowanych użytkowników."),
            ("action", "compare_sources", tr2("Porównaj źródła kontroli"), "Porównuje wynik źródła Standard i Alternatywne."),
            ("action", "tag_bouquet", tr2("Ustaw typ/kategorię bukietu"), "Ręczne przypisanie kategorii bukietu: Polska, Canal+, Polsat, Sport, FTA itd."),
            ("action", "history", tr2("Historia aktualizacji"), "Pokazuje ostatnie działania wtyczki."),
            ("action", "backup_manager", tr2("Menedżer kopii bezpieczeństwa"), "Lista kopii z możliwością przywrócenia wybranej kopii."),
            ("action", "diagnostics", tr2("Diagnostyka systemu"), "Zbiera informacje o systemie, Pythonie, lamedb i liczbie kanałów."),
            ("action", "support_zip", tr2("Przygotuj raport do wysłania"), "Tworzy ZIP z raportami i diagnostyką do wysłania autorowi."),
            ("action", "first_wizard", tr2("Kreator pierwszego uruchomienia"), "Krótki przewodnik dla początkujących."),
            ("action", "normalize_names", tr2("Normalizuj nazwy kanałów"), "Czyści końcowe podkreślenia, podwójne spacje i proste śmieci w opisach kanałów."),
            ("action", "backup_now", tr2("Utwórz kopię bezpieczeństwa teraz"), "Tworzy kopię lamedb, lamedb5, bouquets.tv i wszystkich userbouquet.*.tv."),
            ("action", "restore_last", tr2("Przywróć ostatnią kopię bezpieczeństwa"), "Przywraca ostatnią kopię wykonaną przez PP Channel Sync."),
            ("action", "update_plugin", tr2("Aktualizuj wtyczkę z GitHub"), "Sprawdza update.json na GitHub i instaluje nowszą wersję wtyczki."),
            ("action", "info", tr2("Informacje o działaniu wtyczki"), "Informacje o działaniu, bezpieczeństwie i autorze."),
        ]

    def menu_data(self):
        items = []
        if self.ui_mode == 0:
            items.extend([self.setting_items()[0], self.setting_items()[1], self.setting_items()[2], self.setting_items()[3], self.setting_items()[5], self.setting_items()[7]])
            simple_keys = set(["quick", "status", "single_bouquet", "rename_bouquet", "new_wizard", "duplicates", "epg_picons", "backup_manager", "restore_last", "update_plugin", "info"])
            items.extend([x for x in self.action_items() if x[1] in simple_keys])
        else:
            items.extend(self.setting_items())
            items.extend(self.action_items())
        return items

    def menu_items(self):
        return [item[2] for item in self.menu_data()]

    def refresh_menu(self):
        self._menu_data = self.menu_data()
        self["menu"].setList([x[2] for x in self._menu_data])
        self.update_side_info()

    def selected_index(self):
        try:
            return self["menu"].getCurrentIndex()
        except Exception:
            pass
        try:
            return self["menu"].l.getCurrentSelectionIndex()
        except Exception:
            pass
        try:
            current = self["menu"].getCurrent()
            return self["menu"].list.index(current)
        except Exception:
            return 0

    def current_item(self):
        data = getattr(self, "_menu_data", self.menu_data())
        idx = self.selected_index()
        if idx < 0 or idx >= len(data):
            return data[0]
        return data[idx]

    def update_side_info(self):
        item = self.current_item()
        self["side_title"].setText(tr2("Opis opcji"))
        self["side_info"].setText(tr2(item[3]) if len(item) > 3 else "")

    def save_current_settings(self):
        save_settings({"source_index": self.source_index, "package_index": self.package_index, "mode": self.mode, "add_new_mode": self.add_new_mode, "remove_mode": self.remove_mode, "auto_mode": self.auto_mode, "ui_mode": self.ui_mode, "profile_mode": self.profile_mode, "skip_iptv": self.skip_iptv, "keep_names": self.keep_names, "new_filter": self.new_filter, "new_target": self.new_target, "name_mode": self.name_mode, "operator_profile": self.operator_profile})

    def cycle_setting(self, direction):
        item = self.current_item()
        if item[0] != "setting":
            return False
        key = item[1]
        if key == "ui_mode": self.ui_mode = (self.ui_mode + direction) % len(UI_MODES)
        elif key == "profile_mode": self.profile_mode = (self.profile_mode + direction) % len(PROFILE_MODES)
        elif key == "source_index":
            self.source_index = (self.source_index + direction) % len(SOURCE_OPTIONS)
            self.package_index = clamp_package_index(self.source_index, self.package_index)
        elif key == "package_index":
            packages = packages_for_source(self.source_index)
            self.package_index = (self.package_index + direction) % len(packages)
        elif key == "mode": self.mode = (self.mode + direction) % len(SYNC_MODES)
        elif key == "add_new_mode": self.add_new_mode = (self.add_new_mode + direction) % len(ADD_NEW_MODES)
        elif key == "remove_mode": self.remove_mode = (self.remove_mode + direction) % len(REMOVE_MODES)
        elif key == "auto_mode": self.auto_mode = (self.auto_mode + direction) % len(AUTO_UPDATE_MODES)
        elif key == "skip_iptv": self.skip_iptv = (self.skip_iptv + direction) % len(YESNO_OPTIONS)
        elif key == "keep_names": self.keep_names = (self.keep_names + direction) % len(YESNO_OPTIONS)
        elif key == "new_filter": self.new_filter = (self.new_filter + direction) % len(NEW_FILTER_OPTIONS)
        elif key == "new_target":
            self.new_target = (self.new_target + direction) % len(BOUQUET_TARGET_OPTIONS)
            self.add_new_mode = 2 if self.new_target == 1 else (0 if self.new_target == 2 else 1)
        elif key == "name_mode": self.name_mode = (self.name_mode + direction) % len(NAME_MODE_OPTIONS)
        elif key == "operator_profile": self.operator_profile = (self.operator_profile + direction) % len(OPERATOR_PROFILES)
        self.save_current_settings()
        self.refresh_menu()
        return True

    def up(self):
        self["menu"].up(); self.update_side_info()
    def down(self):
        self["menu"].down(); self.update_side_info()
    def left(self):
        if not self.cycle_setting(-1):
            self.update_side_info()
    def right(self):
        if not self.cycle_setting(1):
            self.update_side_info()
    def ok(self):
        item = self.current_item()
        if item[0] == "setting":
            self.right()
        else:
            self.run_current()

    def run_green_mode(self):
        # Zielony przycisk wykonuje wyłącznie ustawione zadanie korekty/sprawdzenia listy.
        # Najpierw aktualizujemy status i dopiero po krótkiej chwili startujemy pracę,
        # żeby użytkownik widział, że przycisk został przyjęty.
        try:
            self["status"].setText(tr2("Trwa wykonywanie zadania listy. Proszę czekać..."))
        except Exception:
            pass
        try:
            from enigma import eTimer
            self._green_timer = eTimer()
            try:
                self._green_timer.callback.append(self._run_green_mode_delayed)
            except Exception:
                self._green_timer_conn = self._green_timer.timeout.connect(self._run_green_mode_delayed)
            try:
                self._green_timer.start(250, True)
            except Exception:
                self._green_timer.startLongTimer(1)
        except Exception:
            self._run_green_mode_delayed()

    def _run_green_mode_delayed(self):
        try:
            if self.mode == MODE_REPORT:
                self.check_changes()
            else:
                self.apply_update()
        except Exception as e:
            try:
                write_text(ERROR_PATH, "%s\n\n%s" % (str(e), traceback.format_exc()))
            except Exception:
                pass
            try:
                self["status"].setText(tr2("Błąd zadania listy. Szczegóły w raporcie błędu."))
            except Exception:
                pass

    def run_current(self):
        item = self.current_item()
        if item[0] == "setting":
            self.right()
            return
        name = item[1]
        if name == "quick": self.quick_repair()
        elif name == "status": self.check_status()
        elif name == "single_bouquet": self.choose_bouquet_for_update()
        elif name == "single_channel": self.choose_bouquet_for_channel()
        elif name == "rename_bouquet": self.rename_bouquet()
        elif name == "new_wizard": self.new_channels_wizard()
        elif name == "duplicates": self.find_duplicates()
        elif name == "search": self.search_channel()
        elif name == "epg_picons": self.check_epg_picons()
        elif name == "simple_report": self.show_user_report()
        elif name == "tech_report": self.show_detail_report()
        elif name == "compare_sources": self.compare_sources()
        elif name == "tag_bouquet": self.tag_bouquet()
        elif name == "history": self.show_history()
        elif name == "backup_manager": self.backup_manager()
        elif name == "diagnostics": self.diagnostics()
        elif name == "support_zip": self.prepare_support_zip()
        elif name == "first_wizard": self.first_wizard()
        elif name == "normalize_names": self.normalize_names()
        elif name == "backup_now": self.backup_now()
        elif name == "restore_last": self.restore_last()
        elif name == "update_plugin": self.update_plugin_from_github()
        elif name == "info": self.info()

    def popup(self, text, mtype=MessageBox.TYPE_INFO, timeout=0):
        # Nie każdy obraz Enigma2 pozwala otwierać MessageBox z każdego kontekstu
        # (np. po zadaniu uruchomionym z timerem). Dlatego popup jest bezpieczny:
        # jeśli MessageBox nie może zostać otwarty, nie powodujemy GSOD, tylko
        # zapisujemy komunikat do raportu i pokazujemy skrót w pasku statusu.
        try:
            self.session.open(MessageBox, text, type=mtype, timeout=timeout)
        except Exception:
            try:
                write_text(ERROR_PATH, str(text) + "\n")
            except Exception:
                pass
            try:
                short = str(text).replace("\n", " ")
                if len(short) > 120:
                    short = short[:117] + "..."
                self["status"].setText(short)
            except Exception:
                pass

    def prepare_plan(self, single_files=None, force_report=False):
        remote = load_online_package(self.package_index, self.source_index)
        add_new = self.add_new_mode > 0
        if self.new_target == 2:
            add_new = False
        # Wersja 1.2.0: zielona korekta nie usuwa automatycznie istniejących kanałów.
        # Kandydaci do usunięcia trafiają wyłącznie do raportu. Usuwanie poprawnych pozycji
        # było głównym źródłem problemów na listach autorskich, więc jest twardo wyłączone
        # dla automatycznej korekty.
        remove_mode = REMOVE_REPORT
        if force_report:
            remove_mode = REMOVE_REPORT
        plan = build_plan(remote, None, add_new, remove_mode)
        plan["new_channels_mode"] = self.add_new_mode
        plan["new_filter"] = self.new_filter
        if single_files:
            plan = filter_plan_to_files(plan, single_files)
            plan["new_channels_mode"] = self.add_new_mode
        self.last_remote = remote
        self.last_plan = plan
        return plan

    def check_changes(self):
        try:
            self["status"].setText("Pobieranie bazy i kontrola Twojej listy...")
            plan = self.prepare_plan(force_report=True)
            write_report(plan, MODE_REPORT, None)
            write_user_friendly_report(plan)
            self["status"].setText("Raport gotowy: %s" % REPORT_PATH)
            self.popup("Analiza zakończona.\n\n" + plan_status_text(plan) + "\n\nRaport: %s\nRaport prosty: %s" % (REPORT_PATH, USER_REPORT_PATH))
        except Exception as e:
            self["status"].setText("Błąd analizy")
            self.popup("Nie mogę bezpiecznie odczytać lub sprawdzić listy. Lista nie została zmieniona.\n\n%s" % str(e), MessageBox.TYPE_ERROR)

    def apply_update(self):
        try:
            if self.mode == MODE_REPORT or self.profile_mode == 3:
                self.check_changes(); return
            plan = self.last_plan or self.prepare_plan()
            plan["new_channels_mode"] = self.add_new_mode
            self["status"].setText("Wykonywanie korekty posiadanej listy...")
            write_report(plan, MODE_CORRECT, None)
            write_user_friendly_report(plan)
            result = apply_plan(plan, MODE_CORRECT)
            self["status"].setText("Korekta zakończona")
            self.popup(result)
        except Exception as e:
            self["status"].setText("Błąd korekty")
            err = "%s\n\n%s" % (str(e), traceback.format_exc())
            try: write_text(ERROR_PATH, err)
            except Exception: pass
            self.popup("Nie mogę bezpiecznie wykonać korekty. Lista nie powinna zostać zmieniona bez kopii.\n\n%s\n\nSzczegóły: %s" % (str(e), ERROR_PATH), MessageBox.TYPE_ERROR)

    def quick_repair(self):
        old_remove = self.remove_mode
        old_mode = self.mode
        self.remove_mode = REMOVE_REPORT
        self.mode = MODE_CORRECT
        try:
            self.apply_update()
        finally:
            self.remove_mode = old_remove
            self.mode = old_mode
            self.save_current_settings()

    def check_status(self):
        try:
            plan = self.prepare_plan(force_report=True)
            write_report(plan, MODE_REPORT, None)
            write_user_friendly_report(plan)
            self.popup(plan_status_text(plan) + "\n\nRaport prosty: %s" % USER_REPORT_PATH)
        except Exception as e:
            self.popup("Błąd sprawdzania listy:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def choose_bouquet_for_update(self):
        choices = [(bouquet_title_from_file(fn), fn) for fn in list_tv_bouquet_files() if not is_dvbt_bouquet_title(bouquet_title_from_file(fn))]
        if not choices:
            self.popup("Nie znaleziono bukietów SAT do aktualizacji.", MessageBox.TYPE_ERROR); return
        try:
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(self._bouquet_update_selected, ChoiceBox, title="Wybierz bukiet do aktualizacji", list=choices)
        except Exception:
            self._bouquet_update_selected(choices[0])

    def _bouquet_update_selected(self, choice):
        if not choice: return
        title, fn = choice
        try:
            plan = self.prepare_plan([fn])
            write_report(plan, self.mode, None)
            write_user_friendly_report(plan, "PP Channel Sync - raport bukietu %s" % title)
            if self.mode == MODE_REPORT:
                self.popup("Raport bukietu gotowy.\n\n%s\n\n%s" % (title, plan_status_text(plan)))
                return
            result = apply_plan(plan, MODE_CORRECT)
            self.popup("Zaktualizowano wybrany bukiet:\n%s\n\n%s" % (title, result))
        except Exception as e:
            self.popup("Błąd aktualizacji bukietu %s:\n%s" % (title, str(e)), MessageBox.TYPE_ERROR)

    def choose_bouquet_for_channel(self):
        choices = [(bouquet_title_from_file(fn), fn) for fn in list_tv_bouquet_files() if not is_dvbt_bouquet_title(bouquet_title_from_file(fn))]
        if not choices:
            self.popup("Brak bukietów SAT."); return
        try:
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(self._channel_bouquet_selected, ChoiceBox, title="1/2 Wybierz bukiet", list=choices)
        except Exception:
            self._channel_bouquet_selected(choices[0])

    def _channel_bouquet_selected(self, choice):
        if not choice: return
        title, fn = choice
        try:
            names = load_local_lamedb().get("names") or {}
            entries = [e for e in parse_bouquet_entries(fn, names)[1] if is_sat_entry(e) and name_is_usable(e.get("name"))]
            choices = [(e.get("name"), e) for e in entries]
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(lambda ch: self._repair_channel_selected(fn, title, ch), ChoiceBox, title="2/2 Wybierz kanał", list=choices)
        except Exception as e:
            self.popup("Nie udało się wczytać kanałów:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def _repair_channel_selected(self, fn, title, choice):
        if not choice: return
        name, entry = choice
        try:
            plan = self.prepare_plan([fn])
            # Zostaw tylko linie dotyczące wybranego indeksu; lamedb appends zostają jako ochrona.
            fdata = plan.get("files", {}).get(fn)
            if fdata:
                changes = fdata.get("changes") or {}
                fdata["changes"] = dict((k, v) for k, v in changes.items() if k == entry.get("service_index"))
                plan["new_channels"] = {}
                plan["removed_count"] = 0
            write_report(plan, MODE_CORRECT, None)
            if self.mode == MODE_REPORT:
                self.popup("Raport dla kanału:\n%s\n\n%s" % (name, DETAIL_REPORT_PATH)); return
            result = apply_plan(plan, MODE_CORRECT)
            self.popup("Kanał sprawdzony/naprawiony:\n%s\n\n%s" % (name, result))
        except Exception as e:
            self.popup("Błąd naprawy kanału %s:\n%s" % (name, str(e)), MessageBox.TYPE_ERROR)

    def new_channels_wizard(self):
        try:
            plan = self.prepare_plan(force_report=True)
            count = plan.get("new_channels_added", 0)
            write_user_friendly_report(plan, "PP Channel Sync - kreator nowych kanałów")
            msg = "Znaleziono nowych kanałów: %d\n\nMiejsce dodania: %s\n\nTryb korekty może je dopisać zgodnie z ustawieniami.\nRaport: %s" % (count, BOUQUET_TARGET_OPTIONS[self.new_target][0], USER_REPORT_PATH)
            self.popup(msg)
        except Exception as e:
            self.popup("Błąd kreatora nowych kanałów:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def find_duplicates(self):
        try: self.popup(find_duplicate_channels_report())
        except Exception as e: self.popup("Błąd duplikatów:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def search_channel(self):
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._search_channel_text, VirtualKeyBoard, title="Szukaj kanału", text="")
        except Exception:
            self._search_channel_text("TVN")
    def _search_channel_text(self, text):
        if not text: return
        try: self.popup(search_channel_report(text))
        except Exception as e: self.popup("Błąd wyszukiwania:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def check_epg_picons(self):
        try: self.popup(check_epg_picons_report())
        except Exception as e: self.popup("Błąd kontroli EPG/piconów:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def show_user_report(self):
        if not os.path.isfile(USER_REPORT_PATH):
            try:
                plan = self.prepare_plan(force_report=True)
                write_user_friendly_report(plan)
            except Exception: pass
        if not os.path.isfile(USER_REPORT_PATH):
            self.popup("Brak raportu prostego."); return
        text = read_text(USER_REPORT_PATH)
        if len(text) > 5200: text = text[:5200] + "\n\n...\nPełny raport: %s" % USER_REPORT_PATH
        self.popup(text)

    def show_last_report(self):
        if not os.path.isfile(REPORT_PATH):
            self.popup("Brak raportu. Wybierz sprawdzenie listy albo raport prosty."); return
        text = read_text(REPORT_PATH)
        if len(text) > 4200: text = text[:4200] + "\n\n...\nPełny raport: %s" % REPORT_PATH
        self.popup(text)

    def show_detail_report(self):
        if not os.path.isfile(DETAIL_REPORT_PATH):
            self.popup("Brak raportu szczegółowego."); return
        text = read_text(DETAIL_REPORT_PATH)
        if len(text) > 5200: text = text[:5200] + "\n\n...\nPełny raport szczegółowy: %s" % DETAIL_REPORT_PATH
        self.popup(text)

    def compare_sources(self):
        try: self.popup(compare_control_sources_report(self.package_index))
        except Exception as e: self.popup("Błąd porównania źródeł:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def tag_bouquet(self):
        choices = [(bouquet_title_from_file(fn), fn) for fn in list_tv_bouquet_files()]
        if not choices: self.popup("Brak bukietów."); return
        try:
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(self._tag_bouquet_selected, ChoiceBox, title="Wybierz bukiet", list=choices)
        except Exception:
            self._tag_bouquet_selected(choices[0])
    def _tag_bouquet_selected(self, choice):
        if not choice: return
        title, fn = choice
        cats = [(x, x) for x in ["Polska", "Canal+", "Polsat Box", "Sport", "Filmy", "Dzieci", "FTA", "Muzyka", "Informacje", "Inne"]]
        try:
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(lambda c: self._category_selected(title, c), ChoiceBox, title="Wybierz typ bukietu", list=cats)
        except Exception:
            self._category_selected(title, cats[0])
    def _category_selected(self, title, choice):
        if not choice: return
        set_bouquet_category(title, choice[1])
        self.popup("Zapisano kategorię bukietu:\n%s -> %s" % (title, choice[1]))

    def rename_bouquet(self):
        choices = [(bouquet_title_from_file(fn), fn) for fn in list_tv_bouquet_files()]
        if not choices:
            self.popup("Brak bukietów do zmiany nazwy."); return
        try:
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(self._rename_bouquet_selected, ChoiceBox, title="Wybierz bukiet do zmiany nazwy", list=choices)
        except Exception:
            self._rename_bouquet_selected(choices[0])

    def _rename_bouquet_selected(self, choice):
        if not choice: return
        title, fn = choice
        self._rename_target = (title, fn)
        try:
            from Screens.VirtualKeyBoard import VirtualKeyBoard
            self.session.openWithCallback(self._rename_bouquet_text_entered, VirtualKeyBoard, title="Nowa nazwa bukietu", text=title)
        except Exception:
            try:
                from Screens.InputBox import InputBox
                self.session.openWithCallback(self._rename_bouquet_text_entered, InputBox, title="Nowa nazwa bukietu", text=title)
            except Exception:
                self.popup("Na tym obrazie nie znaleziono klawiatury ekranowej. Zmiana nazwy bukietu nie została wykonana.", MessageBox.TYPE_ERROR)

    def _rename_bouquet_text_entered(self, new_title):
        if not new_title: return
        old_title, fn = getattr(self, "_rename_target", ("", ""))
        try:
            rename_bouquet_file(fn, new_title)
            history_append("Zmieniono nazwę bukietu: %s -> %s" % (old_title, new_title))
            self.popup("Zmieniono nazwę bukietu:\n%s\n\nna:\n%s" % (old_title, new_title))
        except Exception as e:
            self.popup("Błąd zmiany nazwy bukietu:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def show_history(self):
        self.popup(show_history_text())

    def backup_manager(self):
        b = list_backup_files()
        if not b: self.popup("Brak kopii bezpieczeństwa."); return
        choices = [(os.path.basename(x), x) for x in b[:30]]
        try:
            from Screens.ChoiceBox import ChoiceBox
            self.session.openWithCallback(self._backup_selected, ChoiceBox, title="Wybierz kopię do przywrócenia", list=choices)
        except Exception:
            self._backup_selected(choices[0])
    def _backup_selected(self, choice):
        if not choice: return
        name, path = choice
        try:
            restore_backup(path)
            self.popup("Przywrócono kopię:\n%s" % path)
        except Exception as e:
            self.popup("Nie udało się przywrócić kopii:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def diagnostics(self):
        try: self.popup(system_diagnostics_report())
        except Exception as e: self.popup("Błąd diagnostyki:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def prepare_support_zip(self):
        try: self.popup("Raport do wysłania przygotowany:\n%s" % export_support_zip())
        except Exception as e: self.popup("Błąd tworzenia ZIP:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def first_wizard(self):
        text = "PP Channel Sync - kreator\n\n1. Zacznij od 'Sprawdź listę i pokaż ocenę'.\n2. Jeśli wynik jest dobry lub drobne zmiany, użyj 'Szybka naprawa listy'.\n3. Jeśli boisz się ruszać całą listę, wybierz 'Aktualizuj wybrany bukiet'.\n4. Nowe kanały znajdziesz na końcu pasujących bukietów albo w osobnym bukiecie, zależnie od ustawień.\n5. DVB-T/DVB-C i IPTV są chronione.\n\nŻółty przycisk tworzy kopię, niebieski ją przywraca."
        self.popup(text)

    def normalize_names(self):
        self.session.openWithCallback(self._normalize_confirm, MessageBox, "Wyczyścić proste końcówki nazw kanałów, np. TVN HD_ -> TVN HD?\n\nWtyczka zrobi tylko proste czyszczenie opisów #DESCRIPTION.", type=MessageBox.TYPE_YESNO, default=False)
    def _normalize_confirm(self, answer):
        if not answer: return
        try:
            make_backup()
            self.popup(normalize_channel_names_report(True))
        except Exception as e:
            self.popup("Błąd normalizacji nazw:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def backup_now(self):
        try:
            backup = make_backup(); self.popup("Kopia bezpieczeństwa utworzona:\n%s" % backup)
        except Exception as e:
            self.popup("Nie udało się utworzyć kopii:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def restore_last(self):
        try:
            b = latest_backup()
            if not b: self.popup("Brak kopii bezpieczeństwa.", MessageBox.TYPE_ERROR); return
            restore_backup(b); self.popup("Przywrócono ostatnią kopię:\n%s" % b)
        except Exception as e:
            self.popup("Nie udało się przywrócić kopii:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def update_plugin_from_github(self):
        try:
            self["status"].setText("Sprawdzanie aktualizacji z GitHub...")
            manifest = fetch_json(UPDATE_MANIFEST_URL)
            remote_version = _manifest_value(manifest, "version", "latest_version")
            notes = manifest.get("notes", "")
            if isinstance(notes, list): notes = "\n".join(["- " + str(x) for x in notes])
            if not remote_version: raise Exception("Plik update.json nie zawiera pola version.")
            if not is_newer_version(remote_version, PLUGIN_VERSION):
                msg = "Masz aktualną wersję PP Channel Sync.\n\nZainstalowana: %s\nNa GitHub: %s" % (PLUGIN_VERSION, remote_version)
                write_text(UPDATE_INFO_PATH, msg + "\n"); self["status"].setText("Wtyczka jest aktualna"); self.popup(msg); return
            msg = "Dostępna aktualizacja PP Channel Sync.\n\nZainstalowana: %s\nNowa: %s" % (PLUGIN_VERSION, remote_version)
            if notes: msg += "\n\nZmiany:\n" + notes[:1600]
            msg += "\n\nRozpocząć pobieranie i instalację?"
            self.session.openWithCallback(lambda answer: self._update_confirmed(answer, manifest), MessageBox, msg, type=MessageBox.TYPE_YESNO, default=True)
        except Exception as e:
            self["status"].setText("Błąd aktualizacji")
            err = "%s\n\n%s" % (str(e), traceback.format_exc())
            try: write_text(UPDATE_INFO_PATH, err)
            except Exception: pass
            self.popup("Nie udało się sprawdzić aktualizacji z GitHub:\n%s\n\nSzczegóły: %s" % (str(e), UPDATE_INFO_PATH), MessageBox.TYPE_ERROR)

    def _update_confirmed(self, answer, manifest):
        if not answer:
            self.popup("Aktualizacja anulowana."); return
        try:
            self["status"].setText("Pobieranie aktualizacji...")
            ipk = download_update_ipk(manifest)
            self["status"].setText("Instalacja aktualizacji...")
            log = install_ipk(ipk)
            version = _manifest_value(manifest, "version", "latest_version")
            msg = "Aktualizacja została zainstalowana.\n\nNowa wersja: %s\nPlik: %s\n\nWykonaj restart GUI, aby załadować nową wersję wtyczki.\n\nLog: %s" % (version, ipk, UPDATE_INFO_PATH)
            self["status"].setText("Aktualizacja zainstalowana"); self.popup(msg, MessageBox.TYPE_INFO)
        except Exception as e:
            self["status"].setText("Błąd instalacji aktualizacji")
            err = "%s\n\n%s" % (str(e), traceback.format_exc())
            try: write_text(UPDATE_INFO_PATH, err)
            except Exception: pass
            self.popup("Nie udało się zainstalować aktualizacji:\n%s\n\nSzczegóły: %s" % (str(e), UPDATE_INFO_PATH), MessageBox.TYPE_ERROR)

    def info(self):
        text = "PP Channel Sync v%s\n%s\n\nWersja 1.1.13 przywraca sprawdzony rdzeń korekty list i EPG z v1.0.17 oraz zachowuje narzędzia z gałęzi 1.1.x: tryb prosty/zaawansowany, pojedynczy bukiet, pojedynczy kanał, zmiana nazwy bukietu, raporty, kopie, diagnostyka i aktualizacja z GitHub.\n\nNajważniejsze: istniejąca lista ma być korygowana tak, aby kanały i EPG działały jak w stabilnej wersji 1.0.17. Wtyczka nie zmienia ustawień głowicy, sieci, skina ani rozdzielczości." % (PLUGIN_VERSION, AUTHOR)
        self.popup(text)

def main(session, **kwargs):
    session.open(PPChannelSyncScreen)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name=PLUGIN_NAME,
            description="PP Channel Sync - extended list tools, bouquet update, reports",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        ),
        PluginDescriptor(
            name=PLUGIN_NAME,
            description="PP Channel Sync - automatic list check",
            where=PluginDescriptor.WHERE_SESSIONSTART,
            fnc=autostart
        )
    ]
