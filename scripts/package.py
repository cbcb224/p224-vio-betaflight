"""Collect required artifacts and check Intel HEX addresses and linker symbols."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware"
OUT = ROOT / "dist"

def run(*args):
    return subprocess.check_output([str(a) for a in args], text=True).strip()

def main():
    selected = {}
    for suffix in ("hex", "bin", "elf", "map"):
        matches = list((FW / "obj").glob("**/*P224_VIO_V1*." + suffix))
        if len(matches) != 1:
            raise SystemExit(f"Expected one {suffix}, found {matches}")
        selected[suffix] = matches[0]
    memory = {}
    upper = 0
    eof = False
    for line in selected["hex"].read_text().splitlines():
        b = bytes.fromhex(line.removeprefix(":"))
        if len(b) != b[0] + 5 or sum(b) & 255:
            raise SystemExit("Invalid HEX record")
        address = int.from_bytes(b[1:3], "big")
        kind, data = b[3], b[4:-1]
        if kind == 4:
            upper = int.from_bytes(data, "big") << 16
        elif kind == 2:
            upper = int.from_bytes(data, "big") << 4
        elif kind == 0:
            for i, value in enumerate(data):
                target = upper + address + i
                if not (0x08000000 <= target < 0x08020000 or 0x08040000 <= target < 0x08200000):
                    raise SystemExit(f"HEX writes outside application regions: {target:#x}")
                if target in memory:
                    raise SystemExit("Overlapping HEX records")
                memory[target] = value
        elif kind == 1:
            eof = True
    if not eof or not memory or min(memory) != 0x08000000:
        raise SystemExit("Missing EOF or unexpected vector base")
    vector = bytes(memory[0x08000000 + i] for i in range(8))
    sp, reset = struct.unpack("<II", vector)
    if not (0x20000000 <= sp <= 0x20020000 and reset & 1 and (reset & ~1) in memory):
        raise SystemExit("Unexpected initial stack or reset vector")
    nm = list((FW / "tools").glob("**/bin/arm-none-eabi-nm"))
    readelf = list((FW / "tools").glob("**/bin/arm-none-eabi-readelf"))
    if len(nm) != 1 or len(readelf) != 1:
        raise SystemExit("Cannot locate locked toolchain")
    symbols_text = run(nm[0], selected["elf"])
    symbols = {cols[-1]: int(cols[0], 16) for line in symbols_text.splitlines()
               if len(cols := line.split()) == 3}
    if symbols.get("__config_start") != 0x08020000 or symbols.get("__config_end") != 0x08040000:
        raise SystemExit("Unexpected configuration flash region")
    (OUT / "elf-layout.txt").write_text(run(readelf[0], "-lW", selected["elf"]) + "\n" + symbols_text)
    for path in selected.values():
        shutil.copy2(path, OUT / path.name)
    shutil.copytree(ROOT / "configs", OUT / "configs", dirs_exist_ok=True)
    shutil.copy2(FW / "src/platform/STM32/link/stm32_flash_h743_2m.ld", OUT)
    shutil.copy2(ROOT / "README.md", OUT / "README.md")
    shutil.copy2(FW / "LICENSE", OUT / "BETAFLIGHT-LICENSE.txt")
    inputs = json.loads((OUT / "inputs.json").read_text())
    manifest = {
        "status": "BENCH BRING-UP ONLY; NOT HARDWARE VALIDATED",
        "inputs": inputs,
        "project_commit": os.getenv("GITHUB_SHA", "local"),
        "firmware_commit": run("git", "-C", FW, "rev-parse", "HEAD"),
        "source_diff": run("git", "-C", FW, "diff", "--stat"),
        "build_command": "make CONFIG=P224_VIO_V1 BETAFLIGHT_CONFIG=<project> REV=yes hex binary",
        "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "build_url": f"https://github.com/{os.getenv('GITHUB_REPOSITORY', '')}/actions/runs/{os.getenv('GITHUB_RUN_ID', '')}",
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT"),
        "bin_base": "0x08000000",
        "config_region": "0x08020000..0x0803FFFF",
        "hex_data_min": hex(min(memory)), "hex_data_max": hex(max(memory)),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    checksums = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT).as_posix()}"
                 for p in sorted(OUT.rglob("*")) if p.is_file() and p.name != "SHA256SUMS"]
    (OUT / "SHA256SUMS").write_text("\n".join(checksums) + "\n")
    print("Verified image regions, vector, config symbols and required artifacts")

if __name__ == "__main__":
    main()
