#include "runtime_base.h"
#include <stdarg.h>
#include <stdio.h>

/* Keep the host importer on the same production manifest/bootstrap reader. */
void grnyx_log(const char *level, const char *fmt, ...) { (void)level; (void)fmt; }
bool grnyx_diag_full_trace_enabled(void) { return false; }
void grnyx_log_category(const char *cat, const char *level, const char *fmt, ...) {
    (void)cat; (void)level; (void)fmt;
}
static void string(const char *p) {
    putchar('"');
    for (; *p; ++p) {
        unsigned char c = (unsigned char)*p;
        if (c == '"' || c == '\\') putchar('\\');
        if (c < 32 || c >= 127) printf("\\u%04x", c); else putchar(c);
    }
    putchar('"');
}
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    GrnyxApkInfo info = {0};
    GrnyxResult rc = grnyx_package_probe(argv[1], &info);
    printf("{\"result\":%d,\"package\":", rc); string(info.package_name);
    printf(",\"activity\":"); string(info.activity_name);
    printf(",\"version\":"); string(info.version_name);
    printf(",\"arm64_libraries\":%zu,\"dex_files\":%zu,\"java_bootstrap\":%s,\"native_activity\":%s}\n",
           info.arm64_lib_count, info.java_dex_count,
           info.java_activity_bootstrap ? "true" : "false", info.native_activity ? "true" : "false");
    return 0;
}
