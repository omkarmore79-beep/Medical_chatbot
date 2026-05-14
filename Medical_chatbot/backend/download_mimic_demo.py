import argparse
import urllib.request
from pathlib import Path


BASE_URL = "https://physionet.org/files/mimic-iv-demo/2.2/hosp"
OUT_DIR = Path("knowledge_base") / "mimic_iv_demo"
FILES = [
    "d_labitems.csv.gz",
    "labevents.csv.gz",
]


def download_file(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as response:
        dest.write_bytes(response.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="Download MIMIC-IV demo lab reference files.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files.")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for filename in FILES:
        dest = OUT_DIR / filename
        if dest.exists() and not args.overwrite:
            print(f"SKIP: {dest} already exists")
            continue
        download_file(f"{BASE_URL}/{filename}", dest)
        print(f"OK: Downloaded {dest}")


if __name__ == "__main__":
    main()
