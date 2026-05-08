import json
import argparse

from app.scanner import scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan Nextcloud photos and update the local database.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N image files.")
    args = parser.parse_args()
    print(json.dumps(scan(limit=args.limit), indent=2, default=str))


if __name__ == "__main__":
    main()
