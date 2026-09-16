#!/bin/bash
# Installed as /usr/local/sbin/pop-revert-to-cosmic.sh (root-owned, root-only writable).
# Invoked via `sudo -n` from the sddm-greeter process (PopGreeterActions plugin),
# under a sudoers.d rule scoped to this exact path for the `sddm` user only.
set -e
systemctl stop sddm.service 2>/dev/null || true
ln -sf /usr/lib/systemd/system/cosmic-greeter.service /etc/systemd/system/display-manager.service
echo /usr/bin/cosmic-greeter > /etc/X11/default-display-manager
systemctl start cosmic-greeter.service
