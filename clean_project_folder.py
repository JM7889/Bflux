# Clean C:\AI\Project Early Warning for GitHub review.
# Default is dry-run. Use --apply to move old patch/backup files into archive.

from pathlib import Path
import argparse, shutil, datetime

ROOT = Path(__file__).resolve().parent
KEEP_FILES = {
    "bank_flux.py", "README.md", ".gitignore", "fetch_bflux_data.py",
    "clean_project_folder.py", "setup_sample_data.py", "requirements.txt"
}
KEEP_DIRS = {"data", "sample_data", "data_current", "exports", ".git", "archive"}
ARCHIVE = ROOT / "archive" / datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def should_archive(p: Path):
    if p.name in KEEP_FILES:
        return False
    if p.is_dir() and p.name in KEEP_DIRS:
        return False
    if p.name.startswith("__pycache__"):
        return True
    if p.suffix.lower() in [".py", ".md", ".docx", ".txt", ".bat"] and p.name not in KEEP_FILES:
        return True
    if p.name.startswith(("patch_", "repair_", "inspect_", "run_", "README_Bank_Flux")):
        return True
    if "backup" in p.name.lower() or "old" in p.name.lower() or "error_version" in p.name.lower():
        return True
    return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually move files. Without this flag, only prints a plan.")
    args = ap.parse_args()

    targets = [p for p in ROOT.iterdir() if should_archive(p)]
    if not targets:
        print("Nothing to archive.")
        return

    print("Files/folders to archive:")
    for p in targets:
        print("  " + p.name)

    if not args.apply:
        print("\nDry run only. To apply:")
        print("  python clean_project_folder.py --apply")
        return

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    for p in targets:
        dest = ARCHIVE / p.name
        try:
            shutil.move(str(p), str(dest))
            print(f"Moved {p.name} -> {dest}")
        except Exception as exc:
            print(f"Skipped {p.name}: {exc}")
    print("Clean complete.")
    print(f"Archive folder: {ARCHIVE}")

if __name__ == "__main__":
    main()
