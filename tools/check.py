#!/usr/bin/env python3
"""Host checks and the standalone NRO release gate (13 MB, decimal)."""
import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 13_000_000


def check_nro(path):
    path = Path(path)
    data = path.read_bytes()
    if len(data) > LIMIT:
        raise ValueError(f"NRO is {len(data):,} bytes; limit is {LIMIT:,}")
    if data[16:20] != b'NRO0':
        raise ValueError('Not a Nintendo Switch NRO')
    asset = struct.unpack_from('<I', data, 24)[0]
    if data[asset:asset + 4] != b'ASET' or asset + 56 > len(data):
        raise ValueError('NRO asset header missing')
    icon_offset, icon_size = struct.unpack_from('<QQ', data, asset + 8)
    if data[asset + icon_offset:asset + icon_offset + icon_size] != (ROOT / 'icon.jpg').read_bytes():
        raise ValueError('NRO does not contain the current Granny app icon')
    if any(term in data.lower() for term in (b'apk' + b'64', b'etd' + b'2x', b'earnt' + b'odie')):
        raise ValueError('NRO contains another runtime or port name')
    print(f'NRO release gate PASS: {len(data):,} / {LIMIT:,} bytes')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--nro', type=Path)
    args = parser.parse_args()
    if args.nro:
        check_nro(args.nro)
        return
    for folder in ('source', 'include', 'tools', 'assets', 'romfs', 'licenses'):
        for path in (ROOT / folder).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts: continue
            data = path.read_bytes().lower()
            assert b'apk' + b'64' not in data, path
            assert b'e\0t\0d\0' not in data, path
            assert b'etd' + b'2x' not in data and b'earnt' + b'odie' not in data, path
    for path in (ROOT / 'assets').glob('*.dex'):
        data = path.read_bytes()
        assert data[:4] == b'dex\n'
        assert struct.unpack_from('<I', data, 32)[0] == len(data)
        assert data[12:32] == hashlib.sha1(data[32:]).digest()
        assert struct.unpack_from('<I', data, 8)[0] == zlib.adler32(data[12:]) & 0xffffffff
        count, table = struct.unpack_from('<II', data, 56)
        strings = []
        for index in range(count):
            offset = struct.unpack_from('<I', data, table + 4 * index)[0]
            while data[offset] & 0x80: offset += 1
            offset += 1
            value = data[offset:data.index(b'\0', offset)].replace(b'\xc0\x80', b'\0')
            strings.append(value.decode('utf-8', 'surrogatepass').encode('utf-16-be', 'surrogatepass'))
        assert strings == sorted(set(strings)), path
    make = (ROOT / 'Makefile').read_text()
    assert '../' not in make and 'tools/check.py --nro $(OUTPUT).nro' in make
    header = (ROOT / 'include/runtime_base.h').read_text()
    assert '#define NX_PACKAGE "com.DVloper.Granny3"' in header
    assert '#define NX_GAME_APK NX_ROOT "/granny3.apk"' in header
    source = '\n'.join(path.read_text() for path in (ROOT / 'source').glob('*.c'))
    exports = set(re.findall(r'\{"([^"\n]+)"', source))
    strong = set((ROOT / 'assets/native_imports.txt').read_text().splitlines())
    assert strong <= exports, sorted(strong - exports)
    cache = ROOT / '.cache/tests'
    cache.mkdir(parents=True, exist_ok=True)
    contract = header.split('/* Interface: input */')[1].split('/* Interface: io timing */')[0]
    contract += header.split('/* Interface: display */')[1].split('/* Interface:', 1)[0]
    (cache / 'input_contract.h').write_text(contract)
    entry = (ROOT / 'source/main.c').read_text()
    diagnostics = entry.split('static void main_java_loop_diagnostics(', 1)[1].split('typedef enum main_JavaActivityLoopResult', 1)[0]
    (cache / 'loop_diagnostics_code.inc').write_text('static void main_java_loop_diagnostics(' + diagnostics)
    graphics = (ROOT / 'source/runtime_graphics.c').read_text()
    touch_set = entry.split('enum { GRNYX_JAVA_TOUCH_MAX', 1)[1].split('typedef struct main_JavaInputPerf', 1)[0]
    mapping = graphics.split('bool grnyx_display_map_touch(', 1)[1].split('/* ---- shader compat ---- */', 1)[0]
    collect = entry.split('static void main_java_touch_collect(', 2)[2].split('static bool main_java_renderer_touch_scalar', 1)[0]
    (cache / 'touch_collect_code.inc').write_text('enum { GRNYX_JAVA_TOUCH_MAX' + touch_set +
        'bool grnyx_display_map_touch(' + mapping + 'static void main_java_touch_collect(' + collect)
    cc = shlex.split(os.environ.get('HOST_CC', 'cc'))
    android = (ROOT / 'source/runtime_android.c').read_text()
    hit = android.split('static bool framework_view_touch_hit(', 1)[1].split('\n}', 1)[0]
    (cache / 'hit_test_code.inc').write_text('static bool framework_view_touch_hit(' + hit + '\n}\n')
    java = (ROOT / 'source/runtime_java.c').read_text()
    for name, start, marker in (('super_35c', 'case 0x6e: case 0x6f:', 'GrnyxJniValue rv={0}; GrnyxResult rc='),
                                ('super_range', 'case 0x74: case 0x75:', 'GrnyxResult rc=dex_vm_execute_target')):
        section = java.split(start, 1)[1].split(marker, 1)[0].rsplit('const char *target_class = nm->cls;', 1)[1]
        (cache / (name + '.inc')).write_text('const char *target_class = nm->cls;' + section)
    exe = cache / ('port_contract_test.exe' if os.name == 'nt' else 'port_contract_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I' + str(cache),
                        'tests/port_contract_test.c', '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    exe = cache / ('controller_test.exe' if os.name == 'nt' else 'controller_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-DNX_CONTROLLER_HOST_TEST',
                        '-I' + str(cache), 'source/runtime_input.c', 'tests/controller_test.c',
                        '-lm', '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    java = (ROOT / 'source/runtime_java.c').read_text()
    declarations = java.split('typedef struct dex_vm_DexProfSlot {', 1)[1].split('static pthread_t dex_vm_g_prof_thread;', 1)[0]
    slot = java.split('static dex_vm_DexProfSlot *dex_vm_dex_prof_slot(void) {', 1)[1].split('typedef struct dex_vm_DexProfThreadStat', 1)[0]
    (cache / 'profiler_code.inc').write_text('typedef struct dex_vm_DexProfSlot {' + declarations +
        'static dex_vm_DexProfSlot *dex_vm_dex_prof_slot(void) {' + slot)
    exe = cache / ('profiler_test.exe' if os.name == 'nt' else 'profiler_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I' + str(cache),
                        'tests/profiler_test.c', '-pthread', '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    cursor = graphics.split('static void granny_draw_cursor(', 1)[1].split('uint32_t grnyx_eglSwapBuffers', 1)[0]
    (cache / 'cursor_code.inc').write_text('static void granny_draw_cursor(' + cursor)
    exe = cache / ('cursor_test.exe' if os.name == 'nt' else 'cursor_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I' + str(cache),
                        'tests/cursor_test.c', '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    focus = entry.split('static bool main_java_app_managed_focus(', 1)[1].split('static main_JavaActivityLoopResult main_java_activity_event_loop', 1)[0]
    (cache / 'lifecycle_code.inc').write_text('static bool main_java_app_managed_focus(' + focus)
    exe = cache / ('lifecycle_test.exe' if os.name == 'nt' else 'lifecycle_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I' + str(cache),
                        'tests/lifecycle_test.c', '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    bionic = (ROOT / 'source/runtime_bionic.c').read_text()
    jni = (ROOT / 'source/runtime_jni.c').read_text()
    refs = jni.split('struct jni_GrnyxJniRef {', 1)[1].split('typedef struct jni_GrnyxJniEnvHandle', 1)[0]
    (cache / 'jni_refs_code.inc').write_text('struct jni_GrnyxJniRef {' + refs)
    index = jni.split('typedef struct jni_PtrSetTable', 1)[1].split('static bool jni_ref_set_insert_locked', 1)[0]
    (cache / 'jni_index_code.inc').write_text('typedef struct jni_PtrSetTable' + index)
    android = (ROOT / 'source/runtime_android.c').read_text()
    uri = android.split('static bool framework_uri_encode_allowed', 1)[1].split('static int framework_uri_hex_value', 1)[0]
    (cache / 'uri_encode_code.inc').write_text('static bool framework_uri_encode_allowed' + uri)
    slice_define = re.search(r'^#define SIGNAL_WAIT_SLICE_NS .*$', bionic, re.M).group()
    cond = bionic.split('typedef struct compat_threads_SafeCondWait', 1)[1].split('static void compat_threads_safe_cond_wait_release', 1)[0]
    address = bionic.split('typedef struct compat_threads_SafeAddrWait', 1)[1].split('static void compat_threads_signal_safe_addr_wait', 1)[0]
    (cache / 'signal_latency_code.inc').write_text(slice_define + '\n' + 'typedef struct compat_threads_SafeCondWait' + cond +
        'typedef struct compat_threads_SafeAddrWait' + address)
    for name in ('jni_index', 'jni_refs', 'uri_encode', 'signal_latency', 'loop_diagnostics'):
        exe = cache / (name + '_test' + ('.exe' if os.name == 'nt' else ''))
        subprocess.run(cc + ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-I' + str(cache),
                            'tests/' + name + '_test.c', '-pthread', '-o', str(exe)], cwd=ROOT, check=True)
        subprocess.run([str(exe)], cwd=cache, check=True)
    aux = bionic.split('static unsigned char compat_g_aux_random[16]', 1)[1].split('static int compat_grnyx_android_log_vprint', 1)[0]
    (cache / 'auxval_test.c').write_text('''#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <pthread.h>
static int fills;
static void grnyx_fd_random_fill(void *data, size_t n) { ++fills; memset(data, 0x5a, n); }
static unsigned char compat_g_aux_random[16]''' + aux + '''
int main(void) {
    assert(grnyx_bionic_getauxval(6) == 4096 && fills == 0);
    unsigned long p = grnyx_bionic_getauxval(25);
    for (int i = 0; i < 16; ++i) assert(compat_g_aux_random[i] == 0x5a);
    assert(p == (unsigned long)(uintptr_t)compat_g_aux_random);
    assert(p == grnyx_bionic_getauxval(25) && fills == 1);
    return 0;
}
''')
    exe = cache / ('auxval_test.exe' if os.name == 'nt' else 'auxval_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', str(cache / 'auxval_test.c'),
                        '-pthread', '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
    assets = (ROOT / 'source/runtime_assets.c').read_text()
    unpack = assets.split('static uint8_t *package_unpack_boot_dex(', 1)[1].split('static void package_core_library_init_blob', 1)[0]
    (cache / 'boot_unpack.inc').write_text('static uint8_t *package_unpack_boot_dex(' + unpack)
    for name in ('core_library_dex', 'aosp_libcore_dex'):
        subprocess.run([sys.executable, str(ROOT / 'tools/embed_data.py'), str(ROOT / 'assets' / (name + '.dex')),
                        str(cache / (name + '.inc')), '--symbol', 'grnyx_' + name], check=True)
    exe = cache / ('boot_dex_test.exe' if os.name == 'nt' else 'boot_dex_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I' + str(cache),
                        'tests/boot_dex_test.c', '-lz', '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe), str(ROOT / 'assets/core_library_dex.dex'), str(ROOT / 'assets/aosp_libcore_dex.dex')], check=True)
    contract = header.split('/* Interface: regex compat */')[1].split('/* Interface: sensors */')[0]
    (cache / 'regex_contract.h').write_text(contract)
    exe = cache / ('regex_test.exe' if os.name == 'nt' else 'regex_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-DNX_REGEX_HOST_TEST',
                        '-I' + str(cache), 'source/runtime_bionic.c', 'tests/regex_test.c',
                        '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    logging = (ROOT / 'source/runtime_diagnostics.c').read_text().split('/* ---- result ---- */')[0]
    logging = logging.replace('#include "runtime.h"', '#include "switch.h"')
    (cache / 'logging_code.inc').write_text(logging)
    (cache / 'switch.h').write_bytes((ROOT / 'tests/switch_mock.h').read_bytes())
    exe = cache / ('logging_test.exe' if os.name == 'nt' else 'logging_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-D__SWITCH__',
                        '-I' + str(cache), 'tests/logging_test.c', '-pthread', '-o', str(exe)],
                   cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    contract = header.split('/* Interface: standalone */')[1]
    contract = contract[:contract.index('bool nx_storage_init(void);') + len('bool nx_storage_init(void);')]
    (cache / 'storage_contract.h').write_text('#pragma once\n' + contract)
    exe = cache / ('storage_test.exe' if os.name == 'nt' else 'storage_test')
    subprocess.run(cc + ['-std=gnu11', '-Wall', '-Wextra', '-Werror', '-I' + str(cache),
                        'tests/storage_test.c', '-pthread', '-o', str(exe)], cwd=ROOT, check=True)
    subprocess.run([str(exe)], cwd=cache, check=True)
    # Exercise the size/format guard without requiring a cross compiler.
    subprocess.run([sys.executable, str(ROOT / 'tests/window_manager_regression.py')], check=True)
    sample = cache / 'invalid.nro'
    sample.write_bytes(b'not an nro')
    try:
        try: check_nro(sample)
        except ValueError: pass
        else: raise AssertionError('Invalid NRO accepted')
        header = bytearray(128)
        header[16:20] = b'NRO0'
        struct.pack_into('<I', header, 24, len(header))
        icon = (ROOT / 'icon.jpg').read_bytes()
        sample.write_bytes(header + struct.pack('<4sI6Q', b'ASET', 0, 56, len(icon), 0, 0, 0, 0) + icon)
        check_nro(sample)
        broken = bytearray(sample.read_bytes()); broken[-1] ^= 1
        sample.write_bytes(broken)
        try: check_nro(sample)
        except ValueError: pass
        else: raise AssertionError('Wrong NRO icon accepted')
        with sample.open('wb') as out: out.truncate(LIMIT + 1)
        try: check_nro(sample)
        except ValueError: pass
        else: raise AssertionError('Oversize NRO accepted')
    finally:
        sample.unlink()
    print('Standalone namespace, boot DEX integrity and release limits PASS')


if __name__ == '__main__':
    main()
