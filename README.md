# PP Channel Sync

PP Channel Sync is an Enigma2 Python 2/3 plugin for safe channel-list checking and correction.

Version: **1.2.0**

Main principles:

- do not remove existing valid user channels automatically,
- do not overwrite valid user bouquet positions,
- preserve EPG-safe local `lamedb` entries,
- add missing technical entries only when needed,
- add new channels only according to user settings,
- protect DVB-T / DVB-C / IPTV / streams,
- create backups before changes,
- provide reports and GitHub update support.

Author: Paweł Pawełek  
Contact: aio-iptv@wp.pl
