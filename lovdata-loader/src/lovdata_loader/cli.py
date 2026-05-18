"""CLI entry point for lovdata-loader."""
import argparse

from .download import download_archives
from .parser import parse_consolidated_archive, parse_lovtidend_archive
from .store import write_snapshot


def main():
    parser = argparse.ArgumentParser(
        description="Download and parse Lovdata XML archives into a snapshot directory"
    )
    parser.add_argument(
        "--output",
        default="snapshot",
        help="Snapshot output directory (default: snapshot/)",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download archives from Lovdata API before processing",
    )
    parser.add_argument(
        "--gjeldende",
        default="gjeldende-lover.tar.bz2",
        help="Path to consolidated laws archive",
    )
    parser.add_argument(
        "--forskrifter",
        default="gjeldende-sentrale-forskrifter.tar.bz2",
        help="Path to consolidated forskrifter archive",
    )
    parser.add_argument(
        "--lovtidend",
        nargs="*",
        default=[],
        help="Paths to Lovtidend amendment archives",
    )
    parser.add_argument(
        "--skip-amendments",
        action="store_true",
        help="Skip Lovtidend parsing (faster, laws only)",
    )
    parser.add_argument(
        "--skip-forskrifter",
        action="store_true",
        help="Skip forskrifter parsing (laws only)",
    )
    args = parser.parse_args()

    if args.download:
        print("=" * 60)
        print("Downloading archives from Lovdata API")
        print("=" * 60)
        archives = download_archives(args.output)
        args.gjeldende = archives["gjeldende"]
        args.forskrifter = archives.get("forskrifter", args.forskrifter)
        if not args.skip_amendments:
            args.lovtidend = archives.get("lovtidend", [])

    print()
    print("=" * 60)
    print("Parsing consolidated laws")
    print("=" * 60)
    laws = parse_consolidated_archive(args.gjeldende)
    print(f"  Parsed {len(laws)} laws")

    forskrifter_data = []
    if not args.skip_forskrifter and args.forskrifter:
        print()
        print("=" * 60)
        print("Parsing consolidated forskrifter")
        print("=" * 60)
        forskrifter_data = parse_consolidated_archive(args.forskrifter)
        print(f"  Parsed {len(forskrifter_data)} forskrifter")

    amendment_acts = []
    if args.lovtidend and not args.skip_amendments:
        print()
        print("=" * 60)
        print("Parsing Lovtidend amendments")
        print("=" * 60)
        for archive in args.lovtidend:
            print(f"  Processing {archive}...")
            nl_acts = parse_lovtidend_archive(archive, prefix_filter="nl-")
            print(f"    Found {len(nl_acts)} law amendment acts")
            amendment_acts.extend(nl_acts)
            if not args.skip_forskrifter:
                sf_acts = parse_lovtidend_archive(archive, prefix_filter="sf-")
                print(f"    Found {len(sf_acts)} forskrift amendment acts")
                amendment_acts.extend(sf_acts)

    print()
    print("=" * 60)
    print("Writing snapshot")
    print("=" * 60)
    path = write_snapshot(
        output_dir=args.output,
        laws=laws,
        amendment_acts=amendment_acts,
        gjeldende_archive=args.gjeldende,
        lovtidend_archives=args.lovtidend,
        forskrifter=forskrifter_data,
        forskrifter_archive=args.forskrifter,
    )
    print(f"  Snapshot written to {path}/")
    print(f"  {len(laws)} laws, {len(forskrifter_data)} forskrifter, {len(amendment_acts)} amendment acts")


if __name__ == "__main__":
    main()
