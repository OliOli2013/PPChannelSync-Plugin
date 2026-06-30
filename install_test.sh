#!/bin/sh
opkg install --force-reinstall /tmp/enigma2-plugin-extensions-ppchannelsync_1.2.1_all.ipk
init 4
sleep 2
init 3
