"""CLI entry point for lovdata-pipeline."""
import argparse
import os
from .pipeline import (
    parse_consolidated_archive,
    parse_lovtidend_archive,
    init_db,
    store_amendment_act,
    run_pipeline,
)


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
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse archives to markdown only, skip git fast-import",
    )
    args = parser.parse_args()

    if args.download:
        from .download import download_archives
        archives = download_archives(args.output)
        args.gjeldende = archives["gjeldende"]
        args.lovtidend = archives.get("lovtidend", [])

    if args.parse_only:
        print("=" * 60)
        print("Parsing consolidated laws")
        print("=" * 60)
        law_files = parse_consolidated_archive(args.gjeldende, args.output)
        print(f"  {len(law_files)} laws parsed to {args.output}/lover/")

        if args.lovtidend:
            print()
            print("=" * 60)
            print("Parsing Lovtidend amendments")
            print("=" * 60)
            conn = init_db(args.db)
            for archive in args.lovtidend:
                print(f"  Processing {archive}...")
                acts = parse_lovtidend_archive(archive, prefix_filter="nl-")
                print(f"    Found {len(acts)} law amendment acts")
                for act in acts:
                    store_amendment_act(conn, act)
            conn.commit()
            conn.close()
    else:
        run_pipeline(
            gjeldende_archive=args.gjeldende,
            lovtidend_archives=args.lovtidend,
            output_dir=args.output,
            db_path=args.db,
        )


if __name__ == "__main__":
    main()
