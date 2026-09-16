#!/bin/bash
# Run this from inside a normal COSMIC session (regular terminal, asks for
# your sudo password like usual) to switch the login screen back to the
# pop-cosmic-reveal SDDM theme. Takes effect on your next logout/reboot.
set -e
ln -sf /usr/lib/systemd/system/sddm.service /etc/systemd/system/display-manager.service
echo /usr/sbin/sddm > /etc/X11/default-display-manager
echo "OK - sddm vai assumir no proximo logout/reboot (nada mudou na sua sessao atual)"
