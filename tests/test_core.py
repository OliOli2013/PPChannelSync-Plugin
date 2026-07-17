# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import types
import tempfile
import shutil
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PLUGIN = os.path.join(ROOT, 'usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/plugin.py')


def stubs():
    modules = {}
    for name in ['Plugins','Plugins.Plugin','Screens','Screens.Screen','Screens.MessageBox','Components','Components.ActionMap','Components.Label','Components.MenuList']:
        modules[name] = types.ModuleType(name)
    class PD(object):
        WHERE_PLUGINMENU = 1
        def __init__(self,*a,**k): pass
    class Screen(object):
        def __init__(self,*a,**k): pass
    class MB(object):
        TYPE_INFO=0; TYPE_ERROR=1; TYPE_YESNO=2
    class Dummy(object):
        def __init__(self,*a,**k): pass
    modules['Plugins.Plugin'].PluginDescriptor = PD
    modules['Screens.Screen'].Screen = Screen
    modules['Screens.MessageBox'].MessageBox = MB
    modules['Components.ActionMap'].ActionMap = Dummy
    modules['Components.Label'].Label = Dummy
    modules['Components.MenuList'].MenuList = Dummy
    sys.modules.update(modules)


def write(path, text):
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent): os.makedirs(parent)
    with open(path,'wb') as f:
        f.write(text.encode('utf-8'))


def local_lamedb5():
    return '''eDVB services /5/
# local
t:00820000:1000:0001,s:11000000:27500000:0:3:130:2:0
t:00c00000:2000:0001,s:12000000:27500000:0:3:192:2:0
s:0100:00820000:1000:0001:19:0:0,"Kanał A",p:Test
s:0200:00c00000:2000:0001:1:0:0,"Kanał B",p:Test
'''


def local_lamedb4():
    return '''eDVB services /4/
transponders
00820000:1000:0001
\ts 11000000:27500000:0:3:130:2:0
00c00000:2000:0001
\ts 12000000:27500000:0:3:192:2:0
/
services
0100:00820000:1000:0001:25:0:0
Kanał A
p:Test
0200:00c00000:2000:0001:1:0:0
Kanał B
p:Test
/
end
'''


def remote_lamedb5():
    return '''eDVB services /5/
# remote
t:00820000:1001:0001,s:11100000:27500000:0:3:130:2:0
t:00820000:1002:0001,s:11200000:27500000:0:3:130:2:0
t:00c00000:2001:0001,s:12100000:27500000:0:3:192:2:0
t:00c00000:2002:0001,s:12200000:27500000:0:3:192:2:0
s:0101:00820000:1001:0001:19:0:0,"Kanał A",p:Test
s:0102:00820000:1002:0001:1:0:0,"Nowy 13E",p:Test
s:0201:00c00000:2001:0001:1:0:0,"Kanał B",p:Test
s:0202:00c00000:2002:0001:1:0:0,"Nowy 19E",p:Test
'''


stubs()
spec = importlib.util.spec_from_file_location('ppcs210', PLUGIN)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
assert p.PLUGIN_VERSION == '2.1.0'
root = tempfile.mkdtemp(prefix='ppcs210_test_')
try:
    e2 = os.path.join(root,'e2'); os.makedirs(e2)
    remote_root = os.path.join(root,'remote'); os.makedirs(remote_root)
    write(os.path.join(e2,'lamedb5'), local_lamedb5())
    write(os.path.join(e2,'lamedb'), local_lamedb4())
    write(os.path.join(e2,'bouquets.tv'), '''#NAME User - bouquets (TV)
#SERVICE 1:7:1:0:0:0:0:0:0:0:FROM BOUQUET "userbouquet.test.tv" ORDER BY bouquet
#DESCRIPTION Test
#SERVICE 1:64:0:0:0:0:0:0:0:0:
#DESCRIPTION @ Vhannibal 15.07.2026
''')
    write(os.path.join(e2,'userbouquet.test.tv'), '''#NAME Test
#SERVICE 1:0:19:100:1000:1:820000:0:0:0:
#DESCRIPTION Kanał A
#SERVICE 1:0:1:200:2000:1:C00000:0:0:0:
#DESCRIPTION Kanał B
''')
    remote_path = os.path.join(remote_root,'lamedb5'); write(remote_path, remote_lamedb5())
    remote_bq = os.path.join(remote_root,'userbouquet.test.tv')
    write(remote_bq, '''#NAME Test
#SERVICE 1:0:19:101:1001:1:820000:0:0:0:
#DESCRIPTION Kanał A
#SERVICE 1:0:1:102:1002:1:820000:0:0:0:
#DESCRIPTION Nowy 13E
#SERVICE 1:0:1:201:2001:1:C00000:0:0:0:
#DESCRIPTION Kanał B
#SERVICE 1:0:1:202:2002:1:C00000:0:0:0:
#DESCRIPTION Nowy 19E
''')
    remote_db = p.parse_lamedb(remote_path)
    assert remote_db['valid'] and len(remote_db['services']) == 4
    assert ('19','101','1001','1','820000') in remote_db['services']

    p.E2_PATH=e2
    p.BACKUP_DIR=os.path.join(root,'backups')
    p.REPORT_PATH=os.path.join(root,'report.txt')
    p.DETAIL_REPORT_PATH=os.path.join(root,'details.txt')

    write(os.path.join(e2,'settings'), 'config.Nims.0.configMode=simple\nconfig.Nims.0.diseqcA=130\nconfig.Nims.0.diseqcB=192\nconfig.Nims.1.configMode=advanced\nconfig.Nims.1.advanced.sat.235.lnb=1\n')
    positions=p.detect_positions()
    assert 130 in positions and 192 in positions and 235 in positions, positions
    assert p.PPChannelSyncScreen.satellites_selected.__defaults__ == (None,)

    remote={'label':'fixture','db':remote_db,'positions':set([130,192]),'root':remote_root,'bouquets':[remote_bq]}
    plan=p.build_plan([130,192],remote)
    assert plan['checked']==2, plan
    assert len(plan['ref_changes'])==2, plan['ref_changes']
    assert plan['new_channels_planned']==2, plan['new_channels']
    assert plan['per_position'][130]['added']==1
    assert plan['per_position'][192]['added']==1
    assert plan['matched_bouquets']==1

    backup=p.make_backup()
    added_db=0
    for db in plan['databases']:
        added_db += p.append_records_to_database(db,plan['db_service_additions'],plan['db_transponder_additions'])
    changed,added,retained=p.write_bouquet_changes(plan)
    assert changed==1 and added==2 and retained==0, (changed,added,retained)
    footer=p.update_main_bouquet_footer()
    assert footer >= 1

    text=open(os.path.join(e2,'userbouquet.test.tv'),'rb').read().decode('utf-8')
    assert '#SERVICE 1:0:19:101:1001:1:820000:0:0:0:' in text
    assert '#service 1:0:1:201:2001:1:c00000:0:0:0:' in text.lower()
    assert '#DESCRIPTION ........ nowe kanały - PP Channel Sync ........' in text
    assert '#DESCRIPTION Nowy 13E' in text and '#DESCRIPTION Nowy 19E' in text
    assert '#DESCRIPTION ........ koniec - PP Channel Sync ........' in text
    assert text.count('nowe kanały - PP Channel Sync')==1

    main=open(os.path.join(e2,'bouquets.tv'),'rb').read().decode('utf-8')
    assert '@ Vhannibal' not in main
    assert '#DESCRIPTION @ PP Channel Sync' in main

    check5=p.parse_lamedb(os.path.join(e2,'lamedb5'))
    assert ('19','101','1001','1','820000') in check5['services']
    assert ('1','102','1002','1','820000') in check5['services']
    assert ('1','202','2002','1','c00000') in check5['services']
    raw='\n'.join(check5['services'][('19','101','1001','1','820000')]['raw'])
    assert ':19:' in raw and ':25:' not in raw
    check4=p.parse_lamedb(os.path.join(e2,'lamedb'))
    assert ('19','101','1001','1','820000') in check4['services']

    # Repeated run must refresh one owned block, not duplicate channels/markers.
    plan2=p.build_plan([130,192],remote)
    assert plan2['new_channels_planned']==0, plan2['new_channels']
    assert plan2['retained_owned_channels']==2
    changed2,added2,retained2=p.write_bouquet_changes(plan2)
    assert added2==0 and retained2==2
    text2=open(os.path.join(e2,'userbouquet.test.tv'),'rb').read().decode('utf-8')
    assert text2.count('nowe kanały - PP Channel Sync')==1
    assert text2.count('#DESCRIPTION Nowy 13E')==1
    assert text2.count('#DESCRIPTION Nowy 19E')==1

    # Moving an owned channel above the block removes its duplicate from owned block.
    lines=text2.splitlines()
    base,owned,found=p.extract_owned_new_channel_block(lines)
    assert found==1 and len(owned)==2
    base.extend([owned[0]['service_line'],owned[0]['description_line']])
    base.extend(p.build_owned_new_channel_block(owned))
    write(os.path.join(e2,'userbouquet.test.tv'),'\n'.join(base)+'\n')
    plan3=p.build_plan([130,192],remote)
    owned_out=plan3['files'][os.path.join(e2,'userbouquet.test.tv')]['owned_items']
    assert sum(1 for x in owned_out if x.get('name')=='Nowy 13E')==0

    # Legacy cleanup remains explicit and exact.
    write(os.path.join(e2,'userbouquet.legacy.tv'), '''#NAME Legacy
#SERVICE 1:0:1:1:1:1:820000:0:0:0:
#DESCRIPTION Keep Me
#SERVICE 1:64:0:0:0:0:0:0:0:0:
#DESCRIPTION ........ nowe kanały - PP Channel Sync ........
#SERVICE 1:0:1:999:999:1:820000:0:0:0:
#DESCRIPTION Bad Added
''')
    changed_files, removed=p.remove_legacy_artifacts()
    legacy=open(os.path.join(e2,'userbouquet.legacy.tv'),'rb').read().decode('utf-8')
    assert 'Keep Me' in legacy and 'Bad Added' not in legacy

    p.restore_backup(backup)
    print('ALL TESTS PASSED')
finally:
    shutil.rmtree(root,ignore_errors=True)
