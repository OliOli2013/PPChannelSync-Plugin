# -*- coding: utf-8 -*-
# PP Channel Sync for Enigma2 Python 3
# Author: by Paweł Pawełek

from __future__ import print_function

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
    Request = None
    urlopen = None

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

PLUGIN_VERSION = "1.0.16"
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
CONFIG_PATH = "/etc/enigma2/ppchannelsync.conf"
STATE_PATH = "/etc/enigma2/ppchannelsync_state.conf"
UPDATE_INFO_PATH = "/tmp/ppchannelsync_update_info.txt"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/update.json"
MANAGED_PREFIX = "ppcs_"

SOURCE_STANDARD = 0
SOURCE_ALTERNATIVE = 1
SOURCE_OPTIONS = [
    ("Standard", "Podstawowe źródło kontroli. Dobre jako pierwszy wybór dla większości list."),
    ("Alternatywne", "Drugie źródło kontroli oparte o paczki Ciefp z GitHub. Przydatne, gdy standardowe źródło gorzej dopasowuje Twoją listę."),
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

# Zgodność z wcześniejszymi funkcjami.
ONLINE_PACKAGES = STANDARD_PACKAGES

def packages_for_source(source_index):
    return ALTERNATIVE_PACKAGES if int(source_index or 0) == SOURCE_ALTERNATIVE else STANDARD_PACKAGES

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
]

REMOVE_OFF = 0
REMOVE_REPORT = 1
REMOVE_DELETE = 2
REMOVE_MODES = [
    ("Nie", "Nie usuwa kanałów z Twoich bukietów. Kanały niepewne zostają tylko w raporcie."),
    ("Tylko raport", "Wykrywa kanały, których nie ma w bazie kontrolnej, ale nie usuwa ich z listy."),
    ("Usuń pewne", "Usuwa wyłącznie pozycje jednoznacznie oznaczone jako nieaktualne w pasującym bukiecie. Używać ostrożnie."),
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



def _(txt):
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
    }


def save_settings(data):
    cfg = read_kv(CONFIG_PATH)
    for key in ("source_index", "package_index", "mode", "add_new_mode", "remove_mode", "auto_mode"):
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


def download_url(url, dest):
    if Request is None or urlopen is None:
        raise Exception("Brak urllib.request w systemie Python.")
    req = Request(url, headers={"User-Agent": "PPChannelSync/%s Enigma2" % PLUGIN_VERSION})
    response = urlopen(req, timeout=60)
    data = response.read()
    if not data or len(data) < 1024:
        raise Exception("Pobrany plik jest pusty albo za mały.")
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def fetch_json(url):
    if Request is None or urlopen is None:
        raise Exception("Brak urllib.request w systemie Python.")
    req = Request(url, headers={"User-Agent": "PPChannelSync/%s Enigma2" % PLUGIN_VERSION, "Accept": "application/vnd.github+json"})
    data = urlopen(req, timeout=30).read()
    return json.loads(data.decode("utf-8", "ignore"))


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
    source_index = int(source_index or 0)
    pkg_index = clamp_package_index(source_index, pkg_index)
    packages = packages_for_source(source_index)
    label, value = packages[pkg_index]
    source_label = SOURCE_OPTIONS[source_index][0]
    if source_index == SOURCE_ALTERNATIVE:
        url, resolved_name = resolve_ciefp_url(value)
        resolved_label = "%s / %s" % (label, resolved_name)
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

            if cur_key in remote_services:
                # Reference już istnieje w bazie kontrolnej. Nie zmieniamy pozycji ani wpisu w bukiecie.
                plan["same_ref"] += 1
                used_remote_keys.add(cur_key)
                continue

            # v1.0.10: najpierw sprawdzamy ten sam SID/TSID/ONID/namespace z innym service type.
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

        # Usuwanie jest domyślnie raportowe. W trybie Usuń pewne usuwamy tylko wpisy bez pewnego
        # odpowiednika, ale dopiero po świadomym ustawieniu opcji przez użytkownika.
        if remove_mode == REMOVE_DELETE:
            for e in entries:
                cur_key = e.get("key")
                if not cur_key or cur_key in remote_services:
                    continue
                cand = candidate_from_global_name(e, strict_unique)
                if cand:
                    continue
                if e.get("service_index") is not None:
                    file_plan["remove_indices"].add(e.get("service_index"))
                    if e.get("desc_index") is not None:
                        file_plan["remove_indices"].add(e.get("desc_index"))
                    plan["removed_channels"].append({"bouquet": local_title, "name": e.get("name") or e.get("ref"), "ref": e.get("ref")})
                    plan["removed_count"] += 1

    plan["protected_local_services"] = len(plan["service_appends"])
    return plan

def report_header_lines():
    return [
        "by Paweł Pawełek * %s" % CONTACT,
        "%s." % SUPPORT_TEXT,
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
    report.append("Zasada działania v1.0.15:")
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
    # Aktualizuje widok list bukietów w /etc/enigma2/bouquets.tv:
    # - usuwa stare wpisy informacyjne autorów/dat,
    # - nie zmienia nazw właściwych bukietów,
    # - dodaje jedną informację o korekcie PP Channel Sync + data na samym dole.
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
        if is_marker_service(line) and i + 1 < len(lines) and lines[i + 1].startswith("#DESCRIPTION "):
            desc = lines[i + 1][len("#DESCRIPTION "):].strip()
            if is_credit_description(desc):
                removed += 1
                i += 2
                continue
        # Nie czyścimy DESCRIPTION właściwych bukietów FROM BOUQUET, bo to są nazwy list użytkownika.
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
                lines.append("#SERVICE 1:64:0:0:0:0:0:0:0:0:")
                lines.append("#DESCRIPTION ........ nowe kanały - PP Channel Sync ........")
                for item in new_items:
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
    result.append("Kanały usunięte z bukietów: %d" % removed_channels)
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
        plan = build_plan(remote, None, cfg.get("add_new_mode", 1) == 1, cfg.get("remove_mode", REMOVE_REPORT))
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
        self.remove_mode = cfg.get("remove_mode", REMOVE_REPORT)
        self.auto_mode = cfg.get("auto_mode", AUTO_OFF)
        self.match_mode = MATCH_SAFE
        self.last_remote = None
        self.last_plan = None
        self["title"] = Label("PP Channel Sync")
        try:
            self.setTitle("PP Channel Sync v%s" % PLUGIN_VERSION)
        except Exception:
            pass
        self["version"] = Label("v%s" % PLUGIN_VERSION)
        self["status"] = Label("Opcje ustawiasz z listy, a zielony przycisk wykonuje wybrany tryb pracy")
        self["side_title"] = Label("Informacje")
        self["side_info"] = Label("")
        self["support_title"] = Label("Wesprzyj")
        self["support_text"] = Label("Pomóż rozwijać\nlokalne projekty")
        self["help"] = Label("OK - zmień opcję / otwórz  |  Zielony - wykonaj wybrany tryb  |  MENU - raport  |  EXIT - wyjście")
        self["footer"] = Label("%s  •  %s  •  Enigma2 Python 3  •  FB: Enigma 2 Oprogramowanie, dodatki" % (AUTHOR, CONTACT))
        self["key_red"] = Label("Czerwony: wyjście")
        self["key_green"] = Label("Zielony: wykonaj")
        self["key_yellow"] = Label("Żółty: kopia")
        self["key_blue"] = Label("Niebieski: przywróć")
        self["menu"] = MenuList([])
        try:
            from enigma import gFont
            self["menu"].l.setFont(0, gFont("Regular", 28))
            self["menu"].l.setItemHeight(44)
        except Exception:
            pass
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "red": self.close,
            "green": self.run_green,
            "yellow": self.backup_now,
            "blue": self.restore_last,
            "left": self.left,
            "right": self.right,
            "menu": self.show_last_report,
            "up": self.up,
            "down": self.down,
        }, -1)
        self.refresh_menu()
        try:
            self.onLayoutFinish.append(self.refresh_menu)
        except Exception:
            pass

    def menu_items(self):
        packages = packages_for_source(self.source_index)
        self.package_index = clamp_package_index(self.source_index, self.package_index)
        return [
            "Źródło kontroli:  %s" % SOURCE_OPTIONS[self.source_index][0],
            "Pakiet kontrolny:  %s" % packages[self.package_index][0],
            "Tryb pracy zielonego: %s" % SYNC_MODES[self.mode][0],
            "Dopisywanie nowych kanałów: %s" % ADD_NEW_MODES[self.add_new_mode][0],
            "Usuwanie nieaktualnych kanałów: %s" % REMOVE_MODES[self.remove_mode][0],
            "Automatyczna aktualizacja: %s" % AUTO_UPDATE_MODES[self.auto_mode][0],
            "Utwórz kopię bezpieczeństwa teraz",
            "Przywróć ostatnią kopię bezpieczeństwa",
            "Pokaż ostatni raport",
            "Pokaż szczegółowy raport zmian",
            "Aktualizuj wtyczkę z GitHub",
            "Informacje o działaniu wtyczki",
        ]

    def refresh_menu(self):
        self["menu"].setList(self.menu_items())
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

    def update_side_info(self):
        idx = self.selected_index()
        self["side_title"].setText("Opis opcji")
        if idx == 0:
            txt = SOURCE_OPTIONS[self.source_index][1] + "\n\nStandard / Alternatywne przełączasz OK albo Lewo/Prawo."
        elif idx == 1:
            txt = "Wybierz zakres kontroli zgodny z listą, którą masz na tunerze.\n\nPakiet służy tylko jako punkt porównania."
        elif idx == 2:
            txt = SYNC_MODES[self.mode][1] + "\n\nZielony przycisk wykonuje wybrany tryb."
        elif idx == 3:
            txt = ADD_NEW_MODES[self.add_new_mode][1]
        elif idx == 4:
            txt = REMOVE_MODES[self.remove_mode][1]
        elif idx == 5:
            txt = AUTO_UPDATE_MODES[self.auto_mode][1]
        elif idx == 6:
            txt = "Tworzy kopię lamedb, lamedb5, bouquets.tv i wszystkich userbouquet.*.tv."
        elif idx == 7:
            txt = "Przywraca ostatnią kopię wykonaną przez PP Channel Sync."
        elif idx == 8:
            txt = "Pokazuje ostatni raport skrócony. MENU działa tak samo z każdego miejsca ekranu."
        elif idx == 9:
            txt = "Pokazuje szczegółowy raport: dodane, usunięte, poprawione i pominięte kanały."
        elif idx == 10:
            txt = "Sprawdza update.json na GitHub, porównuje wersję, pobiera najnowszy plik IPK i instaluje aktualizację."
        else:
            txt = "Autor: by Paweł Pawełek\nKontakt: aio-iptv@wp.pl\n\nDVB-T/DVB-C jest pomijane. Wtyczka nie zmienia głowicy, sieci, skina ani rozdzielczości."
        self["side_info"].setText(txt)
    def up(self):
        self["menu"].up()
        self.update_side_info()

    def down(self):
        self["menu"].down()
        self.update_side_info()

    def left(self):
        idx = self.selected_index()
        if idx == 0:
            self.source_index = (self.source_index - 1) % len(SOURCE_OPTIONS)
            self.package_index = clamp_package_index(self.source_index, self.package_index)
        elif idx == 1:
            self.package_index = (self.package_index - 1) % len(packages_for_source(self.source_index))
        elif idx == 2:
            self.mode = (self.mode - 1) % len(SYNC_MODES)
        elif idx == 3:
            self.add_new_mode = (self.add_new_mode - 1) % len(ADD_NEW_MODES)
        elif idx == 4:
            self.remove_mode = (self.remove_mode - 1) % len(REMOVE_MODES)
        elif idx == 5:
            self.auto_mode = (self.auto_mode - 1) % len(AUTO_UPDATE_MODES)
        save_settings({"source_index": self.source_index, "package_index": self.package_index, "mode": self.mode, "add_new_mode": self.add_new_mode, "remove_mode": self.remove_mode, "auto_mode": self.auto_mode})
        self.refresh_menu()

    def right(self):
        idx = self.selected_index()
        if idx == 0:
            self.source_index = (self.source_index + 1) % len(SOURCE_OPTIONS)
            self.package_index = clamp_package_index(self.source_index, self.package_index)
        elif idx == 1:
            self.package_index = (self.package_index + 1) % len(packages_for_source(self.source_index))
        elif idx == 2:
            self.mode = (self.mode + 1) % len(SYNC_MODES)
        elif idx == 3:
            self.add_new_mode = (self.add_new_mode + 1) % len(ADD_NEW_MODES)
        elif idx == 4:
            self.remove_mode = (self.remove_mode + 1) % len(REMOVE_MODES)
        elif idx == 5:
            self.auto_mode = (self.auto_mode + 1) % len(AUTO_UPDATE_MODES)
        save_settings({"source_index": self.source_index, "package_index": self.package_index, "mode": self.mode, "add_new_mode": self.add_new_mode, "remove_mode": self.remove_mode, "auto_mode": self.auto_mode})
        self.refresh_menu()

    def ok(self):
        idx = self.selected_index()
        if idx in (0, 1, 2, 3, 4, 5):
            self.right()
        elif idx == 6:
            self.backup_now()
        elif idx == 7:
            self.restore_last()
        elif idx == 8:
            self.show_last_report()
        elif idx == 9:
            self.show_detail_report()
        elif idx == 10:
            self.update_plugin_from_github()
        elif idx == 11:
            self.info()

    def run_green(self):
        if self.mode == MODE_REPORT:
            self.check_changes()
        else:
            self.apply_update()

    def popup(self, text, mtype=MessageBox.TYPE_INFO, timeout=0):
        self.session.open(MessageBox, text, type=mtype, timeout=timeout)

    def check_changes(self):
        try:
            self["status"].setText("Pobieranie bazy i kontrola Twojej listy...")
            remote = load_online_package(self.package_index, self.source_index)
            plan = build_plan(remote, None, self.add_new_mode == 1, self.remove_mode)
            report = write_report(plan, self.mode, None)
            self.last_remote = remote
            self.last_plan = plan
            self["status"].setText("Raport gotowy: %s" % REPORT_PATH)
            short = (
                "Analiza zakończona.\n\n"
                "Sprawdzone wpisy kanałów: %d\n"
                "Referencje do korekty: %d\n"
                "Aliasy EPG/service type: %d\n"
                "Nowe kanały do dopisania: %d\n"
                "Kanały do usunięcia: %d\n"
                "Pominięte DVB-T/DVB-C: %d\n"
                "Lamedb zaktualizowany: TAK\n\n"
                "Gotowe bukiety nie będą dogrywane.\n"
                "Szczegóły: %s"
            ) % (plan["checked"], len(plan["ref_fixes"]), len(plan.get("epg_type_aliases", [])), plan["new_channels_added"], plan.get("removed_count", 0), len(plan.get("skipped_dvbt_bouquets", [])), DETAIL_REPORT_PATH)
            self.popup(short)
        except Exception as e:
            self["status"].setText("Błąd analizy")
            self.popup("Błąd podczas analizy:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def apply_update(self):
        try:
            if self.mode == MODE_REPORT:
                self.popup("Wybrany tryb to 'Raport bez zapisu'. Zmień tryb pracy, jeśli chcesz wykonać korektę.", MessageBox.TYPE_INFO)
                return
            if self.last_plan is None:
                remote = load_online_package(self.package_index, self.source_index)
                plan = build_plan(remote, None, self.add_new_mode == 1, self.remove_mode)
                write_report(plan, self.mode, None)
                self.last_remote = remote
                self.last_plan = plan
            self["status"].setText("Wykonywanie korekty posiadanej listy...")
            result = apply_plan(self.last_plan, self.mode)
            self["status"].setText("Korekta zakończona")
            self.popup(result)
        except Exception as e:
            self["status"].setText("Błąd korekty")
            err = "%s\n\n%s" % (str(e), traceback.format_exc())
            try:
                write_text(ERROR_PATH, err)
            except Exception:
                pass
            self.popup("Błąd podczas korekty:\n%s\n\nSzczegóły: %s" % (str(e), ERROR_PATH), MessageBox.TYPE_ERROR)

    def backup_now(self):
        try:
            backup = make_backup()
            self.popup("Kopia bezpieczeństwa utworzona:\n%s" % backup)
        except Exception as e:
            self.popup("Nie udało się utworzyć kopii:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def restore_last(self):
        try:
            b = latest_backup()
            if not b:
                self.popup("Brak kopii bezpieczeństwa.", MessageBox.TYPE_ERROR)
                return
            restore_backup(b)
            self.popup("Przywrócono ostatnią kopię:\n%s" % b)
        except Exception as e:
            self.popup("Nie udało się przywrócić kopii:\n%s" % str(e), MessageBox.TYPE_ERROR)

    def show_last_report(self):
        if not os.path.isfile(REPORT_PATH):
            self.popup("Brak raportu. Najpierw ustaw tryb raportu i naciśnij zielony przycisk.")
            return
        text = read_text(REPORT_PATH)
        if len(text) > 4200:
            text = text[:4200] + "\n\n...\nPełny raport: %s" % REPORT_PATH
        self.popup(text)

    def show_detail_report(self):
        if not os.path.isfile(DETAIL_REPORT_PATH):
            self.popup("Brak raportu szczegółowego. Najpierw ustaw tryb raportu i naciśnij zielony przycisk.")
            return
        text = read_text(DETAIL_REPORT_PATH)
        if len(text) > 5200:
            text = text[:5200] + "\n\n...\nPełny raport szczegółowy: %s" % DETAIL_REPORT_PATH
        self.popup(text)

    def update_plugin_from_github(self):
        try:
            self["status"].setText("Sprawdzanie aktualizacji z GitHub...")
            manifest = fetch_json(UPDATE_MANIFEST_URL)
            remote_version = _manifest_value(manifest, "version", "latest_version")
            notes = manifest.get("notes", "")
            if isinstance(notes, list):
                notes = "\n".join(["- " + str(x) for x in notes])
            if not remote_version:
                raise Exception("Plik update.json nie zawiera pola version.")
            if not is_newer_version(remote_version, PLUGIN_VERSION):
                msg = "Masz aktualną wersję PP Channel Sync.\n\nZainstalowana: %s\nNa GitHub: %s" % (PLUGIN_VERSION, remote_version)
                write_text(UPDATE_INFO_PATH, msg + "\n")
                self["status"].setText("Wtyczka jest aktualna")
                self.popup(msg)
                return
            msg = "Dostępna aktualizacja PP Channel Sync.\n\nZainstalowana: %s\nNowa: %s" % (PLUGIN_VERSION, remote_version)
            if notes:
                msg += "\n\nZmiany:\n" + notes[:1600]
            msg += "\n\nRozpocząć pobieranie i instalację?"
            self.session.openWithCallback(lambda answer: self._update_confirmed(answer, manifest), MessageBox, msg, type=MessageBox.TYPE_YESNO, default=True)
        except Exception as e:
            self["status"].setText("Błąd aktualizacji")
            err = "%s\n\n%s" % (str(e), traceback.format_exc())
            try:
                write_text(UPDATE_INFO_PATH, err)
            except Exception:
                pass
            self.popup("Nie udało się sprawdzić aktualizacji z GitHub:\n%s\n\nSzczegóły: %s" % (str(e), UPDATE_INFO_PATH), MessageBox.TYPE_ERROR)

    def _update_confirmed(self, answer, manifest):
        if not answer:
            self.popup("Aktualizacja anulowana.")
            return
        try:
            self["status"].setText("Pobieranie aktualizacji...")
            ipk = download_update_ipk(manifest)
            self["status"].setText("Instalacja aktualizacji...")
            log = install_ipk(ipk)
            version = _manifest_value(manifest, "version", "latest_version")
            msg = (
                "Aktualizacja została zainstalowana.\n\n"
                "Nowa wersja: %s\n"
                "Plik: %s\n\n"
                "Wykonaj restart GUI, aby załadować nową wersję wtyczki.\n\n"
                "Log: %s"
            ) % (version, ipk, UPDATE_INFO_PATH)
            self["status"].setText("Aktualizacja zainstalowana")
            self.popup(msg, MessageBox.TYPE_INFO)
        except Exception as e:
            self["status"].setText("Błąd instalacji aktualizacji")
            err = "%s\n\n%s" % (str(e), traceback.format_exc())
            try:
                write_text(UPDATE_INFO_PATH, err)
            except Exception:
                pass
            self.popup("Nie udało się zainstalować aktualizacji:\n%s\n\nSzczegóły: %s" % (str(e), UPDATE_INFO_PATH), MessageBox.TYPE_ERROR)

    def info(self):
        text = (
            "PP Channel Sync v%s\n"
            "%s\n\n"
            "Wersja 1.0.16 działa w bezpiecznym trybie korekty technicznej i ma wybór źródła kontroli Standard / Alternatywne:\n"
            "- nie instaluje gotowych bukietów,\n"
            "- nie tworzy nowych bukietów,\n"
            "- nie przebudowuje układu ani kolejności listy,\n"
            "- aktualizuje lamedb bez podmiany całej bazy: zachowuje lokalne wpisy i dopisuje brakujące wpisy kontrolne,\n"
            "- poprawnie rozpoznaje lamedb /4/ z dziesiętnym typem usługi, np. 25=0x19 i 31=0x1F,\n"
            "- service reference poprawia tylko przy pewnym dopasowaniu,\n"
            "- nowe kanały dopisuje tylko na końcu pasujących bukietów,\n"
            "- usuwanie kanałów jest osobną opcją, domyślnie tylko raport,\n"
            "- dodaje datę oraz @ PP Channel Sync na dole widoku bukietów,\n"
            "- zapisuje raport skrócony i szczegółowy,\n"
            "- tworzy kopię przed zapisem.\n\n"
            "Wtyczka nie zmienia ustawień głowicy, sieci, skina ani rozdzielczości."
        ) % (PLUGIN_VERSION, AUTHOR)
        self.popup(text)


def main(session, **kwargs):
    session.open(PPChannelSyncScreen)


def Plugins(**kwargs):
    return [
        PluginDescriptor(
            name=PLUGIN_NAME,
            description="PP Channel Sync - korekta listy, DVB-T pomijane, raporty i QR",
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon="plugin.png",
            fnc=main
        ),
        PluginDescriptor(
            name=PLUGIN_NAME,
            description="PP Channel Sync - automatyczna kontrola listy",
            where=PluginDescriptor.WHERE_SESSIONSTART,
            fnc=autostart
        )
    ]
