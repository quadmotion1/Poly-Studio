#!/usr/bin/env python3
"""Poly Studio, phase 1: rebrand a SolidCraft source tree (MIT OR Apache-2.0).

    python rebrand.py <path-to-solidcraft-main> <output-dir>

Reads the tree, writes a rebranded copy to <output-dir> and leaves the original untouched.
Safe to re-run on a fresh copy of a newer SolidCraft; every edit asserts that the text it
changes is still there, so a changed upstream stops the script instead of half-applying.

Phase 1 changes what users and the Store see: the name in the interface, the icon, the app
ID, the Windows version resource, the update checker, upstream links, Store packaging.
It does NOT rename crates, folders, env vars (SOLIDCRAFT_*) or the file extensions, so the
code compiles exactly as before. Those are phase 2, done once phase 1 builds on your PC.

What it never touches: LICENSE-MIT, LICENSE-APACHE, NOTICE, ATTRIBUTION.md,
THIRD-PARTY-LICENSES.txt, vendor/ and the "SolidCraft contributors" copyright line. The
licences require those to ship with every copy, and the app shows them in Help > About.
"""
import json
import re
import shutil
import sys
from pathlib import Path

# ---- set these before you publish ------------------------------------------------------------
APP_ID = "io.polystudio.app"                      # reverse-DNS id (Linux/Flatpak, Wayland app_id)
SITE_URL = "https://polystudio.example/"          # your website  (REPLACE: Store listing needs a real one)
DOCS_URL = "https://polystudio.example/docs/"     # your documentation
ISSUES_URL = "https://polystudio.example/support" # where bug reports go
COMPANY = "Poly Studio"                           # shown in the Windows file properties
# -----------------------------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
KEEP = "\u0001SC\u0001"  # placeholder protecting text that must keep the old name
STANDALONE = re.compile(r"(?<![A-Za-z0-9_])SolidCraft(?![A-Za-z0-9_])")


def fail(msg):
    sys.exit(f"rebrand: {msg}")


def read(p):
    return p.read_text(encoding="utf-8")


def write(p, s):
    p.write_text(s, encoding="utf-8", newline="")


def edit(root, rel, old, new, count=1):
    p = root / rel
    s = read(p)
    if s.count(old) != count:
        fail(f"{rel}: expected {count} x {old[:70]!r}, found {s.count(old)} (upstream changed?)")
    write(p, s.replace(old, new))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    if not (src / "Cargo.toml").exists() or not (src / "crates" / "ui-egui").exists():
        fail(f"{src} does not look like a SolidCraft source tree")
    if out.exists():
        fail(f"{out} already exists; pick a new folder")
    print(f"copying {src} -> {out}")
    shutil.copytree(src, out, ignore=shutil.ignore_patterns(".git", "target", "node_modules"))

    # 1. Targeted edits (each asserts its anchor). "SolidCraft" inside a replacement that must
    #    survive the blanket rename below is written as KEEP.
    edit(out, "crates/ui-egui/src/update.rs", '/// The repository releases come from.\npub const REPO',
         "/// Poly Studio has no release feed of its own yet, and the Microsoft Store updates the app,\n"
         "/// so the update checker never runs. It would otherwise offer the upstream project's\n"
         "/// downloads to Poly Studio users.\npub const UPDATES_ENABLED: bool = false;\n\n"
         '/// The repository releases come from.\npub const REPO')
    edit(out, "crates/ui-egui/src/update.rs",
         'if std::env::var("SOLIDCRAFT_UPDATE_CHECK").is_ok_and(|v| v == "0") {',
         'if !UPDATES_ENABLED || std::env::var("SOLIDCRAFT_UPDATE_CHECK").is_ok_and(|v| v == "0") {')
    edit(out, "crates/ui-egui/src/help.rs", 'pub const DOCS_URL: &str = "https://docs.solidcraft.io/";',
         f'pub const DOCS_URL: &str = "{DOCS_URL}";')
    edit(out, "crates/ui-egui/src/issue_report.rs",
         'const ISSUE_URL: &str = "https://github.com/tangency-labs/solidcraft/issues/new";',
         f'const ISSUE_URL: &str = "{ISSUES_URL}";')
    edit(out, "apps/solidcraft/src/startup.rs", "More: https://docs.solidcraft.io/guide/troubleshooting.html",
         f"More: {SITE_URL}")
    edit(out, "apps/solidcraft/src/startup.rs", "Start it once with `solidcraft --safe-mode`.",
         "Start it once with `PolyStudio.exe --safe-mode`.")
    # Windows file properties (Explorer > Details). The exe keeps its cargo name; the Store package
    # ships it as PolyStudio.exe.
    edit(out, "apps/solidcraft/build.rs", r'VALUE \"CompanyName\", \"SolidCraft contributors\"',
         r'VALUE \"CompanyName\", \"' + COMPANY + r'\"')
    # Recognise designs and imports written by SolidCraft too.
    edit(out, "crates/engine/src/cmd/file.rs", 'import.system.trim().starts_with("SolidCraft")',
         f'import.system.trim().starts_with("{KEEP}") || import.system.trim().starts_with("SolidCraft")')

    # App id (reverse-DNS) everywhere it is written out.
    for p in list((out / "apps").rglob("*.rs")) + list((out / "crates").rglob("*.rs")) + list((out / "apps").rglob("*.toml")):
        s = read(p)
        if "io.tangencylabs.solidcraft" in s:
            write(p, s.replace("io.tangencylabs.solidcraft", APP_ID))

    # 2. Blanket rename of the standalone product name in code strings, comments and message
    #    catalogs. Names with letters after them (type names) and lowercase crate/env names stay.
    files = [p for r in ("apps", "crates") for p in (out / r).rglob("*") if p.suffix in (".rs", ".toml") and p.is_file()]
    files += list((out / "assets" / "locales").rglob("*.json"))
    files += [p for r in ("apps", "crates") for p in (out / r).rglob("*.json")]  # UI scenario tests quote the UI text
    changed = 0
    for p in files:
        s = read(p)
        s2 = s.replace("SolidCraft contributors", KEEP + " contributors")
        s2 = STANDALONE.sub("Poly Studio", s2)
        s2 = s2.replace(KEEP, "SolidCraft")
        if s2 != s:
            write(p, s2)
            changed += 1
    print(f"renamed the product name in {changed} files")

    # 3. Icons: the Rust icon module (a resampled logo instead of the drawn SolidCraft mark),
    #    the Windows .ico files, the PNG marks.
    shutil.copy(HERE / "rust" / "app_icon.rs", out / "assets/icons/app/shared/source/app_icon.rs")
    shutil.copy(HERE / "assets" / "poly_mark_512.rgba", out / "assets/icons/app/shared/source/poly_mark_512.rgba")
    for ico in ("solidcraft-executable.ico", "solidcraft.ico"):
        shutil.copy(HERE / "assets" / "polystudio.ico", out / "assets/icons/app/windows/exports" / ico)
    logo_dir = out / "assets/branding/logo"
    from PIL import Image  # only for the 2048 px mark; pip install pillow
    big = Image.open(HERE / "assets" / "polystudio-mark-1024.png").convert("RGBA")
    for size in (512, 1024, 2048):
        big.resize((size, size), Image.LANCZOS).save(logo_dir / f"solidcraft-mark-{size}.png")

    # 4. Store packaging, project notes, no upstream funding/CI/issue templates.
    pkg = out / "packaging/windows"
    shutil.copy(HERE / "msix" / "package-msix.ps1", pkg / "package-msix.ps1")
    shutil.copytree(HERE / "msix", pkg / "msix", dirs_exist_ok=True)
    (pkg / "msix" / "package-msix.ps1").unlink()
    shutil.rmtree(out / ".github", ignore_errors=True)
    shutil.move(out / "README.md", out / "UPSTREAM-README.md")
    write(out / "README.md", "# Poly Studio\n\nParametric 3D CAD. Built on SolidCraft (MIT OR Apache-2.0); see POLYSTUDIO.md.\n")
    write(out / "POLYSTUDIO.md", (HERE / "POLYSTUDIO.md").read_text(encoding="utf-8"))

    # 5. Checks.
    bad = 0
    for p in (out / "assets" / "locales").rglob("*.json"):
        try:
            json.loads(read(p))
        except ValueError as e:
            print(f"INVALID JSON {p}: {e}")
            bad += 1
    left = sum(len(STANDALONE.findall(read(p))) for p in files)
    print(f"standalone 'SolidCraft' left in code/catalogs: {left} (expected: attribution and the legacy-file check only)")
    for ph in (SITE_URL, DOCS_URL, ISSUES_URL):
        if "polystudio.example" in ph:
            print(f"TODO: replace placeholder URL {ph} at the top of rebrand.py and re-run")
            break
    if bad:
        fail("some locale files are not valid JSON")
    print("done")


if __name__ == "__main__":
    main()
