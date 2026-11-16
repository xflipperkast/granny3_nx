


<div align="center">

<img src="icon.jpg" alt="granny3_nx" width="160">

# granny_nx

**Granny 3 on Nintendo Switch**

An unofficial Nintendo Switch port of the Android version of  
**Granny 3 — 1.3**

[![Switch](https://img.shields.io/badge/Nintendo_Switch-Homebrew-E60012?style=for-the-badge&logo=nintendoswitch&logoColor=white)](#)
[![Ko-fi](https://img.shields.io/badge/Support_on_Ko--fi-FF5E5B?style=for-the-badge&logo=ko-fi&logoColor=white)](https://ko-fi.com/flippyy)

</div>

---

## About

`granny3_nx` is an experimental standalone port of Granny to Nintendo Switch.

The project includes its own Switch compatibility runtime and build setup. It launches Granny directly, with no separate launcher or runtime installation.

> You must provide your own legally obtained Granny game files. Game assets are not part of the port's source distribution.

---

## Controls

Granny NX supports touchscreen and Nintendo Switch controller input. Gameplay controls are enabled by default. Press Minus to switch to cursor mode for menus.

### General

| Input | Action |
|---|---|
| Minus (-) | Toggle cursor mode |
| Touchscreen | Direct touch input in handheld mode |

### During Gameplay

| Input | Action |
|---|---|
| Left Stick | Walk |
| Right Stick | Look around |
| A / ZR | Interact |
| B / ZL | Crouch |
| X | Drop the held item |
| Y | Pause |

### Menus / Cursor Mode

- Press Minus to show the cursor.
- Either stick moves the cursor.
- A or ZR clicks.
- Press Minus again to return to gameplay controls.
- Touchscreen input takes priority over controller touches.

---

## Build

### Requirements

- [devkitPro](https://devkitpro.org/) with devkitA64 and libnx.
- Switch portlibs: Mesa, libdrm_nouveau, Vorbis/Ogg, FreeType, curl, Mbed TLS and zlib.
- GNU Make, Python 3 and a host C compiler for checks.
- Meson, Ninja, Bison, Flex, m4 and the Python Mako/PLY modules for the first graphics build.
- On Windows, a working WSL distribution with the build tools installed.
- Your own Granny 3 Android 1.3 ARM64 package.

### Compile

Open a terminal in `granny3_nx`. The build script uses `/opt/devkitpro` by default; set `DEVKITPRO` and `DEVKITA64` if your SDK is elsewhere.

Build:
make the build files example to run:

```sh
bash build.sh
```

Rebuild from scratch:

```sh
bash build.sh clean
```

Run the host checks:

```sh
make check
```

The finished `granny3_nx.nro` is copied into the project folder only after passing the release checks, Build dependencies are cached in `.cache/`.

---

## Running

Place these two files on your SD card:

```text
sd:/switch/granny3_nx/granny3_nx.nro
sd:/switch/granny3_nx/granny3.apk
```

Hold **R** while launching an installed game to open hbmenu with full application memory, then launch Granny. Use title takeover instead of applet mode.

The port creates `cache/` and `saves/` inside its own folder. Keep `saves/` when updating.


## Support

When reporting a problem, include the port version, what happened and how to reproduce it.

Logging is **off by default**. To collect a log:

1. Create an empty `logging.flag` beside `granny3_nx.nro`.
2. Launch Granny and reproduce the problem.
3. Collect `granny3_nx.log`, plus `granny3_nx.log.prev` if you relaunched the game.

Remove `logging.flag` and relaunch to turn logging off. Use `full-trace.flag` alongside it only when detailed tracing is needed; ordinary logging is preferred for gameplay reports.

---

## Disclaimer

This is an unofficial fan project and is not affiliated with or endorsed by DVloper.

Granny and its trademarks, artwork, audio and game assets belong to their respective owners. See [LICENSES.md](LICENSES.md) for the port's dependency notices.

## Contribution

Bug reports, performance improvements and fixes are welcome. Include clear reproduction steps in issues and describe the changes and validation in pull requests.
