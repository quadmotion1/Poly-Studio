# Poly Studio kit (phase 1)

Turns a SolidCraft source tree into a Poly Studio tree you can build and put in the Microsoft Store.
The original SolidCraft folder is never modified.

## 1. Rebrand
1. Open `rebrand.py` and set `APP_ID`, `SITE_URL`, `DOCS_URL`, `ISSUES_URL`, `COMPANY` at the top.
   The Store needs a real website and privacy-policy page, so don't ship the `.example` placeholders.
2. `pip install pillow`, then:
   `python rebrand.py C:\path\to\solidcraft-main C:\path\to\poly-studio`

## 2. Build on Windows
Install Rust 1.95+ (MSVC toolchain), Visual Studio Build Tools (C++), and the Windows 10/11 SDK.
In the new folder: `cargo build --release -p solidcraft`
(no `--locked` the first time; Cargo may rewrite `Cargo.lock`). Run `target\release\solidcraft.exe`.
The exe keeps its cargo name; the Store package ships it as `PolyStudio.exe`.

## 3. Package for the Store
1. Partner Center: reserve the name "Poly Studio"; copy Package/Identity/Name, Publisher and
   Publisher display name from Product management > Product identity.
2. `pwsh packaging\windows\package-msix.ps1 -IdentityName <Name> -Publisher <CN=...> -PublisherDisplayName <name>`
3. Upload `dist\msix\PolyStudio_<version>_x64.msix` in the submission. Microsoft signs it.
4. To try it on your own PC first, sign a copy with a self-signed certificate whose subject equals
   your Publisher string, trust it, then double-click the .msix.

## Not done in phase 1 (and why)
- Not compiled or run: this was prepared without Rust or Windows. Expect to fix small things on the first build.
- `update.rs` tests that assume update checks are on may fail; the checker is deliberately off.
- Crate names, folders, `SOLIDCRAFT_*` environment variables and the `.sc` / `.solidcraft` file
  extensions are unchanged (phase 2). The Store manifest registers `.sc`; change both together.
- The SVG marks in `assets/branding`, the Linux/macOS icons, `docs/` and `skills/` are still SolidCraft's.
- Check the in-app splash/About for any drawn SolidCraft mark before publishing.
- Store submission also needs: privacy policy URL (the app makes network calls), age rating,
  screenshots, description. Read the Store's current policy on apps built from open-source code,
  and search trademarks for "Poly Studio" before you commit to the name.
