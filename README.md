# sddm-forge

A GTK4/libadwaita app to configure **SDDM** and its login theme ("Maia Theme")
without hand-editing QML.

## App layout

Sidebar (sections) · settings panel · **live preview**. The preview stays in
view — every change shows up in it right away — and collapses via the header
button or on its own in narrow windows. It follows the system theme (light/dark
and accent color). The **Full screen** button opens the real greeter (with
video) on top.

## What you can change

- **Appearance** — background (video / image / color), blur, dimming, color
  palette, font and sizes, and **widget style** (presets for the password field,
  the LOGIN button, and the session/power buttons).
- **Layout** — a tree editor: create **panels** (containers) and choose what
  goes in each one. Per panel: position, direction (column/row), width (auto /
  % of the screen / full screen), alignment, spacing, padding, **blur of the
  background behind the panel**, dimming, corner radius. Add / remove / reorder
  panels, sub-panels, and elements. Reorder by **drag** (or ↑↓). Each element's
  visibility = whether it sits in a panel — e.g. a clock with no weekday is a
  panel with only `clock`. Pieces: clock, date, usernameRow, userHandle,
  avatar, password, passwordToggle (show password), loginButton, sessionButton,
  sessionName, rebootButton, powerButton, suspendButton, errorMessage, text
  (free), separator, spacer. Each text piece takes its own **color / size /
  bold**.
- **Clock** — time and date format, locale.
- **System** — the SDDM drop-in: automatic login (user / session / relogin),
  the greeter session (Numlock, cursor theme, font, HiDPI) and who shows in the
  user list (UID range, `HideUsers`, `HideShells`).
- **Themes** — switch `[Theme] Current`, (re)install the bundled theme, enable
  the service at boot, and **backups** (an automatic snapshot before every
  "Apply"; restore any of them).

## How it works

- The GUI runs as a normal user and edits a **working copy** of the theme in
  `~/.local/share/sddm-forge/work/maia-theme/` (seeded from the bundled theme).
- The **preview pane** runs an offscreen QML renderer (PySide6) in a separate
  process that watches the working copy's `theme.conf` and rewrites a PNG on
  every change. The background video does not run offscreen: in "video" mode the
  preview shows the **first frame** of the file (extracted with ffmpeg). Users
  are fictitious. For a faithful render, the **Full screen** button opens
  `sddm-greeter-qt6 --test-mode`.
- **Apply** calls **one** `pkexec` that, as root: makes a backup, copies the
  theme to `/usr/share/sddm/themes/maia-theme/` and writes
  `/etc/sddm.conf.d/10-maia.conf` (its own drop-in — it never touches the
  distro defaults).
- It never restarts `sddm.service` (that would kill your session). To see the
  result: log out, or run `systemctl restart sddm` from a TTY.

## Dependencies

```
sudo dnf install gtk4 libadwaita python3-gobject python3-pyside6 sddm polkit ffmpeg
```

`python3-pyside6` and `ffmpeg` are only for the **embedded preview**; without
them the app still works and the preview falls back to the "Full screen" button.

## Run

```
./bin/sddm-forge            # straight from the repo
```

## Install (per user, no root)

```
./install.sh               # ~/.local/bin/sddm-forge + a menu launcher
```

## Assets

The background videos in `theme/maia-theme/assets/` are large (~70 MB). If you
plan to version them, consider `git lfs track '*.mp4'` before the first commit,
or ignore them and keep them locally.
