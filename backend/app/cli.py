import json
import argparse
import logging

from app.backup import export_backup, import_backup, inspect_backup
from app.scanner import scan


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Nextcloud Photo Map.")
    subparsers = parser.add_subparsers(dest="command")

    scan_parser = subparsers.add_parser("scan", help="Scan Nextcloud photos and update the local database.")
    scan_parser.add_argument("--user-id", type=int, default=None, help="Scan a specific Companion user.")
    scan_parser.add_argument("--limit", type=int, default=None, help="Process only the first N image files.")
    scan_parser.add_argument(
        "--progress-every",
        type=int,
        default=100,
        help="Log scan progress every N processed files. Use 0 to disable progress logs.",
    )

    backup_parser = subparsers.add_parser("backup", help="Export the application database to a JSON backup.")
    backup_parser.add_argument(
        "path",
        nargs="?",
        default="/data/backups/photomap-backup.json",
        help="Backup output path. Default: /data/backups/photomap-backup.json",
    )

    import_parser = subparsers.add_parser("import", help="Replace the current database with a JSON backup.")
    import_parser.add_argument("path", help="Backup JSON path to import.")

    # Backward-compatible scan options for existing commands like: python -m app.cli --limit 5
    parser.add_argument("--limit", type=int, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--progress-every", type=int, default=100, help=argparse.SUPPRESS)

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if args.command == "backup":
        print(json.dumps(export_backup(args.path), indent=2, default=str))
        return

    if args.command == "import":
        info = inspect_backup(args.path)
        print(json.dumps(info, indent=2, default=str))
        confirmation = input("This will delete current database data and replace it with this backup. Type IMPORT to continue: ")
        if confirmation != "IMPORT":
            raise SystemExit("Import cancelled.")
        print(json.dumps(import_backup(args.path, confirmed=True), indent=2, default=str))
        return

    scan_limit = args.limit
    progress_every = args.progress_every
    user_id = getattr(args, "user_id", None)
    print(json.dumps(scan(user_id=user_id, limit=scan_limit, progress_every=progress_every), indent=2, default=str))


if __name__ == "__main__":
    main()
