"""Validate a checkout and apply reviewed source patches; never compile locally."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / "firmware"
def git(*args):
    return subprocess.check_output(["git", "-C", str(FW), *args], text=True).strip()

def main():
    lock = json.loads((ROOT / "source-lock.json").read_text())
    if git("rev-parse", "HEAD") != lock["commit"]:
        raise SystemExit("Firmware HEAD differs from source-lock.json")
    if git("status", "--porcelain", "--untracked-files=no"):
        raise SystemExit("Firmware has tracked edits: export them to patches/ before CI preparation")
    entry = git("ls-tree", "HEAD", "src/config").split()
    if entry[2] != lock["upstream_config_commit"]:
        raise SystemExit("Unexpected upstream config submodule revision")
    patches = sorted((ROOT / "patches").glob("*.patch"))
    for patch in patches:
        subprocess.run(["git", "-C", str(FW), "apply", "--check", str(patch)], check=True)
        subprocess.run(["git", "-C", str(FW), "apply", str(patch)], check=True)
    files = sorted((ROOT / "configs").rglob("*")) + patches
    hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in files if p.is_file()}
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    (out / "inputs.json").write_text(json.dumps({"lock": lock, "sha256": hashes}, indent=2) + "\n")
    print("Locked source and upstream config verified; source patches applied:", len(patches))

if __name__ == "__main__":
    main()
