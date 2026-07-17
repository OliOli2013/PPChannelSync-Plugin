# -*- coding: utf-8 -*-
# PP Channel Sync for Enigma2 Python 2/3
# PP Channel Sync 2.1 core: multi-satellite correction with controlled new-channel blocks.
# Author: by Paweł Pawełek

from __future__ import print_function, unicode_literals

import os
import re
import time
import json
import shutil
import tarfile
import zipfile
import hashlib
import tempfile
import traceback
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

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.ActionMap import ActionMap
from Components.Label import Label
from Components.MenuList import MenuList

PLUGIN_VERSION = "2.1.0"
PLUGIN_NAME = "PP Channel Sync"
AUTHOR = "by Paweł Pawełek"
CONTACT = "aio-iptv@wp.pl"
PLUGIN_PATH = "/usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync"
E2_PATH = "/etc/enigma2"
BACKUP_DIR = "/etc/enigma2/ppchannelsync_backups"
CONFIG_PATH = "/etc/enigma2/ppchannelsync2.conf"
STATE_PATH = "/etc/enigma2/ppchannelsync2_state.conf"
WORK_DIR = "/tmp/ppchannelsync2"
REPORT_PATH = "/tmp/ppchannelsync_report.txt"
DETAIL_REPORT_PATH = "/tmp/ppchannelsync_details.txt"
ERROR_PATH = "/tmp/ppchannelsync_error.txt"
UPDATE_INFO_PATH = "/tmp/ppchannelsync_update_info.txt"
DIAGNOSTIC_PATH = "/tmp/ppchannelsync_diagnostics.txt"
SUPPORT_ZIP_PATH = "/tmp/ppchannelsync_support.zip"
HISTORY_PATH = "/etc/enigma2/ppchannelsync2_history.log"
UPDATE_MANIFEST_URL = "https://raw.githubusercontent.com/OliOli2013/PPChannelSync-Plugin/main/update.json"
BACKUP_KEEP = 10
MAX_DOWNLOAD_BYTES = 128 * 1024 * 1024
MAX_EXTRACTED_BYTES = 384 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 20000
MIN_REMOTE_SERVICES = 100

GIOPPYGIO_API = "https://api.github.com/repos/OpenVisionE2/GioppyGio-settings/contents/GioppyGio_E2_Motor_75E-45W"
CIEFP_API = "https://api.github.com/repos/ciefp/ciefpsettings-enigma2-zipped/contents/"
CIEFP_PREFIX = "ciefp-E2-75E-34W-"

MODE_REPORT = 0
MODE_SYNC = 1
MODE_LABELS = ["Raport bez zapisu", "Bezpieczna korekta"]

SKIP_TYPES = set(["0", "64", "832"])
IPTV_TYPES = set(["4097", "5001", "5002", "8193", "8739"])


def _system_lang():
    try:
        from Components.Language import language
        lang = language.getLanguage() or ""
        return "pl" if lang.lower().startswith("pl") else "en"
    except Exception:
        return "pl"


_LANG = _system_lang()
_TR = {
    "Wybrane satelity": "Selected satellites",
    "Tryb pracy": "Operation mode",
    "Uruchom synchronizację": "Run synchronization",
    "Napraw ślady wersji 1.x": "Repair 1.x leftovers",
    "Pokaż ostatni raport": "Show last report",
    "Przywróć ostatnią kopię": "Restore last backup",
    "Aktualizuj wtyczkę z GitHub": "Update plugin from GitHub",
    "Informacje": "Information",
    "Raport bez zapisu": "Report only",
    "Bezpieczna korekta": "Safe correction",
    "Wyjście": "Exit",
    "Start": "Start",
    "Satelity": "Satellites",
    "Przywróć": "Restore",
    "Zapisz": "Save",
    "Anuluj": "Cancel",
    "Wybór satelitów": "Satellite selection",
    "Brak wykrytych satelitów w lokalnej liście.": "No satellites were detected in the local list.",
    "Sprawdź listę": "Check channel list",
    "Pokaż raport techniczny": "Show technical report",
    "Utwórz kopię bezpieczeństwa": "Create backup",
    "Diagnostyka systemu": "System diagnostics",
    "Przygotuj raport do wysłania": "Create support report",
    "Wesprzyj": "Support",
    "Pomóż rozwijać\nlokalne projekty": "Help develop\nlocal projects",
    "Nie wybrano żadnej satelity.": "No satellite was selected.",
    "Wybierz pozycje orbitalne, które mają zostać sprawdzone. OK zaznacza lub odznacza pozycję.": "Select orbital positions to check. OK toggles a position.",
    "Wtyczka poprawia istniejące kanały DVB-S i dopisuje pewne nowe kanały na końcu pasujących bukietów. Nie usuwa kanałów i nie zmienia kolejności istniejących pozycji.": "The plugin corrects existing DVB-S channels and appends verified new channels to the end of matching bouquets. It does not remove channels or reorder existing entries.",
}


def _(text):
    if _LANG == "en":
        return _TR.get(text, text)
    return text


def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def read_text(path):
    with open(path, "rb") as handle:
        data = handle.read()
    for enc in ("utf-8", "latin-1", "cp1250"):
        try:
            return data.decode(enc)
        except Exception:
            pass
    return data.decode("utf-8", "ignore")


def atomic_write(path, text):
    tmp = path + ".ppcs2.tmp"
    with open(tmp, "wb") as handle:
        handle.write(text.encode("utf-8", "ignore"))
        try:
            handle.flush()
            os.fsync(handle.fileno())
        except Exception:
            pass
    os.rename(tmp, path)


def read_kv(path):
    result = {}
    if not os.path.isfile(path):
        return result
    try:
        for line in read_text(path).splitlines():
            if not line or line.lstrip().startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
    except Exception:
        pass
    return result


def write_kv(path, data):
    lines = ["%s=%s" % (key, data[key]) for key in sorted(data.keys())]
    atomic_write(path, "\n".join(lines) + "\n")


def load_settings():
    data = read_kv(CONFIG_PATH)
    try:
        mode = int(data.get("mode", MODE_SYNC))
    except Exception:
        mode = MODE_SYNC
    if mode not in (MODE_REPORT, MODE_SYNC):
        mode = MODE_SYNC
    positions = []
    for value in data.get("positions", "").split(","):
        try:
            pos = int(value)
            if 0 < pos <= 3600 and pos not in positions:
                positions.append(pos)
        except Exception:
            pass
    return {"mode": mode, "positions": positions}


def save_settings(mode, positions):
    write_kv(CONFIG_PATH, {
        "mode": int(mode),
        "positions": ",".join([str(int(x)) for x in sorted(set(positions or []))]),
    })


def norm_hex(value):
    value = str(value or "0").strip().lower().replace("0x", "")
    value = value.lstrip("0")
    return value or "0"


def is_hex(value):
    return bool(re.match(r"^[0-9a-fA-F]+$", str(value or "")))


def lamedb4_type_to_ref(value):
    raw = str(value or "0").strip().lower()
    try:
        if re.match(r"^[0-9]+$", raw):
            return norm_hex(format(int(raw, 10), "x"))
        return norm_hex(raw)
    except Exception:
        return norm_hex(raw)


def ref_type_to_lamedb4(value):
    try:
        return str(int(norm_hex(value), 16))
    except Exception:
        return "0"


def make_key(stype, sid, tsid, onid, namespace):
    return (norm_hex(stype), norm_hex(sid), norm_hex(tsid), norm_hex(onid), norm_hex(namespace))


def key_core(key):
    if not key or len(key) != 5:
        return None
    return (key[1], key[2], key[3], key[4])


def key_tkey(key):
    if not key or len(key) != 5:
        return None
    return (key[4], key[2], key[3])


def ref_from_key(key):
    if not key or len(key) != 5:
        return ""
    return "1:0:%s:%s:%s:%s:%s:0:0:0:" % key


def key_from_ref(ref):
    if not ref or "FROM BOUQUET" in ref:
        return None
    parts = ref.strip().split(":")
    if len(parts) < 7 or parts[0] != "1" or parts[1] != "0":
        return None
    if not all(is_hex(x) for x in parts[2:7]):
        return None
    key = make_key(parts[2], parts[3], parts[4], parts[5], parts[6])
    if key[0] in SKIP_TYPES or key[1] == "0":
        return None
    return key


def valid_dvb_ref(ref):
    key = key_from_ref(ref)
    if not key:
        return False
    parts = ref.strip().split(":")
    return len(parts) >= 10


def is_iptv_ref(ref):
    raw = (ref or "").strip().lower()
    if "://" in raw or "%3a//" in raw:
        return True
    first = raw.split(":", 1)[0]
    return first in IPTV_TYPES


def terrestrial_namespace(namespace):
    ns = norm_hex(namespace)
    return ns.startswith("eeee") or ns.startswith("ffff")


def normalize_name(name):
    value = (name or "").strip().lower()
    value = value.replace("&amp;", "&").replace("\xc2\x86", "").replace("\xc2\x87", "")
    replacements = {
        "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z",
        "ä": "a", "ö": "o", "ü": "u", "ß": "ss", "é": "e", "è": "e", "à": "a", "á": "a",
        "í": "i", "ì": "i", "ú": "u", "ù": "u", "ý": "y", "č": "c", "ř": "r", "š": "s", "ž": "z",
    }
    for src, dst in replacements.items():
        value = value.replace(src, dst)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def usable_name(name):
    value = normalize_name(name)
    if not value or value in ("n/a", "<n/a>", "na", "none", "brak", "unknown"):
        return False
    compact = value.replace(" ", "")
    if re.match(r"^[0-9a-f]+(?::[0-9a-f]+){4,}$", compact):
        return False
    return True


def orbital_from_namespace(namespace):
    ns = norm_hex(namespace)
    if terrestrial_namespace(ns):
        return None
    try:
        value = int(ns, 16)
    except Exception:
        return None
    for shift in (16, 24):
        pos = (value >> shift) & 0xFFFF
        if 0 < pos <= 3600:
            return pos
    return None


def orbital_label(pos):
    try:
        pos = int(pos)
    except Exception:
        return str(pos)
    if pos > 1800:
        west = 3600 - pos
        return "%.1f°W" % (west / 10.0)
    return "%.1f°E" % (pos / 10.0)


def parse_transponder_line_v5(line):
    raw = (line or "").strip()
    if not raw.startswith("t:") or "," not in raw:
        return None
    head, suffix = raw.split(",", 1)
    parts = head.split(":")
    if len(parts) < 4 or not all(is_hex(x) for x in parts[1:4]):
        return None
    tkey = (norm_hex(parts[1]), norm_hex(parts[2]), norm_hex(parts[3]))
    return {"tkey": tkey, "suffix": suffix, "raw": [line]}


def parse_service_line_v5(line):
    raw = (line or "").strip()
    if not raw.startswith("s:") or "," not in raw:
        return None
    head, tail = raw.split(",", 1)
    parts = head.split(":")
    if len(parts) < 8 or not all(is_hex(x) for x in parts[1:6]):
        return None
    # In lamedb /5/ service_type is already hexadecimal. Do not convert it as decimal.
    key = make_key(parts[5], parts[1], parts[3], parts[4], parts[2])
    name = ""
    provider = ""
    match = re.match(r'^"((?:[^"\\]|\\.)*)"(?:,(.*))?$', tail)
    extras = ""
    if match:
        name = match.group(1).replace('\\"', '"')
        extras = match.group(2) or ""
    else:
        extras = tail
    pm = re.search(r"(?:^|,)p:([^,]*)", extras)
    if pm:
        provider = pm.group(1)
    return {
        "key": key,
        "name": name,
        "provider": provider,
        "service_number": parts[6],
        "source_id": parts[7],
        "tail": tail,
        "raw": [line],
        "format": 5,
    }


def parse_service_head_v4(line):
    raw = (line or "").strip()
    parts = raw.split(":")
    if len(parts) < 5 or len(parts) > 9:
        return None
    if not all(is_hex(x) for x in parts[:5]):
        return None
    key = make_key(lamedb4_type_to_ref(parts[4]), parts[0], parts[2], parts[3], parts[1])
    return key


def transponder_orbit(tkey, block):
    for line in block or []:
        raw = (line or "").strip()
        if ",s:" in raw:
            raw = raw.split(",", 1)[1]
        elif raw.startswith("s "):
            raw = raw[2:]
        elif raw.startswith("s:"):
            raw = raw[2:]
        else:
            continue
        if raw.startswith("s:"):
            raw = raw[2:]
        parts = raw.split(":")
        if len(parts) >= 5:
            try:
                pos = int(parts[4])
                if 0 < pos <= 3600:
                    return pos
            except Exception:
                pass
    return orbital_from_namespace(tkey[0] if tkey else "0")


def parse_lamedb(path):
    result = {
        "path": path,
        "format": 0,
        "lines": [],
        "services": OrderedDict(),
        "transponders": OrderedDict(),
        "names": {},
        "service_orbits": {},
        "valid": False,
        "trans_insert": None,
        "service_insert": None,
    }
    if not path or not os.path.isfile(path):
        return result
    lines = read_text(path).splitlines()
    result["lines"] = lines
    header = "\n".join(lines[:12]).lower()
    is_v5 = "/5/" in header or any(parse_service_line_v5(x) for x in lines[:300])
    if is_v5:
        result["format"] = 5
        trans_indices = []
        service_indices = []
        for idx, line in enumerate(lines):
            t = parse_transponder_line_v5(line)
            if t:
                result["transponders"][t["tkey"]] = t
                trans_indices.append(idx)
                continue
            service = parse_service_line_v5(line)
            if service:
                result["services"][service["key"]] = service
                if usable_name(service["name"]):
                    result["names"][service["key"]] = service["name"]
                service_indices.append(idx)
        if trans_indices and service_indices:
            result["trans_insert"] = service_indices[0]
            result["service_insert"] = service_indices[-1] + 1
            result["valid"] = True
    else:
        result["format"] = 4
        trans_start = trans_end = serv_start = serv_end = None
        for idx, line in enumerate(lines):
            low = line.strip().lower()
            if low == "transponders" and trans_start is None:
                trans_start = idx + 1
            elif trans_start is not None and trans_end is None and line.strip() == "/":
                trans_end = idx
            elif low == "services" and serv_start is None:
                serv_start = idx + 1
            elif serv_start is not None and serv_end is None and line.strip().lower() in ("/", "end"):
                serv_end = idx
                break
        if None not in (trans_start, trans_end, serv_start, serv_end):
            current = None
            block = []
            for line in lines[trans_start:trans_end]:
                raw = line.strip()
                parts = raw.split(":")
                new_key = None
                if len(parts) == 3 and all(is_hex(x) for x in parts):
                    new_key = (norm_hex(parts[0]), norm_hex(parts[1]), norm_hex(parts[2]))
                if new_key:
                    if current is not None:
                        result["transponders"][current] = {"tkey": current, "raw": list(block)}
                    current = new_key
                    block = [line]
                elif current is not None:
                    block.append(line)
            if current is not None:
                result["transponders"][current] = {"tkey": current, "raw": list(block)}

            current_key = None
            current_block = []
            for line in lines[serv_start:serv_end]:
                new_key = parse_service_head_v4(line)
                if new_key:
                    if current_key is not None:
                        record = service_record_v4(current_key, current_block)
                        result["services"][current_key] = record
                        if usable_name(record["name"]):
                            result["names"][current_key] = record["name"]
                    current_key = new_key
                    current_block = [line]
                elif current_key is not None:
                    current_block.append(line)
            if current_key is not None:
                record = service_record_v4(current_key, current_block)
                result["services"][current_key] = record
                if usable_name(record["name"]):
                    result["names"][current_key] = record["name"]
            result["trans_insert"] = trans_end
            result["service_insert"] = serv_end
            result["valid"] = bool(result["transponders"] and result["services"])

    for key in result["services"].keys():
        tkey = key_tkey(key)
        trans = result["transponders"].get(tkey)
        result["service_orbits"][key] = transponder_orbit(tkey, trans.get("raw") if trans else [])
    return result


def service_record_v4(key, block):
    name = ""
    provider = ""
    for line in block[1:]:
        raw = line.strip()
        if not raw or raw == "/":
            continue
        if raw.lower().startswith("p:"):
            provider = raw[2:]
            continue
        if raw.lower().startswith(("c:", "f:", "c ", "f ")):
            continue
        if not name:
            name = raw
    return {"key": key, "name": name, "provider": provider, "raw": list(block), "format": 4}


def valid_local_databases():
    databases = []
    for name in ("lamedb", "lamedb5"):
        db = parse_lamedb(os.path.join(E2_PATH, name))
        if db.get("valid"):
            databases.append(db)
    databases.sort(key=lambda item: (-len(item.get("services") or {}), 0 if os.path.basename(item.get("path", "")) == "lamedb" else 1))
    return databases


def choose_remote_database(root):
    candidates = []
    for base, _dirs, files in os.walk(root):
        for name in files:
            if name.lower() in ("lamedb", "lamedb5"):
                db = parse_lamedb(os.path.join(base, name))
                if db.get("valid"):
                    candidates.append(db)
    candidates.sort(key=lambda item: -len(item.get("services") or {}))
    if not candidates or len(candidates[0].get("services") or {}) < MIN_REMOTE_SERVICES:
        raise Exception("Pobrane źródło nie zawiera poprawnej bazy kanałów.")
    return candidates[0]


def bouquet_files():
    ordered = []
    main = os.path.join(E2_PATH, "bouquets.tv")
    if os.path.isfile(main):
        try:
            for line in read_text(main).splitlines():
                if "FROM BOUQUET" not in line or "userbouquet." not in line or ".tv" not in line:
                    continue
                match = re.search(r'"([^\"]*userbouquet\.[^\"]+\.tv)"', line)
                if match:
                    path = os.path.join(E2_PATH, os.path.basename(match.group(1)))
                    if os.path.isfile(path) and path not in ordered:
                        ordered.append(path)
        except Exception:
            pass
    try:
        for name in sorted(os.listdir(E2_PATH)):
            if name.startswith("userbouquet.") and name.endswith(".tv"):
                path = os.path.join(E2_PATH, name)
                if path not in ordered:
                    ordered.append(path)
    except Exception:
        pass
    return ordered


def find_local_record(databases, key):
    for db in databases or []:
        record = (db.get("services") or {}).get(key)
        if record:
            return db, record
    return None, None


def entry_orbit(databases, key):
    for db in databases or []:
        if key in (db.get("service_orbits") or {}):
            pos = db["service_orbits"].get(key)
            if pos is not None:
                return pos
    return orbital_from_namespace(key[4] if key else "0")


def marker_service_line(line):
    if not (line or "").startswith("#SERVICE "):
        return False
    ref = line[9:].strip()
    if "FROM BOUQUET" in ref:
        return False
    parts = ref.split(":")
    return len(parts) >= 2 and norm_hex(parts[1]) in ("64", "832")


def new_block_start(description):
    value = normalize_name(description)
    return "pp channel sync" in value and "nowe kanaly" in value


def new_block_end(description):
    value = normalize_name(description)
    return "pp channel sync" in value and "koniec" in value


def extract_owned_new_channel_block(lines):
    """Remove only PP Channel Sync-owned new-channel blocks.

    Existing channels are returned as structured items so a later run can
    rebuild one clean block without duplicating markers or deleting channels.
    Legacy 1.x blocks without an explicit end marker are supported when they
    are located at the end of a bouquet.
    """
    source = list(lines or [])
    base = []
    owned = []
    found = 0
    idx = 0
    while idx < len(source):
        line = source[idx]
        desc = source[idx + 1][13:].strip() if idx + 1 < len(source) and source[idx + 1].startswith("#DESCRIPTION ") else ""
        if marker_service_line(line) and new_block_start(desc):
            found += 1
            idx += 2
            while idx < len(source):
                current = source[idx]
                next_desc = source[idx + 1][13:].strip() if idx + 1 < len(source) and source[idx + 1].startswith("#DESCRIPTION ") else ""
                if marker_service_line(current) and new_block_end(next_desc):
                    idx += 2
                    break
                if current.startswith("#SERVICE "):
                    ref = current[9:].strip()
                    key = key_from_ref(ref)
                    if key and not is_iptv_ref(ref) and not terrestrial_namespace(key[4]):
                        name = next_desc if usable_name(next_desc) else ""
                        owned.append({
                            "service_line": "#SERVICE %s" % ref,
                            "description_line": "#DESCRIPTION %s" % name if name else "",
                            "ref": ref,
                            "key": key,
                            "name": name,
                        })
                        idx += 2 if next_desc else 1
                        continue
                # Legacy blocks had no end marker and were always appended at EOF.
                idx += 1
            continue
        base.append(line)
        idx += 1
    return base, owned, found


def parse_bouquet_lines(path, lines, databases):
    entries = []
    pending = None
    for idx, line in enumerate(lines or []):
        if line.startswith("#SERVICE "):
            ref = line[9:].strip()
            pending = None
            if "FROM BOUQUET" in ref or is_iptv_ref(ref):
                continue
            key = key_from_ref(ref)
            if not key or terrestrial_namespace(key[4]):
                continue
            _db, record = find_local_record(databases, key)
            name = record.get("name", "") if record else ""
            entry = {
                "path": path,
                "index": idx,
                "ref": ref,
                "key": key,
                "name": name,
                "orbit": entry_orbit(databases, key),
            }
            entries.append(entry)
            pending = entry
            continue
        if line.startswith("#DESCRIPTION ") and pending is not None:
            desc = line[13:].strip()
            if usable_name(desc):
                pending["name"] = desc
            pending = None
        elif not line.startswith("#DESCRIPTION "):
            pending = None
    return entries


def parse_bouquet(path, databases):
    lines = read_text(path).splitlines()
    return lines, parse_bouquet_lines(path, lines, databases)


def bouquet_title(lines, path=""):
    for line in lines or []:
        if line.startswith("#NAME"):
            value = line[5:].strip()
            if value:
                return value
    name = os.path.basename(path or "")
    return name.replace("userbouquet.", "").replace(".tv", "").replace("_", " ")


def bouquet_match_key(value):
    text = normalize_name(value)
    text = text.replace("+", " plus ")
    replacements = {
        "canal plus": "canalplus", "cyfra plus": "canalplus",
        "polsat box": "polsatbox", "cyfrowy polsat": "polsatbox",
        "wiadomosci": "informacyjne", "news": "informacyjne", "notizie": "informacyjne",
        "filmy": "film", "cinema": "film", "kino": "film",
        "dzieci": "kids", "bambini": "kids",
        "muzyka": "music", "musica": "music",
        "sporty": "sport", "sports": "sport",
        "polska": "polskie", "polish": "polskie", "poland": "polskie",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    text = text.replace("13.0e", "13e").replace("19.2e", "19e")
    return re.sub(r"[^a-z0-9]+", "", text)


def remote_bouquet_files(root):
    result = []
    for base, _dirs, files in os.walk(root or ""):
        for name in files:
            low = name.lower()
            if low.startswith("userbouquet.") and low.endswith(".tv"):
                result.append(os.path.join(base, name))
    return sorted(result)


def remote_bouquet_index(remote):
    db = remote.get("db") or {}
    items = []
    for path in remote.get("bouquets") or remote_bouquet_files(remote.get("root")):
        try:
            lines = read_text(path).splitlines()
            entries = parse_bouquet_lines(path, lines, [db])
            if not entries:
                continue
            title = bouquet_title(lines, path)
            names = set([normalize_name(x.get("name")) for x in entries if usable_name(x.get("name"))])
            positions = set([x.get("orbit") for x in entries if x.get("orbit")])
            items.append({"path": path, "title": title, "key": bouquet_match_key(title), "entries": entries, "names": names, "positions": positions})
        except Exception:
            pass
    return items


def find_remote_bouquet(local_title, local_entries, remote_items, selected_positions):
    local_names = set([normalize_name(x.get("name")) for x in local_entries if usable_name(x.get("name"))])
    local_key = bouquet_match_key(local_title)
    local_positions = set([x.get("orbit") for x in local_entries if x.get("orbit") in selected_positions])
    best = None
    best_rank = None
    for item in remote_items or []:
        if local_positions and not local_positions.intersection(item.get("positions") or set()):
            continue
        item_key = item.get("key") or ""
        overlap = len(local_names.intersection(item.get("names") or set()))
        ratio = float(overlap) / float(max(1, len(local_names)))
        exact_title = bool(local_key and item_key and local_key == item_key)
        related_title = bool(local_key and item_key and (local_key in item_key or item_key in local_key))
        rank = (2 if exact_title else 1 if related_title else 0, overlap, ratio)
        if best_rank is None or rank > best_rank:
            best = item
            best_rank = rank
    if not best or best_rank is None:
        return None
    title_rank, overlap, ratio = best_rank
    if title_rank == 2:
        return best
    if title_rank == 1 and overlap >= 3:
        return best
    threshold = max(5, int(len(local_names) * 0.25))
    if overlap >= threshold and ratio >= 0.20:
        return best
    return None


def configured_positions_from_settings(path=None):
    """Read orbital positions configured on tuner inputs.

    Enigma2 images use several key layouts (simple DiSEqC and advanced mode),
    so values are collected only from keys which are known to contain a
    satellite orbital position. This avoids showing frequencies and LNB data.
    """
    path = path or os.path.join(E2_PATH, "settings")
    found = set()
    if not os.path.isfile(path):
        return []
    try:
        lines = read_text(path).splitlines()
    except Exception:
        return []
    for line in lines:
        if not line.startswith("config.Nims.") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        low = key.lower()
        # Advanced tuner configuration stores the position in the key.
        for match in re.findall(r"\.advanced\.sat\.(\d+)(?:\.|$)", low):
            try:
                pos = int(match)
                if 0 < pos <= 3600:
                    found.add(pos)
            except Exception:
                pass
        # Simple DiSEqC and rotor images store it in the value.
        relevant = (
            re.search(r"\.diseqc[a-d]$", low) or
            low.endswith(".satpos") or
            low.endswith(".lastrotorposition") or
            low.endswith(".lastsatrotorposition") or
            low.endswith(".advanced.sats") or
            low.endswith(".satellites")
        )
        if not relevant:
            continue
        for token in re.findall(r"\d+", value):
            try:
                pos = int(token)
                if 0 < pos <= 3600:
                    found.add(pos)
            except Exception:
                pass
    return sorted(found)


def detect_positions():
    """Return every useful orbital position, not only the first bouquet hit.

    Sources are merged: services used by bouquets, all valid local lamedb
    records and tuner input configuration. The old 2.0.0 implementation
    returned early as soon as one bouquet position was found, which hid the
    remaining configured satellites.
    """
    databases = valid_local_databases()
    used = set()
    local = set()
    if databases:
        for path in bouquet_files():
            try:
                _lines, entries = parse_bouquet(path, databases)
                for entry in entries:
                    pos = entry.get("orbit")
                    if pos:
                        used.add(pos)
            except Exception:
                pass
        for db in databases:
            for pos in db.get("service_orbits", {}).values():
                if pos:
                    local.add(pos)
    configured = set(configured_positions_from_settings())
    return sorted(used.union(local).union(configured))


def download_bytes(url, headers=None, max_bytes=MAX_DOWNLOAD_BYTES):
    error = None
    if Request is not None and urlopen is not None:
        try:
            req_headers = {
                "User-Agent": "PPChannelSync/%s Enigma2" % PLUGIN_VERSION,
                "Accept": "*/*",
                "Cache-Control": "no-cache",
            }
            if headers:
                req_headers.update(headers)
            response = urlopen(Request(url, headers=req_headers), timeout=45)
            data = response.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise Exception("Pobrany plik przekracza limit rozmiaru.")
            return data
        except Exception as exc:
            error = exc
    tmp = tempfile.mktemp(prefix="ppcs2_dl_")
    for command in (
        ["wget", "-q", "--no-check-certificate", "-O", tmp, url],
        ["curl", "-L", "-k", "-sS", "--max-time", "60", "-o", tmp, url],
    ):
        try:
            ret = subprocess.call(command)
            if ret == 0 and os.path.isfile(tmp):
                if os.path.getsize(tmp) > max_bytes:
                    raise Exception("Pobrany plik przekracza limit rozmiaru.")
                with open(tmp, "rb") as handle:
                    data = handle.read()
                try:
                    os.unlink(tmp)
                except Exception:
                    pass
                return data
        except Exception as exc:
            error = exc
    try:
        if os.path.isfile(tmp):
            os.unlink(tmp)
    except Exception:
        pass
    raise Exception("Nie udało się pobrać danych: %s" % str(error or "brak wget/curl"))


def fetch_json(url):
    data = download_bytes(url, {"Accept": "application/vnd.github+json"}, 8 * 1024 * 1024)
    try:
        return json.loads(data.decode("utf-8", "ignore"))
    except Exception as exc:
        raise Exception("Niepoprawna odpowiedź JSON: %s" % str(exc))


def safe_target(base, name):
    target = os.path.abspath(os.path.join(base, name))
    root = os.path.abspath(base) + os.sep
    if not target.startswith(root):
        raise Exception("Archiwum zawiera niebezpieczną ścieżkę: %s" % name)
    return target


def extract_archive(path, dest):
    ensure_dir(dest)
    total = 0
    members_count = 0
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path, "r") as archive:
            for info in archive.infolist():
                members_count += 1
                if members_count > MAX_ARCHIVE_MEMBERS:
                    raise Exception("Archiwum zawiera zbyt wiele plików.")
                total += int(info.file_size or 0)
                if total > MAX_EXTRACTED_BYTES:
                    raise Exception("Rozpakowane dane przekraczają limit.")
                safe_target(dest, info.filename)
            archive.extractall(dest)
        return
    try:
        with tarfile.open(path, "r:*") as archive:
            selected = []
            for member in archive.getmembers():
                members_count += 1
                if members_count > MAX_ARCHIVE_MEMBERS:
                    raise Exception("Archiwum zawiera zbyt wiele plików.")
                if not member.isfile() and not member.isdir():
                    raise Exception("Archiwum zawiera niedozwolony typ wpisu.")
                total += int(member.size or 0)
                if total > MAX_EXTRACTED_BYTES:
                    raise Exception("Rozpakowane dane przekraczają limit.")
                safe_target(dest, member.name)
                selected.append(member)
            archive.extractall(dest, members=selected)
        return
    except tarfile.TarError:
        pass
    raise Exception("Nieobsługiwany format archiwum.")


def cleanup_workdir():
    if os.path.isdir(WORK_DIR):
        shutil.rmtree(WORK_DIR, ignore_errors=True)
    ensure_dir(WORK_DIR)


def remote_needed_file(name):
    low = str(name or "").lower()
    if low in ("lamedb", "lamedb5", "bouquets.tv"):
        return True
    return low.startswith("userbouquet.") and low.endswith(".tv")


def load_gioppygio_motor():
    listing = fetch_json(GIOPPYGIO_API)
    if not isinstance(listing, list):
        raise Exception("GitHub nie zwrócił listy plików GioppyGio.")
    wanted = []
    for item in listing:
        name = str(item.get("name", ""))
        if item.get("type") == "file" and remote_needed_file(name):
            wanted.append(item)
    if not any(str(x.get("name", "")).lower() in ("lamedb", "lamedb5") for x in wanted):
        raise Exception("W źródle GioppyGio nie znaleziono lamedb ani lamedb5.")
    root = os.path.join(WORK_DIR, "gioppygio")
    ensure_dir(root)
    errors = []
    for item in wanted:
        url = item.get("download_url")
        if not url:
            continue
        try:
            data = download_bytes(url)
            with open(os.path.join(root, os.path.basename(item.get("name"))), "wb") as handle:
                handle.write(data)
        except Exception as exc:
            errors.append("%s: %s" % (item.get("name"), str(exc)))
    db = choose_remote_database(root)
    bouquets = remote_bouquet_files(root)
    if not bouquets:
        raise Exception("Źródło GioppyGio nie udostępniło bukietów TV potrzebnych do dopisywania nowych kanałów.%s" % ("\n" + "\n".join(errors) if errors else ""))
    return {"label": "GioppyGio Motor 75E-45W", "db": db, "root": root, "bouquets": bouquets}


def ciefp_date_key(name):
    match = re.search(r"(\d{2})[._-](\d{2})[._-](\d{4})", name or "")
    if match:
        return (int(match.group(3)), int(match.group(2)), int(match.group(1)), name)
    return (0, 0, 0, name or "")


def load_ciefp_motor():
    listing = fetch_json(CIEFP_API)
    if not isinstance(listing, list):
        raise Exception("GitHub nie zwrócił listy paczek Ciefp.")
    items = []
    for item in listing:
        name = str(item.get("name", ""))
        if item.get("type") == "file" and name.startswith(CIEFP_PREFIX) and name.lower().endswith(".zip"):
            items.append(item)
    if not items:
        raise Exception("Nie znaleziono paczki Ciefp Motor.")
    items.sort(key=lambda item: ciefp_date_key(str(item.get("name", ""))), reverse=True)
    chosen = items[0]
    url = chosen.get("download_url")
    if not url:
        raise Exception("Brak bezpośredniego adresu paczki Ciefp.")
    archive = os.path.join(WORK_DIR, "ciefp_motor.zip")
    with open(archive, "wb") as handle:
        handle.write(download_bytes(url))
    root = os.path.join(WORK_DIR, "ciefp")
    extract_archive(archive, root)
    db = choose_remote_database(root)
    bouquets = remote_bouquet_files(root)
    if not bouquets:
        raise Exception("Paczka Ciefp nie zawiera bukietów TV potrzebnych do dopisywania nowych kanałów.")
    return {"label": str(chosen.get("name")), "db": db, "root": root, "bouquets": bouquets}


def load_remote_motor():
    cleanup_workdir()
    errors = []
    for loader in (load_gioppygio_motor, load_ciefp_motor):
        try:
            remote = loader()
            positions = set([x for x in remote["db"].get("service_orbits", {}).values() if x])
            if len(positions) < 4:
                raise Exception("Pobrana baza nie wygląda na listę wielosatelitarną.")
            remote["positions"] = positions
            return remote
        except Exception as exc:
            errors.append("%s: %s" % (loader.__name__, str(exc)))
    raise Exception("Nie udało się pobrać bazy kontrolnej.\n" + "\n".join(errors))


def remote_indexes(remote_db):
    exact = remote_db.get("services") or {}
    core = {}
    names = {}
    for key, record in exact.items():
        pos = remote_db.get("service_orbits", {}).get(key)
        if not pos or terrestrial_namespace(key[4]):
            continue
        core.setdefault(key_core(key), []).append(record)
        if usable_name(record.get("name")):
            names.setdefault((pos, normalize_name(record.get("name"))), []).append(record)
    return exact, core, names


def build_plan(selected_positions, remote):
    databases = valid_local_databases()
    if not databases:
        raise Exception("Nie znaleziono poprawnego lokalnego pliku lamedb ani lamedb5.")
    selected = set([int(x) for x in selected_positions or []])
    if not selected:
        raise Exception(_("Nie wybrano żadnej satelity."))
    exact, core_index, name_index = remote_indexes(remote["db"])
    remote_bouquets = remote_bouquet_index(remote)
    plan = {
        "databases": databases,
        "remote": remote,
        "remote_bouquets": remote_bouquets,
        "selected": selected,
        "files": OrderedDict(),
        "db_service_additions": OrderedDict(),
        "db_transponder_additions": OrderedDict(),
        "checked": 0,
        "unchanged": 0,
        "ref_changes": [],
        "aliases": [],
        "unmatched": [],
        "ambiguous": [],
        "new_channels": [],
        "new_channels_planned": 0,
        "retained_owned_channels": 0,
        "matched_bouquets": 0,
        "unmatched_bouquets": [],
        "missing_remote_positions": [],
        "per_position": OrderedDict(),
    }
    remote_positions = remote.get("positions") or set()
    for pos in sorted(selected):
        plan["per_position"][pos] = {"checked": 0, "changed": 0, "aliases": 0, "unmatched": 0, "ambiguous": 0, "added": 0}
        if pos not in remote_positions:
            plan["missing_remote_positions"].append(pos)

    for path in bouquet_files():
        try:
            original_lines = read_text(path).splitlines()
            base_lines, old_owned, owned_blocks = extract_owned_new_channel_block(original_lines)
            entries = parse_bouquet_lines(path, base_lines, databases)
        except Exception:
            continue
        changes = {}
        local_positions = set([x.get("orbit") for x in entries if x.get("orbit") in selected])
        for entry in entries:
            pos = entry.get("orbit")
            if pos not in selected:
                continue
            stats = plan["per_position"].setdefault(pos, {"checked": 0, "changed": 0, "aliases": 0, "unmatched": 0, "ambiguous": 0, "added": 0})
            stats["checked"] += 1
            plan["checked"] += 1
            current_key = entry["key"]
            local_has_key = any(current_key in (db.get("services") or {}) for db in databases)
            if current_key in exact:
                if not local_has_key:
                    source_record = exact[current_key]
                    add_db_record(plan, current_key, source_record)
                    plan["aliases"].append({"path": path, "name": entry.get("name") or source_record.get("name") or entry.get("ref"), "key": current_key, "source_key": source_record["key"], "position": pos})
                    stats["aliases"] += 1
                else:
                    plan["unchanged"] += 1
                continue

            same_core = core_index.get(key_core(current_key), [])
            if len(same_core) == 1:
                source_record = same_core[0]
                add_db_record(plan, current_key, source_record)
                plan["aliases"].append({"path": path, "name": entry.get("name") or entry.get("ref"), "key": current_key, "source_key": source_record["key"], "position": pos})
                stats["aliases"] += 1
                continue

            name = entry.get("name") or ""
            if not usable_name(name):
                plan["unmatched"].append({"path": path, "name": name or entry.get("ref"), "ref": entry.get("ref"), "position": pos, "reason": "brak poprawnej nazwy"})
                stats["unmatched"] += 1
                continue
            candidates = name_index.get((pos, normalize_name(name)), [])
            unique = {}
            for record in candidates:
                unique[record["key"]] = record
            candidates = list(unique.values())
            if len(candidates) != 1:
                target = plan["ambiguous"] if len(candidates) > 1 else plan["unmatched"]
                target.append({"path": path, "name": name, "ref": entry.get("ref"), "position": pos, "reason": "wiele dopasowań" if len(candidates) > 1 else "brak w bazie"})
                stats["ambiguous" if len(candidates) > 1 else "unmatched"] += 1
                continue

            source_record = candidates[0]
            remote_key = source_record["key"]
            target_key = make_key(current_key[0], remote_key[1], remote_key[2], remote_key[3], remote_key[4])
            new_ref = ref_from_key(target_key)
            if not valid_dvb_ref(new_ref):
                plan["unmatched"].append({"path": path, "name": name, "ref": entry.get("ref"), "position": pos, "reason": "niepoprawny wynikowy reference"})
                stats["unmatched"] += 1
                continue
            if new_ref != entry.get("ref"):
                changes[entry["index"]] = "#SERVICE %s" % new_ref
                plan["ref_changes"].append({"path": path, "name": name, "old_ref": entry.get("ref"), "new_ref": new_ref, "position": pos})
                stats["changed"] += 1
            add_db_record(plan, target_key, source_record)

        # Preserve channels already owned by a previous PP Channel Sync block,
        # but drop duplicates which the user moved into the normal bouquet area.
        base_keys = set([x.get("key") for x in entries if x.get("key")])
        base_names = set([normalize_name(x.get("name")) for x in entries if usable_name(x.get("name"))])
        retained = []
        for item in old_owned:
            key = item.get("key")
            name = normalize_name(item.get("name")) if usable_name(item.get("name")) else ""
            if key in base_keys or (name and name in base_names):
                continue
            retained.append(item)
            base_keys.add(key)
            if name:
                base_names.add(name)
            source_record = exact.get(key)
            if source_record and not any(key in (db.get("services") or {}) for db in databases):
                add_db_record(plan, key, source_record)
        plan["retained_owned_channels"] += len(retained)

        local_title = bouquet_title(base_lines, path)
        remote_item = find_remote_bouquet(local_title, entries, remote_bouquets, selected)
        new_items = []
        refresh_owned = False
        if remote_item and local_positions:
            plan["matched_bouquets"] += 1
            refresh_owned = True
            existing_keys = set(base_keys)
            existing_cores = set([key_core(x) for x in existing_keys if x])
            existing_names = set(base_names)
            for remote_entry in remote_item.get("entries") or []:
                pos = remote_entry.get("orbit")
                if pos not in selected or pos not in local_positions:
                    continue
                key = remote_entry.get("key")
                record = exact.get(key)
                ref = remote_entry.get("ref") or ref_from_key(key)
                name = remote_entry.get("name") or (record.get("name") if record else "") or ref
                normalized = normalize_name(name) if usable_name(name) else ""
                if not key or not record or not valid_dvb_ref(ref):
                    continue
                if key in existing_keys or key_core(key) in existing_cores or (normalized and normalized in existing_names):
                    continue
                item = {
                    "service_line": "#SERVICE %s" % ref,
                    "description_line": "#DESCRIPTION %s" % name,
                    "ref": ref,
                    "key": key,
                    "name": name,
                    "position": pos,
                    "remote_bouquet": remote_item.get("title") or "",
                }
                new_items.append(item)
                plan["new_channels"].append({"path": path, "bouquet": local_title, "name": name, "ref": ref, "position": pos, "remote_bouquet": remote_item.get("title") or ""})
                plan["new_channels_planned"] += 1
                plan["per_position"][pos]["added"] += 1
                existing_keys.add(key)
                existing_cores.add(key_core(key))
                if normalized:
                    existing_names.add(normalized)
                add_db_record(plan, key, record)
        elif entries and local_positions:
            plan["unmatched_bouquets"].append(local_title)

        owned_items = retained + new_items
        if changes or owned_blocks or new_items:
            plan["files"][path] = {
                "original_lines": original_lines,
                "lines": base_lines,
                "changes": changes,
                "owned_items": owned_items,
                "refresh_owned": refresh_owned,
                "remote_title": remote_item.get("title") if remote_item else "",
            }
    return plan


def add_db_record(plan, target_key, source_record):
    if not target_key or not source_record:
        return
    plan["db_service_additions"][target_key] = source_record
    source_tkey = key_tkey(source_record.get("key"))
    target_tkey = key_tkey(target_key)
    remote_trans = plan["remote"]["db"].get("transponders", {}).get(source_tkey)
    if remote_trans and target_tkey:
        plan["db_transponder_additions"][target_tkey] = remote_trans


def escape_v5(value):
    return (value or "").replace("\\", "\\\\").replace('"', '\\"')


def service_line_for_db(target_key, source_record, target_format):
    name = source_record.get("name") or "unknown"
    provider = source_record.get("provider") or ""
    if target_format == 5:
        service_number = source_record.get("service_number", "0") if source_record.get("format") == 5 else "0"
        source_id = source_record.get("source_id", "0") if source_record.get("format") == 5 else "0"
        tail = '"%s"' % escape_v5(name)
        if provider:
            tail += ",p:%s" % provider
        return ["s:%s:%s:%s:%s:%s:%s:%s,%s" % (
            target_key[1], target_key[4], target_key[2], target_key[3], target_key[0], service_number, source_id, tail
        )]
    first = "%s:%s:%s:%s:%s:0:0" % (
        target_key[1], target_key[4], target_key[2], target_key[3], ref_type_to_lamedb4(target_key[0])
    )
    lines = [first, name]
    if provider:
        lines.append("p:%s" % provider)
    else:
        lines.append("p:unknown")
    return lines


def transponder_lines_for_db(target_tkey, source_trans, target_format):
    raw_lines = list(source_trans.get("raw") or [])
    if not raw_lines:
        return []
    first = raw_lines[0].strip()
    if target_format == 5:
        suffix = ""
        if first.startswith("t:") and "," in first:
            suffix = first.split(",", 1)[1]
        else:
            for line in raw_lines[1:]:
                value = line.strip()
                if not value or value == "/":
                    continue
                if len(value) > 2 and value[1] == " ":
                    value = value[0] + ":" + value[2:].strip()
                suffix = value
                break
        if not suffix:
            return []
        return ["t:%s:%s:%s,%s" % (target_tkey[0], target_tkey[1], target_tkey[2], suffix)]
    result = ["%s:%s:%s" % target_tkey]
    if first.startswith("t:") and "," in first:
        value = first.split(",", 1)[1].strip()
        if len(value) > 2 and value[1] == ":":
            value = value[0] + " " + value[2:]
        result.append("\t" + value)
    else:
        for line in raw_lines[1:]:
            value = line.strip()
            if not value or value == "/":
                continue
            if len(value) > 2 and value[1] == ":":
                value = value[0] + " " + value[2:]
            result.append("\t" + value)
    return result if len(result) > 1 else []


def append_records_to_database(db, service_additions, trans_additions):
    fresh = parse_lamedb(db["path"])
    if not fresh.get("valid"):
        raise Exception("Nie można ponownie odczytać %s." % db["path"])
    trans_lines = []
    service_lines = []
    expected_services = []
    expected_trans = []
    for tkey, source_trans in trans_additions.items():
        if tkey in fresh.get("transponders", {}):
            continue
        lines = transponder_lines_for_db(tkey, source_trans, fresh["format"])
        if lines:
            trans_lines.extend(lines)
            expected_trans.append(tkey)
    for key, source_record in service_additions.items():
        if key in fresh.get("services", {}):
            continue
        lines = service_line_for_db(key, source_record, fresh["format"])
        if lines:
            service_lines.extend(lines)
            expected_services.append(key)
    if not trans_lines and not service_lines:
        return 0
    lines = list(fresh["lines"])
    trans_insert = int(fresh["trans_insert"])
    service_insert = int(fresh["service_insert"])
    if trans_lines:
        lines[trans_insert:trans_insert] = trans_lines
        if service_insert >= trans_insert:
            service_insert += len(trans_lines)
    if service_lines:
        lines[service_insert:service_insert] = service_lines
    atomic_write(fresh["path"], "\n".join(lines) + "\n")
    verify = parse_lamedb(fresh["path"])
    for key in expected_services:
        if key not in verify.get("services", {}):
            raise Exception("Weryfikacja zapisu usługi w %s nie powiodła się." % fresh["path"])
    for tkey in expected_trans:
        if tkey not in verify.get("transponders", {}):
            raise Exception("Weryfikacja zapisu transpondera w %s nie powiodła się." % fresh["path"])
    return len(expected_services)


def build_owned_new_channel_block(items):
    clean = []
    seen = set()
    for item in items or []:
        ref = (item.get("ref") or "").strip()
        if not valid_dvb_ref(ref) or ref in seen:
            continue
        seen.add(ref)
        name = item.get("name") or ""
        service_line = item.get("service_line") or ("#SERVICE %s" % ref)
        description_line = item.get("description_line") or ("#DESCRIPTION %s" % name)
        clean.append((service_line, description_line))
    if not clean:
        return []
    lines = [
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:",
        "#DESCRIPTION ........ nowe kanały - PP Channel Sync ........",
    ]
    for service_line, description_line in clean:
        lines.append(service_line)
        if description_line:
            lines.append(description_line)
    lines.extend([
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:",
        "#DESCRIPTION ........ koniec - PP Channel Sync ........",
    ])
    return lines


def validate_bouquet_output(path, lines):
    for line in lines or []:
        raw = line.strip()
        if raw and not raw.startswith("#") and re.match(r"^[0-9a-fA-F]+(?::[0-9a-fA-F]+){5,}$", raw):
            raise Exception("W bukiecie wykryto surowy wpis lamedb: %s" % raw)
        if raw.startswith("#SERVICE ") and "FROM BOUQUET" not in raw and not marker_service_line(raw):
            ref = raw[9:].strip()
            if not is_iptv_ref(ref) and key_from_ref(ref) is None:
                raise Exception("Zablokowano niepoprawny service reference w %s: %s" % (path, ref))


def write_bouquet_changes(plan):
    changed = 0
    added = 0
    retained = 0
    for path, item in plan.get("files", {}).items():
        lines = list(item.get("lines") or [])
        for idx, value in item.get("changes", {}).items():
            if idx < 0 or idx >= len(lines) or not value.startswith("#SERVICE "):
                raise Exception("Niepoprawny plan zapisu bukietu %s." % path)
            ref = value[9:].strip()
            if not valid_dvb_ref(ref):
                raise Exception("Zablokowano niepoprawny service reference: %s" % ref)
            lines[idx] = value
        owned_items = item.get("owned_items") or []
        block = build_owned_new_channel_block(owned_items)
        if block:
            lines.extend(block)
        validate_bouquet_output(path, lines)
        expected_refs = set([x.get("ref") for x in owned_items if x.get("ref")])
        new_refs = set([x.get("ref") for x in plan.get("new_channels", []) if x.get("path") == path])
        added += len(new_refs)
        retained += max(0, len(expected_refs) - len(new_refs))
        original = item.get("original_lines") or []
        if lines == original:
            continue
        atomic_write(path, "\n".join(lines) + "\n")
        verify_lines = read_text(path).splitlines()
        validate_bouquet_output(path, verify_lines)
        actual_refs = set([x[9:].strip() for x in verify_lines if x.startswith("#SERVICE ")])
        missing = expected_refs.difference(actual_refs)
        if missing:
            raise Exception("Weryfikacja dopisanych kanałów w %s nie powiodła się: %s" % (path, ", ".join(sorted(missing))))
        changed += 1
    return changed, added, retained


def polish_date_stamp():
    months = ["stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca", "lipca", "sierpnia", "września", "października", "listopada", "grudnia"]
    try:
        return "%d %s %s" % (int(time.strftime("%d")), months[int(time.strftime("%m")) - 1], time.strftime("%Y"))
    except Exception:
        return time.strftime("%d.%m.%Y")


def credit_description(value):
    text = normalize_name(value)
    if not text:
        return False
    if "pp channel sync" in text:
        return True
    creators = ("bzyk83", "bzyk3", "vhannibal", "vannibal", "hannibal", "jakitaki", "jaki taki", "anom", "matzg", "satvenus", "e2settings", "ciefp", "gioppygio")
    if any(x in text for x in creators):
        return True
    if re.search(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b", text):
        return True
    polish_months = "stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|wrzesnia|pazdziernika|listopada|grudnia"
    if re.search(r"\b\d{1,2}\s+(?:%s)\s+\d{4}\b" % polish_months, text):
        return True
    return text.startswith("@ ") or text.startswith("© ")


def update_main_bouquet_footer():
    path = os.path.join(E2_PATH, "bouquets.tv")
    if not os.path.isfile(path):
        return 0
    lines = read_text(path).splitlines()
    out = []
    removed = 0
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        next_desc = lines[idx + 1][13:].strip() if idx + 1 < len(lines) and lines[idx + 1].startswith("#DESCRIPTION ") else ""
        if line.startswith("#SERVICE ") and "FROM BOUQUET" in line:
            out.append(line)
            if next_desc:
                out.append(lines[idx + 1])
                idx += 2
            else:
                idx += 1
            continue
        if marker_service_line(line) and next_desc and credit_description(next_desc):
            removed += 1
            idx += 2
            continue
        if line.startswith("#DESCRIPTION ") and credit_description(line[13:].strip()):
            removed += 1
            idx += 1
            continue
        out.append(line)
        idx += 1
    footer = [
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:",
        "#DESCRIPTION ........ %s ........" % polish_date_stamp(),
        "#SERVICE 1:64:0:0:0:0:0:0:0:0:",
        "#DESCRIPTION @ PP Channel Sync",
    ]
    out.extend(footer)
    validate_bouquet_output(path, out)
    atomic_write(path, "\n".join(out) + "\n")
    verify = read_text(path)
    if "#DESCRIPTION @ PP Channel Sync" not in verify:
        raise Exception("Nie udało się zweryfikować podpisu PP Channel Sync w bouquets.tv.")
    return removed + 1


def backup_sources():
    files = []
    try:
        for name in os.listdir(E2_PATH):
            if name in ("lamedb", "lamedb5", "bouquets.tv", "bouquets.radio") or (name.startswith("userbouquet.") and (name.endswith(".tv") or name.endswith(".radio"))):
                path = os.path.join(E2_PATH, name)
                if os.path.isfile(path):
                    files.append(path)
    except Exception:
        pass
    return sorted(files)


def prune_backups():
    ensure_dir(BACKUP_DIR)
    files = sorted([os.path.join(BACKUP_DIR, x) for x in os.listdir(BACKUP_DIR) if x.endswith(".tar.gz")], reverse=True)
    for path in files[BACKUP_KEEP:]:
        try:
            os.unlink(path)
        except Exception:
            pass


def make_backup():
    ensure_dir(BACKUP_DIR)
    files = backup_sources()
    if not files:
        raise Exception("Nie znaleziono plików listy do wykonania kopii.")
    path = os.path.join(BACKUP_DIR, "ppchannelsync_%s.tar.gz" % time.strftime("%Y%m%d_%H%M%S"))
    with tarfile.open(path, "w:gz") as archive:
        for source in files:
            archive.add(source, arcname=os.path.basename(source), recursive=False)
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
    if not any(x in names for x in ("lamedb", "lamedb5")):
        raise Exception("Kopia nie zawiera lamedb ani lamedb5.")
    prune_backups()
    return path


def latest_backup():
    if not os.path.isdir(BACKUP_DIR):
        return None
    files = sorted([os.path.join(BACKUP_DIR, x) for x in os.listdir(BACKUP_DIR) if x.endswith(".tar.gz")], reverse=True)
    return files[0] if files else None


def restore_backup(path):
    if not path or not os.path.isfile(path):
        raise Exception("Brak kopii bezpieczeństwa.")
    with tarfile.open(path, "r:gz") as archive:
        members = []
        for member in archive.getmembers():
            name = os.path.basename(member.name)
            allowed = name in ("lamedb", "lamedb5", "bouquets.tv", "bouquets.radio") or (name.startswith("userbouquet.") and (name.endswith(".tv") or name.endswith(".radio")))
            if not allowed or member.name != name or not member.isfile():
                raise Exception("Kopia zawiera niedozwolony wpis: %s" % member.name)
            safe_target(E2_PATH, name)
            members.append(member)
        archive.extractall(E2_PATH, members=members)
    reload_bouquets()


def legacy_artifacts():
    found = []
    for path in bouquet_files():
        try:
            text = read_text(path)
            if re.search(r"#DESCRIPTION .*nowe kana.*PP Channel Sync", text, re.I):
                found.append(path)
        except Exception:
            pass
    main = os.path.join(E2_PATH, "bouquets.tv")
    if os.path.isfile(main):
        try:
            if re.search(r"#DESCRIPTION .*PP Channel Sync", read_text(main), re.I):
                found.append(main)
        except Exception:
            pass
    dedicated = os.path.join(E2_PATH, "userbouquet.ppchannelsync_new.tv")
    if os.path.isfile(dedicated):
        found.append(dedicated)
    return sorted(set(found))


def remove_legacy_artifacts():
    changed = 0
    removed_lines = 0
    for path in bouquet_files():
        try:
            lines = read_text(path).splitlines()
            cut = None
            for idx, line in enumerate(lines):
                if line.startswith("#DESCRIPTION ") and re.search(r"nowe kana.*PP Channel Sync", line, re.I):
                    cut = idx - 1 if idx > 0 and lines[idx - 1].startswith("#SERVICE ") else idx
                    break
            if cut is not None:
                removed_lines += len(lines) - cut
                atomic_write(path, "\n".join(lines[:cut]) + "\n")
                changed += 1
        except Exception:
            pass
    main = os.path.join(E2_PATH, "bouquets.tv")
    if os.path.isfile(main):
        lines = read_text(main).splitlines()
        out = []
        idx = 0
        dirty = False
        while idx < len(lines):
            line = lines[idx]
            next_line = lines[idx + 1] if idx + 1 < len(lines) else ""
            if line.startswith("#SERVICE ") and "FROM BOUQUET" not in line and next_line.startswith("#DESCRIPTION ") and "PP Channel Sync" in next_line:
                dirty = True
                removed_lines += 2
                idx += 2
                continue
            if "FROM BOUQUET" in line and "userbouquet.ppchannelsync_new.tv" in line:
                dirty = True
                removed_lines += 1
                idx += 1
                if idx < len(lines) and lines[idx].startswith("#DESCRIPTION "):
                    removed_lines += 1
                    idx += 1
                continue
            out.append(line)
            idx += 1
        if dirty:
            atomic_write(main, "\n".join(out) + "\n")
            changed += 1
    dedicated = os.path.join(E2_PATH, "userbouquet.ppchannelsync_new.tv")
    if os.path.isfile(dedicated):
        try:
            os.unlink(dedicated)
            changed += 1
        except Exception:
            pass
    return changed, removed_lines


def reload_bouquets():
    try:
        from enigma import eDVBDB
        db = eDVBDB.getInstance()
        try:
            db.reloadServicelist()
        except Exception:
            pass
        try:
            db.reloadBouquets()
        except Exception:
            pass
        return True
    except Exception:
        return False


def write_report(plan, mode, backup=None, changed_files=0, db_added=0, legacy=None, added_channels=0, retained_channels=0, footer_updates=0):
    lines = []
    details = []
    lines.append("PP Channel Sync v%s" % PLUGIN_VERSION)
    lines.append(AUTHOR)
    lines.append("Data: %s" % time.strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("Źródło: %s" % plan["remote"].get("label"))
    lines.append("Satelity: %s" % ", ".join([orbital_label(x) for x in sorted(plan["selected"])]))
    lines.append("Tryb: %s" % MODE_LABELS[mode])
    lines.append("")
    lines.append("Sprawdzone kanały: %d" % plan.get("checked", 0))
    lines.append("Bez zmian: %d" % plan.get("unchanged", 0))
    lines.append("Poprawione service reference: %d" % len(plan.get("ref_changes", [])))
    lines.append("Naprawione brakujące wpisy lamedb: %d" % len(plan.get("aliases", [])))
    lines.append("Niejednoznaczne: %d" % len(plan.get("ambiguous", [])))
    lines.append("Bez dopasowania: %d" % len(plan.get("unmatched", [])))
    lines.append("Pasujące bukiety kontrolne: %d" % plan.get("matched_bouquets", 0))
    lines.append("Nowe kanały wykryte do dopisania: %d" % plan.get("new_channels_planned", 0))
    if mode == MODE_SYNC:
        lines.append("Nowe kanały dopisane na dole bukietów: %d" % added_channels)
        lines.append("Zachowane kanały z wcześniejszego bloku wtyczki: %d" % retained_channels)
        lines.append("Zmienione pliki bukietów: %d" % changed_files)
        lines.append("Dopisane rekordy techniczne do baz: %d" % db_added)
        lines.append("Podpis i data w widoku bukietów: %s" % ("zaktualizowane" if footer_updates else "bez zmian"))
        lines.append("Kopia: %s" % (backup or "brak"))
    else:
        lines.append("Zapis: NIE — raport nie zmienił listy")
    lines.append("Usunięte kanały: 0")
    if legacy:
        lines.append("Usunięte ślady wersji 1.x: %d plików / %d linii" % (legacy[0], legacy[1]))
    if plan.get("missing_remote_positions"):
        lines.append("Brak pozycji w źródle: %s" % ", ".join([orbital_label(x) for x in plan["missing_remote_positions"]]))
    if plan.get("unmatched_bouquets"):
        lines.append("Bukiety bez pewnego dopasowania: %d" % len(plan.get("unmatched_bouquets")))
    lines.append("")
    lines.append("Wynik dla każdej satelity:")
    for pos, stat in plan.get("per_position", {}).items():
        lines.append("- %s: sprawdzone %d, poprawione %d, lamedb %d, nowe %d, niejednoznaczne %d, brak %d" % (
            orbital_label(pos), stat["checked"], stat["changed"], stat["aliases"], stat.get("added", 0), stat["ambiguous"], stat["unmatched"]
        ))

    details.extend(lines)
    details.append("")
    details.append("--- NOWE KANAŁY DO DOPISANIA ---")
    for item in plan.get("new_channels", []):
        details.append("[%s] %s -> %s | %s" % (orbital_label(item["position"]), item.get("bouquet"), item.get("name"), item.get("ref")))
    details.append("")
    details.append("--- POPRAWIONE REFERENCE ---")
    for item in plan.get("ref_changes", []):
        details.append("[%s] %s\n  %s\n  -> %s" % (orbital_label(item["position"]), item["name"], item["old_ref"], item["new_ref"]))
    details.append("")
    details.append("--- NAPRAWIONE WPISY LAMEDB ---")
    for item in plan.get("aliases", []):
        details.append("[%s] %s | %s" % (orbital_label(item["position"]), item["name"], ref_from_key(item["key"])))
    details.append("")
    details.append("--- NIEJEDNOZNACZNE / BRAK ---")
    for item in plan.get("ambiguous", []) + plan.get("unmatched", []):
        details.append("[%s] %s | %s | %s" % (orbital_label(item["position"]), item["name"], item["ref"], item["reason"]))
    atomic_write(REPORT_PATH, "\n".join(lines) + "\n")
    atomic_write(DETAIL_REPORT_PATH, "\n".join(details) + "\n")
    return "\n".join(lines)


def execute_sync(selected_positions, mode, clean_legacy=False):
    remote = load_remote_motor()
    plan = build_plan(selected_positions, remote)
    if mode == MODE_REPORT:
        return write_report(plan, mode), plan
    backup = make_backup()
    legacy_result = None
    try:
        if clean_legacy:
            legacy_result = remove_legacy_artifacts()
            plan = build_plan(selected_positions, remote)
        db_added = 0
        for db in plan["databases"]:
            db_added += append_records_to_database(db, plan["db_service_additions"], plan["db_transponder_additions"])
        changed_files, added_channels, retained_channels = write_bouquet_changes(plan)
        footer_updates = update_main_bouquet_footer()
        reload_bouquets()
        summary = write_report(plan, mode, backup, changed_files, db_added, legacy_result, added_channels, retained_channels, footer_updates)
        return summary, plan
    except Exception:
        try:
            restore_backup(backup)
        except Exception as restore_error:
            raise Exception("Synchronizacja została przerwana. Nie udało się przywrócić kopii: %s\n\n%s" % (str(restore_error), traceback.format_exc()))
        raise Exception("Synchronizacja została przerwana i cofnięta z kopii.\n\n%s" % traceback.format_exc())


def version_tuple(value):
    parts = []
    for item in re.findall(r"\d+", str(value or ""))[:4]:
        try:
            parts.append(int(item))
        except Exception:
            parts.append(0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def download_update(manifest):
    url = manifest.get("url") or manifest.get("ipk_url") or manifest.get("download_url")
    if not url:
        raise Exception("update.json nie zawiera adresu IPK.")
    path = "/tmp/enigma2-plugin-extensions-ppchannelsync_%s_all.ipk" % manifest.get("version", "update")
    with open(path, "wb") as handle:
        handle.write(download_bytes(url))
    expected = (manifest.get("sha256") or "").strip().lower()
    if expected and sha256_file(path).lower() != expected:
        raise Exception("Suma SHA256 pobranego IPK jest niepoprawna.")
    return path


def install_ipk(path):
    commands = [
        ["opkg", "install", "--force-reinstall", path],
        ["dpkg", "-i", path],
    ]
    errors = []
    for command in commands:
        try:
            proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out, err = proc.communicate()
            if proc.returncode == 0:
                atomic_write(UPDATE_INFO_PATH, (out + b"\n" + err).decode("utf-8", "ignore"))
                return True
            errors.append("%s: %s" % (" ".join(command), err.decode("utf-8", "ignore")))
        except Exception as exc:
            errors.append(str(exc))
    raise Exception("Instalacja IPK nie powiodła się.\n" + "\n".join(errors))


def append_history(text):
    try:
        ensure_dir(os.path.dirname(HISTORY_PATH))
        line = "%s | v%s | %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), PLUGIN_VERSION, str(text).replace("\n", " ")[:500])
        with open(HISTORY_PATH, "ab") as handle:
            handle.write(line.encode("utf-8", "ignore"))
    except Exception:
        pass


def create_diagnostics(selected_positions=None):
    lines = [
        "PP Channel Sync v%s - diagnostyka" % PLUGIN_VERSION,
        "Data: %s" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "Autor: %s" % AUTHOR,
        "",
    ]
    try:
        import sys
        lines.append("Python: %s" % sys.version.replace("\n", " "))
    except Exception:
        pass
    configured = configured_positions_from_settings()
    detected = detect_positions()
    lines.append("Satelity skonfigurowane w głowicach: %s" % (", ".join([orbital_label(x) for x in configured]) or "brak/nie wykryto"))
    lines.append("Satelity wykryte w liście i lamedb: %s" % (", ".join([orbital_label(x) for x in detected]) or "brak"))
    lines.append("Satelity zaznaczone we wtyczce: %s" % (", ".join([orbital_label(x) for x in sorted(selected_positions or [])]) or "brak"))
    lines.append("")
    databases = valid_local_databases()
    if not databases:
        lines.append("Baza kanałów: BRAK poprawnego lamedb/lamedb5")
    for db in databases:
        lines.append("Baza: %s | format /%s/ | usługi: %d | transpondery: %d" % (
            db.get("path"), db.get("format"), len(db.get("services") or {}), len(db.get("transponders") or {})
        ))
    bfiles = bouquet_files()
    lines.append("Bukiety TV: %d" % len(bfiles))
    sat_entries = 0
    per_position = {}
    for path in bfiles:
        try:
            _raw, entries = parse_bouquet(path, databases)
            sat_entries += len(entries)
            for entry in entries:
                pos = entry.get("orbit")
                if pos:
                    per_position[pos] = per_position.get(pos, 0) + 1
        except Exception as exc:
            lines.append("Błąd odczytu %s: %s" % (os.path.basename(path), str(exc)))
    lines.append("Pozycje DVB-S w bukietach: %d" % sat_entries)
    for pos in sorted(per_position):
        lines.append("- %s: %d" % (orbital_label(pos), per_position[pos]))
    lines.append("")
    lines.append("Ostatni raport: %s" % ("jest" if os.path.isfile(REPORT_PATH) else "brak"))
    lines.append("Ostatni błąd: %s" % ("jest" if os.path.isfile(ERROR_PATH) else "brak"))
    atomic_write(DIAGNOSTIC_PATH, "\n".join(lines) + "\n")
    return "\n".join(lines)


def create_support_zip(selected_positions=None):
    create_diagnostics(selected_positions)
    try:
        if os.path.isfile(SUPPORT_ZIP_PATH):
            os.unlink(SUPPORT_ZIP_PATH)
    except Exception:
        pass
    with zipfile.ZipFile(SUPPORT_ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in (DIAGNOSTIC_PATH, REPORT_PATH, DETAIL_REPORT_PATH, ERROR_PATH, UPDATE_INFO_PATH, HISTORY_PATH):
            if os.path.isfile(path):
                archive.write(path, os.path.basename(path))
    return SUPPORT_ZIP_PATH


class SatelliteSelectScreen(Screen):
    skin = """
    <screen name="SatelliteSelectScreen" position="center,center" size="1050,650" title="PP Channel Sync - satelity">
        <eLabel position="0,0" size="1050,650" backgroundColor="#08111b" zPosition="-5" />
        <eLabel position="10,10" size="1030,630" backgroundColor="#101c29" zPosition="-4" />
        <eLabel position="18,18" size="1014,70" backgroundColor="#123a5a" zPosition="-3" />
        <eLabel position="38,170" size="974,340" backgroundColor="#071016" zPosition="-3" />
        <widget name="title" position="42,31" size="760,40" font="Regular;34" foregroundColor="#00c8ff" backgroundColor="#123a5a" transparent="1" zPosition="5" />
        <widget name="help" position="42,102" size="960,56" font="Regular;22" foregroundColor="#eeeeee" backgroundColor="#101c29" transparent="1" zPosition="5" />
        <widget name="menu" position="52,180" size="944,315" scrollbarMode="showOnDemand" foregroundColor="#ffffff" foregroundColorSelected="#ffffff" backgroundColor="#071016" backgroundColorSelected="#1f5f95" transparent="0" zPosition="5" />
        <widget name="hint" position="42,522" size="950,35" font="Regular;21" foregroundColor="#b8b8b8" backgroundColor="#101c29" transparent="1" zPosition="5" />
        <eLabel position="42,580" size="290,46" backgroundColor="#421010" zPosition="-1" />
        <eLabel position="360,580" size="290,46" backgroundColor="#0d3818" zPosition="-1" />
        <widget name="key_red" position="60,590" size="255,28" font="Regular;22" foregroundColor="#ff4545" backgroundColor="#421010" transparent="1" zPosition="5" />
        <widget name="key_green" position="378,590" size="255,28" font="Regular;22" foregroundColor="#42ff70" backgroundColor="#0d3818" transparent="1" zPosition="5" />
    </screen>
    """

    def __init__(self, session, positions, selected):
        Screen.__init__(self, session)
        self.positions = list(positions or [])
        self.selected = set(selected or [])
        self["title"] = Label(_("Wybór satelitów"))
        self["help"] = Label(_("Wybierz pozycje orbitalne, które mają zostać sprawdzone. OK zaznacza lub odznacza pozycję."))
        self["hint"] = Label("Pozycje pochodzą z bukietów, lamedb oraz konfiguracji głowic tunera.")
        self["key_red"] = Label(_("Anuluj"))
        self["key_green"] = Label(_("Zapisz"))
        self["menu"] = MenuList([])
        try:
            from enigma import gFont
            self["menu"].l.setFont(0, gFont("Regular", 28))
            self["menu"].l.setItemHeight(43)
        except Exception:
            pass
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.toggle,
            "cancel": self.cancel,
            "red": self.cancel,
            "green": self.save,
        }, -1)
        self.refresh()

    def refresh(self):
        self["menu"].setList(["[%s]  %s" % ("X" if pos in self.selected else " ", orbital_label(pos)) for pos in self.positions])

    def current_index(self):
        try:
            return self["menu"].getCurrentIndex()
        except Exception:
            return 0

    def toggle(self):
        idx = self.current_index()
        if idx < 0 or idx >= len(self.positions):
            return
        pos = self.positions[idx]
        if pos in self.selected:
            self.selected.remove(pos)
        else:
            self.selected.add(pos)
        self.refresh()
        try:
            self["menu"].moveToIndex(idx)
        except Exception:
            pass

    def cancel(self):
        # openWithCallback must always receive one value; closing without it
        # caused the GSOD in 2.0.0 on OpenATV 8.
        self.close(None)

    def save(self):
        if not self.selected:
            self.session.open(MessageBox, _("Nie wybrano żadnej satelity."), type=MessageBox.TYPE_ERROR)
            return
        self.close(sorted(self.selected))


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
        <widget name="menu" position="52,142" size="720,365" scrollbarMode="showOnDemand" foregroundColor="#ffffff" foregroundColorSelected="#ffffff" backgroundColor="#071016" backgroundColorSelected="#1f5f95" transparent="0" zPosition="5" />
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
        settings = load_settings()
        detected = detect_positions()
        saved = settings.get("positions") or []
        self.positions = sorted(set(saved if saved else detected))
        self.mode = settings.get("mode", MODE_SYNC)
        self["title"] = Label("PP Channel Sync")
        try:
            self.setTitle("PP Channel Sync v%s" % PLUGIN_VERSION)
        except Exception:
            pass
        self["version"] = Label("v%s" % PLUGIN_VERSION)
        self["status"] = Label("OK - opcja | Zielony - start | Żółty - wybór satelitów | Niebieski - przywróć")
        self["side_title"] = Label(_("Informacje"))
        self["side_info"] = Label("")
        self["support_title"] = Label(_("Wesprzyj"))
        self["support_text"] = Label(_("Pomóż rozwijać\nlokalne projekty"))
        self["help"] = Label("OK - funkcja  |  LEWO/PRAWO - zmiana trybu  |  MENU - raport  |  EXIT - wyjście")
        self["footer"] = Label("%s  •  %s  •  Enigma2 Python 2/3  •  FB: Enigma 2 Oprogramowanie, dodatki" % (AUTHOR, CONTACT))
        self["key_red"] = Label("Czerwony: wyjście")
        self["key_green"] = Label("Zielony: uruchom")
        self["key_yellow"] = Label("Żółty: satelity")
        self["key_blue"] = Label("Niebieski: przywróć")
        self["menu"] = MenuList([])
        try:
            from enigma import gFont
            self["menu"].l.setFont(0, gFont("Regular", 25))
            self["menu"].l.setItemHeight(38)
            self["menu"].onSelectionChanged.append(self.update_info)
        except Exception:
            pass
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions", "DirectionActions", "MenuActions"], {
            "ok": self.ok,
            "cancel": self.close,
            "red": self.close,
            "green": self.run_sync,
            "yellow": self.select_satellites,
            "blue": self.restore_last,
            "left": self.left_right,
            "right": self.left_right,
            "menu": self.show_report,
            "up": self.up,
            "down": self.down,
        }, -1)
        self.refresh()

    def menu_data(self):
        sats = ", ".join([orbital_label(x) for x in sorted(self.positions)]) if self.positions else "brak"
        return [
            ("satellites", "%s: %s" % (_("Wybrane satelity"), sats), "Wybierz dowolną liczbę pozycji orbitalnych. Lista jest budowana z bukietów, lamedb oraz konfiguracji głowic."),
            ("mode", "%s: %s" % (_("Tryb pracy"), _(MODE_LABELS[self.mode])), "Raport nie zapisuje zmian. Bezpieczna korekta poprawia istniejące wpisy i dopisuje pewne nowe kanały na końcu pasujących bukietów."),
            ("check", _("Sprawdź listę"), "Pobiera bazę kontrolną i tworzy raport dla wszystkich zaznaczonych satelitów bez modyfikacji listy."),
            ("run", _("Uruchom synchronizację"), _("Wtyczka poprawia istniejące kanały DVB-S i dopisuje pewne nowe kanały na końcu pasujących bukietów. Nie usuwa kanałów i nie zmienia kolejności istniejących pozycji.")),
            ("cleanup", _("Napraw ślady wersji 1.x"), "Usuwa wyłącznie rozpoznawalne bloki i błędne dopiski utworzone przez wersje 1.x. Przed operacją wykonywana jest kopia."),
            ("report", _("Pokaż ostatni raport"), "Pokazuje czytelne podsumowanie ostatniego sprawdzenia lub korekty."),
            ("details", _("Pokaż raport techniczny"), "Pokazuje szczegóły: zmienione reference, brakujące rekordy i wynik osobno dla każdej satelity."),
            ("backup", _("Utwórz kopię bezpieczeństwa"), "Tworzy natychmiastową kopię lamedb, lamedb5 oraz wszystkich bukietów TV i radio."),
            ("restore", _("Przywróć ostatnią kopię"), "Przywraca ostatnią kompletną kopię wykonaną przez PP Channel Sync."),
            ("diagnostics", _("Diagnostyka systemu"), "Sprawdza wykryte satelity, format bazy kanałów, liczbę usług i bukietów bez zmieniania listy."),
            ("support", _("Przygotuj raport do wysłania"), "Tworzy archiwum ZIP z raportami i diagnostyką w /tmp/ppchannelsync_support.zip."),
            ("update", _("Aktualizuj wtyczkę z GitHub"), "Sprawdza update.json, pobiera IPK, kontroluje SHA256 i instaluje nowszą wersję."),
            ("info", _("Informacje"), "Bezpieczny rdzeń wielosatelitarny: dopisywanie pewnych nowych kanałów bez zmiany kolejności, brak automatycznego usuwania, kopia i rollback."),
        ]

    def refresh(self):
        self._items = self.menu_data()
        self["menu"].setList([x[1] for x in self._items])
        self.update_info()
        save_settings(self.mode, self.positions)

    def up(self):
        try:
            self["menu"].up()
        except Exception:
            pass
        self.update_info()

    def down(self):
        try:
            self["menu"].down()
        except Exception:
            pass
        self.update_info()

    def current_index(self):
        try:
            return self["menu"].getCurrentIndex()
        except Exception:
            return 0

    def current(self):
        idx = self.current_index()
        if idx < 0 or idx >= len(self._items):
            return self._items[0]
        return self._items[idx]

    def update_info(self):
        try:
            item = self.current()
            self["side_title"].setText("Opis opcji")
            self["side_info"].setText(item[2])
        except Exception:
            pass

    def left_right(self):
        if self.current()[0] == "mode":
            self.mode = MODE_REPORT if self.mode == MODE_SYNC else MODE_SYNC
            self.refresh()

    def ok(self):
        action = self.current()[0]
        if action == "satellites":
            self.select_satellites()
        elif action == "mode":
            self.left_right()
        elif action == "check":
            self.run_report()
        elif action == "run":
            self.run_sync()
        elif action == "cleanup":
            self.cleanup_legacy()
        elif action == "report":
            self.show_report()
        elif action == "details":
            self.show_details()
        elif action == "backup":
            self.backup_now()
        elif action == "restore":
            self.restore_last()
        elif action == "diagnostics":
            self.show_diagnostics()
        elif action == "support":
            self.make_support_zip()
        elif action == "update":
            self.check_update()
        elif action == "info":
            self.show_info()

    def popup(self, text, kind=MessageBox.TYPE_INFO):
        try:
            self.session.open(MessageBox, text, type=kind)
        except Exception:
            try:
                atomic_write(ERROR_PATH, str(text) + "\n")
                self["status"].setText(str(text).replace("\n", " ")[:140])
            except Exception:
                pass

    def select_satellites(self):
        detected = detect_positions()
        positions = sorted(set(detected + list(self.positions or [])))
        if not positions:
            self.popup(_("Brak wykrytych satelitów w lokalnej liście."), MessageBox.TYPE_ERROR)
            return
        self.session.openWithCallback(self.satellites_selected, SatelliteSelectScreen, positions, self.positions)

    def satellites_selected(self, selected=None):
        # selected=None means the selector was cancelled. The optional argument
        # is required because some Enigma2 images call callbacks without a value.
        if selected is not None:
            self.positions = list(selected)
            self.refresh()

    def run_report(self):
        self._run_with_mode(MODE_REPORT)

    def run_sync(self):
        self._run_with_mode(self.mode)

    def _run_with_mode(self, requested_mode):
        if not self.positions:
            self.popup(_("Nie wybrano żadnej satelity."), MessageBox.TYPE_ERROR)
            return
        clean = bool(legacy_artifacts())
        question = "Uruchomić %s dla: %s?" % (_(MODE_LABELS[requested_mode]), ", ".join([orbital_label(x) for x in sorted(self.positions)]))
        if clean and requested_mode == MODE_SYNC:
            question += "\n\nWykryto ślady wersji 1.x. Zostaną usunięte z kopią bezpieczeństwa przed korektą."
        self.session.openWithCallback(lambda answer=None: self._run_confirmed(answer, clean, requested_mode), MessageBox, question, type=MessageBox.TYPE_YESNO, default=True)

    def _run_confirmed(self, answer=None, clean=False, requested_mode=MODE_REPORT):
        if not answer:
            return
        try:
            self["status"].setText("Pobieranie bazy i analiza wszystkich wybranych satelitów...")
            summary, plan = execute_sync(self.positions, requested_mode, clean_legacy=clean and requested_mode == MODE_SYNC)
            self["status"].setText("Zakończono. Raport: %s" % REPORT_PATH)
            append_history("%s | satelity %s | sprawdzone %d | zmiany %d" % (
                MODE_LABELS[requested_mode], ",".join([orbital_label(x) for x in sorted(self.positions)]), plan.get("checked", 0), len(plan.get("ref_changes", []))
            ))
            self.popup(summary)
        except Exception as exc:
            try:
                atomic_write(ERROR_PATH, "%s\n\n%s" % (str(exc), traceback.format_exc()))
            except Exception:
                pass
            self["status"].setText("Błąd. Szczegóły: %s" % ERROR_PATH)
            self.popup("Nie udało się wykonać synchronizacji:\n%s\n\nSzczegóły: %s" % (str(exc), ERROR_PATH), MessageBox.TYPE_ERROR)

    def cleanup_legacy(self):
        found = legacy_artifacts()
        if not found:
            self.popup("Nie znaleziono śladów dopisanych przez wersje 1.x.")
            return
        self.session.openWithCallback(self._cleanup_confirmed, MessageBox, "Usunąć ślady wersji 1.x?\n\nZostanie wykonana kopia bezpieczeństwa. Usuwane są tylko rozpoznawalne bloki PP Channel Sync.", type=MessageBox.TYPE_YESNO, default=False)

    def _cleanup_confirmed(self, answer=None):
        if not answer:
            return
        backup = make_backup()
        try:
            changed, removed = remove_legacy_artifacts()
            reload_bouquets()
            append_history("naprawa śladów 1.x | pliki %d | linie %d" % (changed, removed))
            self.popup("Naprawa zakończona.\n\nZmienione pliki: %d\nUsunięte linie: %d\nKopia: %s" % (changed, removed, backup))
        except Exception as exc:
            restore_backup(backup)
            self.popup("Naprawa została przerwana i cofnięta:\n%s" % str(exc), MessageBox.TYPE_ERROR)

    def show_report(self):
        if not os.path.isfile(REPORT_PATH):
            self.popup("Brak raportu.")
            return
        text = read_text(REPORT_PATH)
        if len(text) > 5600:
            text = text[:5600] + "\n\n...\nPełny raport: %s" % REPORT_PATH
        self.popup(text)

    def show_details(self):
        if not os.path.isfile(DETAIL_REPORT_PATH):
            self.popup("Brak raportu technicznego.")
            return
        text = read_text(DETAIL_REPORT_PATH)
        if len(text) > 5600:
            text = text[:5600] + "\n\n...\nPełny raport: %s" % DETAIL_REPORT_PATH
        self.popup(text)

    def backup_now(self):
        try:
            path = make_backup()
            append_history("ręczna kopia | %s" % path)
            self.popup("Kopia bezpieczeństwa została utworzona:\n%s" % path)
        except Exception as exc:
            self.popup("Nie udało się utworzyć kopii:\n%s" % str(exc), MessageBox.TYPE_ERROR)

    def restore_last(self):
        path = latest_backup()
        if not path:
            self.popup("Brak kopii bezpieczeństwa.", MessageBox.TYPE_ERROR)
            return
        self.session.openWithCallback(lambda answer=None: self._restore_confirmed(answer, path), MessageBox, "Przywrócić ostatnią kopię?\n\n%s" % path, type=MessageBox.TYPE_YESNO, default=False)

    def _restore_confirmed(self, answer=None, path=None):
        if not answer:
            return
        try:
            restore_backup(path)
            append_history("przywrócono kopię | %s" % path)
            self.popup("Przywrócono kopię:\n%s" % path)
        except Exception as exc:
            self.popup("Nie udało się przywrócić kopii:\n%s" % str(exc), MessageBox.TYPE_ERROR)

    def show_diagnostics(self):
        try:
            text = create_diagnostics(self.positions)
            if len(text) > 5600:
                text = text[:5600] + "\n\n...\nPełna diagnostyka: %s" % DIAGNOSTIC_PATH
            self.popup(text)
        except Exception as exc:
            self.popup("Nie udało się wykonać diagnostyki:\n%s" % str(exc), MessageBox.TYPE_ERROR)

    def make_support_zip(self):
        try:
            path = create_support_zip(self.positions)
            self.popup("Raport do wysłania został utworzony:\n%s" % path)
        except Exception as exc:
            self.popup("Nie udało się utworzyć raportu ZIP:\n%s" % str(exc), MessageBox.TYPE_ERROR)

    def check_update(self):
        try:
            manifest = fetch_json(UPDATE_MANIFEST_URL)
            remote_version = manifest.get("version") or manifest.get("latest_version")
            if not remote_version:
                raise Exception("Brak pola version w update.json.")
            if version_tuple(remote_version) <= version_tuple(PLUGIN_VERSION):
                self.popup("Wtyczka jest aktualna.\n\nZainstalowana: %s\nNa GitHub: %s" % (PLUGIN_VERSION, remote_version))
                return
            notes = manifest.get("notes") or ""
            if isinstance(notes, list):
                notes = "\n".join(["- " + str(x) for x in notes])
            text = "Dostępna aktualizacja %s.\n\n%s\n\nPobrać i zainstalować?" % (remote_version, notes[:1400])
            self.session.openWithCallback(lambda answer=None: self._update_confirmed(answer, manifest), MessageBox, text, type=MessageBox.TYPE_YESNO, default=True)
        except Exception as exc:
            self.popup("Nie udało się sprawdzić aktualizacji:\n%s" % str(exc), MessageBox.TYPE_ERROR)

    def _update_confirmed(self, answer=None, manifest=None):
        if not answer:
            return
        try:
            path = download_update(manifest)
            install_ipk(path)
            self.popup("Aktualizacja została zainstalowana. Wykonaj restart GUI.")
        except Exception as exc:
            self.popup("Nie udało się zainstalować aktualizacji:\n%s" % str(exc), MessageBox.TYPE_ERROR)

    def show_info(self):
        text = "PP Channel Sync v%s\n%s\n%s\n\nZasady działania:\n- prawdziwy wybór wielu satelitów,\n- każda zaznaczona pozycja jest analizowana osobno,\n- nowe kanały dopisywane na końcu pasujących bukietów,\n- data i podpis PP Channel Sync na dole listy bukietów,\n- brak automatycznego usuwania kanałów,\n- natywna obsługa lamedb /4/ i lamedb5 /5/,\n- kopia i automatyczny rollback przy błędzie,\n- raport oraz diagnostyka do wysłania autorowi." % (PLUGIN_VERSION, AUTHOR, CONTACT)
        self.popup(text)


def main(session, **kwargs):
    session.open(PPChannelSyncScreen)


def Plugins(**kwargs):
    return [PluginDescriptor(
        name=PLUGIN_NAME,
        description="PP Channel Sync 2.1.0 - korekta wielu satelitów i nowe kanały",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        icon="plugin.png",
        fnc=main,
    )]
