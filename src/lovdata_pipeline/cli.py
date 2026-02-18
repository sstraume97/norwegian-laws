"""CLI entry point for lovdata-pipeline."""
import argparse
import os
from .pipeline import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Parse Lovdata XML archives into a git repository"
    )
    parser.add_argument(
        "--gjeldende",
        default="gjeldende-lover.tar.bz2",
        help="Path to consolidated laws archive",
    )
    parser.add_argument(
        "--lovtidend",
        nargs="*",
        default=[],
        help="Paths to Lovtidend amendment archives",
    )
    parser.add_argument(
        "--output",
        default=".",
        help="Output directory (git repo root)",
    )
    parser.add_argument(
        "--db",
        default="amendments.db",
        help="SQLite database path",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download archives from Lovdata API before processing",
    )
    args = parser.parse_args()

    if args.download:
        from .download import download_archives
        archives = download_archives(args.output)
        args.gjeldende = archives["gjeldende"]
        args.lovtidend = archives.get("lovtidend", [])

    run_pipeline(
        gjeldende_archive=args.gjeldende,
        lovtidend_archives=args.lovtidend,
        output_dir=args.output,
        db_path=args.db,
    )


if __name__ == "__main__":
    main()
