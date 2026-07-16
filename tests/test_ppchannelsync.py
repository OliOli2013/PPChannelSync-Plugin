# -*- coding: utf-8 -*-
from __future__ import print_function
import os, sys, types, tempfile, shutil, zipfile, tarfile, importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PLUGIN_PATH = os.path.join(ROOT, 'usr', 'lib', 'enigma2', 'python', 'Plugins', 'Extensions', 'PPChannelSync', 'plugin.py')

# Minimal Enigma2 stubs needed only to import the module outside a receiver.
def install_stubs():
    modules = {
        'Plugins': types.ModuleType('Plugins'),
        'Plugins.Plugin': types.ModuleType('Plugins.Plugin'),
        'Screens': types.ModuleType('Screens'),
        'Screens.Screen': types.ModuleType('Screens.Screen'),
        'Screens.MessageBox': types.ModuleType('Screens.MessageBox'),
        'Components': types.ModuleType('Components'),
        'Components.ActionMap': types.ModuleType('Components.ActionMap'),
        'Components.Label': types.ModuleType('Components.Label'),
        'Components.MenuList': types.ModuleType('Components.MenuList'),
    }
    class PluginDescriptor(object):
        WHERE_PLUGINMENU = 1
        WHERE_SESSIONSTART = 2
        def __init__(self, *args, **kwargs): pass
    class Screen(object):
        def __init__(self, *args, **kwargs): pass
    class MessageBox(object):
        TYPE_INFO = 0
        TYPE_ERROR = 1
        TYPE_YESNO = 2
    class Dummy(object):
        def __init__(self, *args, **kwargs): pass
    modules['Plugins.Plugin'].PluginDescriptor = PluginDescriptor
    modules['Screens.Screen'].Screen = Screen
    modules['Screens.MessageBox'].MessageBox = MessageBox
    modules['Components.ActionMap'].ActionMap = Dummy
    modules['Components.Label'].Label = Dummy
    modules['Components.MenuList'].MenuList = Dummy
    sys.modules.update(modules)


def lamedb4(service_count=6):
    lines = ['eDVB services /4/', 'transponders', '82000000:1:1', '\ts 12345000:27500000:0:3:130:2:0', '/', 'services']
    for i in range(1, service_count + 1):
        lines += ['%x:82000000:1:1:1:0:0' % i, 'Channel %d' % i, 'p:Provider']
    lines += ['/', 'end', '']
    return '\n'.join(lines)


def lamedb5(service_count=6):
    lines = ['eDVB services /5/', 'transponders', 't:82000000:1:1', 's:12345000:27500000:0:3:130:2:0', '/', 'services']
    for i in range(1, service_count + 1):
        lines += ['s:1:0:1:%x:1:1:82000000:0:0:0:' % i, 'Channel %d' % i, 'p:Provider']
    lines += ['/', 'end', '']
    return '\n'.join(lines)


def write(path, data):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent): os.makedirs(parent)
    with open(path, 'wb') as f:
        f.write(data.encode('utf-8') if isinstance(data, str) else data)


def read(path):
    with open(path, 'rb') as f: return f.read()


def check(cond, msg):
    if not cond: raise AssertionError(msg)

install_stubs()
spec = importlib.util.spec_from_file_location('ppchannelsync_plugin', PLUGIN_PATH)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
check(p.PLUGIN_VERSION == '1.3.0', 'wrong plugin version')

root = tempfile.mkdtemp(prefix='ppcs_test_')
try:
    # 1. Regression: package with only lamedb5 must be accepted.
    pkg = os.path.join(root, 'only_lamedb5')
    os.makedirs(pkg)
    write(os.path.join(pkg, 'lamedb5'), lamedb5())
    db_path, db, rejected = p.choose_control_database(pkg)
    check(os.path.basename(db_path) == 'lamedb5', 'lamedb5 was not selected')
    check(len(db['services']) == 6 and len(db['transponders']) == 1, 'lamedb5 parsing failed')

    # 2. Invalid lamedb must fall back to valid lamedb5.
    pkg2 = os.path.join(root, 'mixed')
    os.makedirs(pkg2)
    write(os.path.join(pkg2, 'lamedb'), 'broken')
    write(os.path.join(pkg2, 'lamedb5'), lamedb5())
    db_path, db, rejected = p.choose_control_database(pkg2)
    check(os.path.basename(db_path) == 'lamedb5', 'valid lamedb5 fallback failed')
    check(rejected, 'invalid lamedb was not reported')

    # 3. Nested archive support.
    nested_root = os.path.join(root, 'nested')
    os.makedirs(nested_root)
    nested_zip = os.path.join(nested_root, 'settings-inner.zip')
    with zipfile.ZipFile(nested_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('deep/path/lamedb5', lamedb5())
        z.writestr('deep/path/userbouquet.test.tv', '#NAME Test\n')
    extracted = p.try_extract_nested_archives(nested_root)
    check(extracted, 'nested archive was not extracted')
    db_path, db, rejected = p.choose_control_database(nested_root)
    check(db_path and os.path.basename(db_path) == 'lamedb5', 'nested lamedb5 not discovered')

    # 4. Archive traversal protection.
    evil = os.path.join(root, 'evil.zip')
    with zipfile.ZipFile(evil, 'w') as z:
        z.writestr('../escape.txt', 'bad')
    blocked = False
    try:
        p.extract_archive(evil, os.path.join(root, 'evil_out'))
    except Exception:
        blocked = True
    check(blocked, 'unsafe archive path was not blocked')
    check(not os.path.exists(os.path.join(root, 'escape.txt')), 'unsafe archive escaped destination')

    # 5. Verified backup and restore (TV + radio + lamedb/lamedb5).
    e2 = os.path.join(root, 'e2')
    backups = os.path.join(root, 'backups')
    os.makedirs(e2)
    original_l4 = lamedb4()
    original_l5 = lamedb5()
    write(os.path.join(e2, 'lamedb'), original_l4)
    write(os.path.join(e2, 'lamedb5'), original_l5)
    write(os.path.join(e2, 'bouquets.tv'), '#NAME TV\n')
    write(os.path.join(e2, 'bouquets.radio'), '#NAME RADIO\n')
    write(os.path.join(e2, 'userbouquet.test.tv'), '#NAME Test\n')
    write(os.path.join(e2, 'userbouquet.radio.radio'), '#NAME Radio\n')
    p.E2_PATH, p.BACKUP_DIR = e2, backups
    backup = p.make_backup()
    check(os.path.isfile(backup), 'backup not created')
    with tarfile.open(backup, 'r:gz') as t:
        names = set(t.getnames())
    check('lamedb' in names and 'lamedb5' in names and 'bouquets.radio' in names, 'backup is incomplete')
    write(os.path.join(e2, 'lamedb'), 'changed')
    write(os.path.join(e2, 'userbouquet.test.tv'), 'changed')
    p.restore_backup(backup)
    check(read(os.path.join(e2, 'lamedb')).decode('utf-8') == original_l4, 'lamedb restore failed')
    check(read(os.path.join(e2, 'userbouquet.test.tv')).decode('utf-8') == '#NAME Test\n', 'bouquet restore failed')

    # 6. Never copy lamedb /4/ blindly into lamedb5 /5/.
    local = p.parse_lamedb(os.path.join(e2, 'lamedb'))
    before_l5 = read(os.path.join(e2, 'lamedb5'))
    p.rebuild_lamedb(local, local, {}, {})
    check(read(os.path.join(e2, 'lamedb5')) == before_l5, 'lamedb5 was overwritten by lamedb4')

    # 7. Transaction rollback when bouquet writing fails after lamedb stage.
    original_lamedb = read(os.path.join(e2, 'lamedb'))
    remote_file = os.path.join(root, 'remote_lamedb')
    write(remote_file, lamedb4(7))
    remote_db = p.parse_lamedb(remote_file)
    plan = {
        'local_db': p.parse_lamedb(os.path.join(e2, 'lamedb')),
        'remote_db': remote_db,
        'service_appends': {}, 'transponder_updates': {}, 'files': {},
        'new_channels': {}, 'epg_type_aliases': [], 'skipped_dvbt_bouquets': [],
        'skipped_dvbt_channels': 0,
    }
    old_write = p.write_bouquet_channel_changes
    p.write_bouquet_channel_changes = lambda _plan: (_ for _ in ()).throw(Exception('simulated write failure'))
    rolled_back = False
    try:
        p.apply_plan(plan, p.MODE_CORRECT)
    except Exception as exc:
        rolled_back = 'automatycznie cofnięta' in str(exc)
    finally:
        p.write_bouquet_channel_changes = old_write
    check(rolled_back, 'apply_plan did not report automatic rollback')
    check(read(os.path.join(e2, 'lamedb')) == original_lamedb, 'transaction rollback did not restore lamedb')

    # 8. Diagnostic file includes package inventory and rejected database info.
    p.ERROR_PATH = os.path.join(root, 'error.txt')
    p.write_package_error('Test', 'Test package', 'https://example.invalid', pkg2, 'test reason', rejected=['lamedb broken'])
    error_text = read(p.ERROR_PATH).decode('utf-8')
    check('lamedb5' in error_text and 'test reason' in error_text, 'diagnostic report incomplete')

    print('ALL TESTS PASSED')
finally:
    shutil.rmtree(root, ignore_errors=True)
