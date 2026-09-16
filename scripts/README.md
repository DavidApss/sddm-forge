# scripts

- `install.sh` — full (re)install: theme, PopGreeterActions plugin, revert
  script, sudoers rule. Needs the plugin already built (`qmake && make` in
  `plugin/PopGreeterActions`). Run with `sudo`.
- `update-theme.sh` — re-syncs `theme/pop-cosmic-reveal` (Main.qml + assets)
  into the installed theme after an edit. Run with `sudo`.
- `pop-revert-to-cosmic.sh` — installed to `/usr/local/sbin/` by `install.sh`;
  not meant to be run directly. Switches the active display manager back to
  `cosmic-greeter`. Called via `sudo -n` by the PopGreeterActions plugin from
  inside the greeter, under a sudoers.d rule scoped to that exact path for
  the `sddm` user only.
- `switch-to-sddm.sh` — the way back: run from inside a normal COSMIC
  session (ordinary interactive `sudo`) to make `pop-cosmic-reveal` the
  active login screen again on the next logout/reboot.
- `fix-monitor-order.sh` — appends a monitor-position override to the end
  of `/usr/share/sddm/scripts/Xsetup` (the distro's own auto-arrange logic
  there tiles outputs in xrandr's enumeration order, which doesn't
  necessarily match the layout saved in the user's Wayland/COSMIC session).
  Idempotent - safe to re-run. Run with `sudo`.
