#!/usr/bin/env bash
# Rebuild the whole graphics archive so LTO can optimize it with the runtime.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK="$ROOT/.cache/mesa-switch"
REV=05fc4b1d449b8fe12cf1a47b46c4a1c1f4e4e3a6
SOURCE_HASH=935a9aa82e4f0ac8a6352700849b48398f70954a97e908673d79c46fc9377f84
export DEVKITPRO="${DEVKITPRO:-/opt/devkitpro}"
export DEVKITA64="${DEVKITA64:-$DEVKITPRO/devkitA64}"
export PATH="$DEVKITA64/bin:$DEVKITPRO/tools/bin:$DEVKITPRO/portlibs/switch/bin:$PATH"
mkdir -p "$WORK/lib"
KEY="$({ sha256sum "${BASH_SOURCE[0]}" "$ROOT/tools/mesa/switch-egl-surfaces.patch" \
    "$DEVKITPRO/libnx/lib/libnx.a" "$DEVKITPRO/portlibs/switch/lib/libdrm_nouveau.a";
    aarch64-none-elf-gcc --version; } | sha256sum | cut -d' ' -f1)"
if [[ -f "$WORK/lib/libEGL.a" && -f "$WORK/lib/libGLESv2.a" && -f "$WORK/lib/libglapi.a" &&
      -f "$WORK/version" && "$(cat "$WORK/version")" == "$KEY" ]]; then exit 0; fi
for tool in ninja bison flex m4; do
    command -v "$tool" >/dev/null || { echo "[Granny] Missing Mesa build tool: $tool (see README.md)." >&2; exit 1; }
done
python3 -c 'import mesonbuild, mako, ply' || {
    echo '[Granny] Install the Mesa Python build tools listed in README.md.' >&2; exit 1;
}
TARBALL="$WORK/source.tar.gz"
if [[ ! -f "$TARBALL" ]]; then
    curl -fsSL "https://codeload.github.com/devkitPro/mesa/tar.gz/$REV" -o "$TARBALL"
fi
printf '%s  %s\n' "$SOURCE_HASH" "$TARBALL" | sha256sum -c -
# Generated-header builds are much faster on Linux than on a /mnt/c mount.
BUILD_TMP=$(mktemp -d "${TMPDIR:-/tmp}/granny-mesa.XXXXXX")
trap 'rm -rf "$BUILD_TMP"' EXIT
tar -xf "$TARBALL" -C "$BUILD_TMP"
SRC="$BUILD_TMP/mesa-$REV"
patch -d "$SRC" -p1 < "$ROOT/tools/mesa/switch-egl-surfaces.patch"
python3 - "$SRC" "$DEVKITPRO" "$BUILD_TMP" <<'PY'
from pathlib import Path
import re, sys
root, sdk, work = map(Path, sys.argv[1:])
p = root / 'meson.build'
p.write_text(p.read_text().replace('from distutils.version import StrictVersion',
    'def StrictVersion(v): return tuple(map(int, v.split(".")))'))
for name in ('gl_XML.py', 'glX_XML.py'):
    p = root / 'src/mapi/glapi/gen' / name
    p.write_text(re.sub(r'(\w+(?:\.\w+)*)\.getchildren\(\)', r'list(\1)', p.read_text()))
args = ['-Oz', '-march=armv8-a+crc+crypto', '-mtune=cortex-a57', '-mtp=soft', '-fPIC',
        '-ffunction-sections', '-fdata-sections', '-D__SWITCH__', '-DHAVE_TIMESPEC_GET',
        f'-ffile-prefix-map={work}=.', f'-fmacro-prefix-map={work}=.',
        f'-I{sdk}/libnx/include', f'-I{sdk}/portlibs/switch/include']
link = [f'-specs={sdk}/libnx/switch.specs', f'-L{sdk}/libnx/lib', f'-L{sdk}/portlibs/switch/lib', '-lnx']
tools = {'c': sdk/'devkitA64/bin/aarch64-none-elf-gcc', 'cpp': sdk/'devkitA64/bin/aarch64-none-elf-g++',
         'ar': sdk/'devkitA64/bin/aarch64-none-elf-gcc-ar', 'strip': sdk/'devkitA64/bin/aarch64-none-elf-strip',
         'pkgconfig': sdk/'portlibs/switch/bin/aarch64-none-elf-pkg-config'}
(work/'cross.ini').write_text('[binaries]\n' + '\n'.join(f'{k} = {str(v)!r}' for k,v in tools.items()) + f'''
[host_machine]
system = 'horizon'
cpu_family = 'aarch64'
cpu = 'cortex-a57'
endian = 'little'
[properties]
needs_exe_wrapper = true
[built-in options]
c_args = {args!r}
cpp_args = {args!r}
c_link_args = {link!r}
cpp_link_args = {link!r}
''')
PY
export PKG_CONFIG_LIBDIR="$DEVKITPRO/portlibs/switch/lib/pkgconfig"
echo '[Granny] Configuring size-optimized Mesa...'
python3 -u -m mesonbuild.mesonmain setup "$BUILD_TMP/build" "$SRC" --cross-file "$BUILD_TMP/cross.ini" \
    --prefix "$BUILD_TMP/install" -Ddefault_library=static -Dbuildtype=minsize -Db_lto=true -Db_ndebug=true \
    -Dplatforms=switch -Ddri-drivers= -Dgallium-drivers=nouveau -Dvulkan-drivers= \
    -Dopengl=true -Dgles1=true -Dgles2=true -Dglx=disabled -Degl=true -Dgbm=false \
    -Dllvm=false -Dshared-glapi=true -Dgallium-vdpau=false -Dgallium-xvmc=false -Dgallium-va=false -Dgallium-omx=disabled \
    2>&1 | tee "$WORK/configure.log"
echo '[Granny] Compiling Mesa (first build only)...'
ninja -C "$BUILD_TMP/build" -j4 2>&1 | tee "$WORK/build.log"
ninja -C "$BUILD_TMP/build" install >> "$WORK/build.log" 2>&1
for archive in libEGL.a libGLESv2.a libglapi.a; do
    cp "$BUILD_TMP/install/lib/$archive" "$WORK/lib/$archive"
done
printf '%s\n' "$KEY" > "$WORK/version"
echo '[Granny] Size-optimized Mesa ready.'
