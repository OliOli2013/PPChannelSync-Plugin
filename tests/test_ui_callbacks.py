# -*- coding: utf-8 -*-
from __future__ import print_function
import os
import sys
import types
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PLUGIN = os.path.join(ROOT, 'usr/lib/enigma2/python/Plugins/Extensions/PPChannelSync/plugin.py')

modules = {}
for name in ['Plugins','Plugins.Plugin','Screens','Screens.Screen','Screens.MessageBox','Components','Components.ActionMap','Components.Label','Components.MenuList']:
    modules[name] = types.ModuleType(name)

class PD(object):
    WHERE_PLUGINMENU = 1
    def __init__(self,*a,**k): pass

class Screen(dict):
    def __init__(self, session=None, *a, **k):
        dict.__init__(self)
        self.session = session
        self.closed_with = None
    def close(self, *args):
        self.closed_with = args
    def setTitle(self, *args):
        pass

class MB(object):
    TYPE_INFO=0; TYPE_ERROR=1; TYPE_YESNO=2

class DummyL(object):
    def setFont(self,*a): pass
    def setItemHeight(self,*a): pass

class Label(object):
    def __init__(self, text=''):
        self.text=text
    def setText(self,text):
        self.text=text

class MenuList(object):
    def __init__(self, values):
        self.list=list(values)
        self.index=0
        self.l=DummyL()
        self.onSelectionChanged=[]
    def setList(self, values):
        self.list=list(values)
    def getCurrentIndex(self):
        return self.index
    def moveToIndex(self,index):
        self.index=index
    def up(self):
        self.index=max(0,self.index-1)
    def down(self):
        self.index=min(max(0,len(self.list)-1),self.index+1)

class ActionMap(object):
    def __init__(self,*a,**k): pass

modules['Plugins.Plugin'].PluginDescriptor=PD
modules['Screens.Screen'].Screen=Screen
modules['Screens.MessageBox'].MessageBox=MB
modules['Components.ActionMap'].ActionMap=ActionMap
modules['Components.Label'].Label=Label
modules['Components.MenuList'].MenuList=MenuList
sys.modules.update(modules)

spec=importlib.util.spec_from_file_location('ppcs201_ui',PLUGIN)
p=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class Session(object):
    def open(self,*a,**k): pass
    def openWithCallback(self,*a,**k): pass

selector=p.SatelliteSelectScreen(Session(),[130,192],[130])
selector.cancel()
assert selector.closed_with == (None,), selector.closed_with
selector=p.SatelliteSelectScreen(Session(),[130,192],[130])
selector.toggle()
assert 130 not in selector.selected
selector.toggle()
assert 130 in selector.selected
selector.save()
assert selector.closed_with == ([130],), selector.closed_with

class FakeMain(object):
    def __init__(self):
        self.positions=[130]
        self.refreshed=False
    def refresh(self): self.refreshed=True

fake=FakeMain()
p.PPChannelSyncScreen.satellites_selected(fake)
assert fake.positions == [130] and not fake.refreshed
p.PPChannelSyncScreen.satellites_selected(fake,[130,192])
assert fake.positions == [130,192] and fake.refreshed

for name in ('key_red','key_green','key_yellow','key_blue'):
    assert 'name="%s"' % name in p.PPChannelSyncScreen.skin
    segment=p.PPChannelSyncScreen.skin.split('name="%s"' % name,1)[1].split('/>',1)[0]
    assert 'zPosition="5"' in segment, (name,segment)

print('UI CALLBACK TESTS PASSED')
