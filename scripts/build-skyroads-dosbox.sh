#!/usr/bin/env bash
# Build a pinned ARM64 DOSBox-X with a read-only SkyRoads observer.
set -euo pipefail
SRE_PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SRE_DOSBOX_SOURCE="$SRE_PROJECT_ROOT/tools/dosbox-x"
SRE_DOSBOX_COMMIT=b60936a716c72e0978e940f813bab2cd40d43868
export PATH="$SRE_PROJECT_ROOT/runtime/build-tools/bin:$PATH"

if [[ ! -d "$SRE_DOSBOX_SOURCE/.git" ]]; then
    git clone --no-checkout https://github.com/joncampbell123/dosbox-x.git "$SRE_DOSBOX_SOURCE"
    git -C "$SRE_DOSBOX_SOURCE" checkout --detach "$SRE_DOSBOX_COMMIT"
fi
if [[ "$(git -C "$SRE_DOSBOX_SOURCE" rev-parse HEAD)" != "$SRE_DOSBOX_COMMIT" ]]; then
    printf '%s\n' 'DOSBox-X checkout differs from the pinned revision; preserving it and stopping.' >&2
    exit 1
fi
for SRE_BUILD_TOOL in autoconf automake pkg-config sdl2-config; do
    command -v "$SRE_BUILD_TOOL" >/dev/null
done

"$SRE_PROJECT_ROOT/runtime/re-venv/bin/python" - "$SRE_PROJECT_ROOT" <<'PY'
import sys
from pathlib import Path
root=Path(sys.argv[1]);cpu=root/'tools/dosbox-x/src/cpu';source=cpu/'core_normal.cpp'
text=source.read_text()
if '#include "skyroads_probe.h"' not in text:
    needle='Bits CPU_Core_Normal_Run(void) {'
    assert text.count(needle)==1
    text=text.replace(needle,'#include "skyroads_probe.h"\n\n'+needle)
if 'SkyRoadsProbe();' not in text:
    needle='while (CPU_Cycles-->0) {'
    assert text.count(needle)==1
    text=text.replace(needle,needle+'\n        SkyRoadsProbe();')
source.write_text(text)
(cpu/'skyroads_probe.h').write_bytes((root/'scripts/dosbox-skyroads-probe.h').read_bytes())
PY

cd "$SRE_DOSBOX_SOURCE"
./autogen.sh
CPPFLAGS=-I/opt/homebrew/include LDFLAGS=-L/opt/homebrew/lib ./configure \
    --prefix="$SRE_PROJECT_ROOT/runtime/dosbox-x" \
    --enable-sdl2 --disable-debug --disable-sdlnet --disable-libslirp \
    --disable-libfluidsynth --disable-mt32 --disable-avcodec --disable-x11 \
    --enable-force-menu-sdldraw
make -j "${SRE_BUILD_JOBS:-6}"

"$SRE_PROJECT_ROOT/runtime/re-venv/bin/python" - "$SRE_PROJECT_ROOT" "$SRE_DOSBOX_COMMIT" <<'PY'
import hashlib,json,sys
from pathlib import Path
root=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
record={'emulator_commit':sys.argv[2],
        'emulator_sha256':sha(root/'tools/dosbox-x/src/dosbox-x'),
        'probe_sha256':sha(root/'scripts/dosbox-skyroads-probe.h'),
        'normal_core_sha256':sha(root/'tools/dosbox-x/src/cpu/core_normal.cpp'),
        'build_script_sha256':sha(root/'scripts/build-skyroads-dosbox.sh')}
(root/'runtime/dosbox-x-build.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
PY
