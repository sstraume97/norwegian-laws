"""CLI entry point for lovdata-publisher."""
import argparse

from .formatter import format_all_laws
from .git_export import build_history
from .quarto import generate_quarto_config


def main():
    parser = argparse.ArgumentParser(
        description="Read a snapshot and produce formatted law outputs"
    )
    parser.add_argument(
        "--snapshot",
        default="snapshot",
        help="Snapshot directory to read (default: snapshot/)",
    )
    parser.add_argument(
        "--output",
        default=".",
        help="Output directory for Markdown files (default: .)",
    )
    parser.add_argument(
        "--format-only",
        action="store_true",
        help="Write Markdown files only, skip git operations",
    )
    parser.add_argument(
        "--build-history",
        action="store_true",
        help="Build the law-history branch with backdated commits",
    )
    parser.add_argument(
        "--quarto",
        action="store_true",
        help="Generate Quarto book chapters and config",
    )
    parser.add_argument(
        "--repo-path",
        default=None,
        help="Git repo path for history operations (default: temp dir)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="Path to amendments.db (default: snapshot/amendments.db)",
    )
    args = parser.parse_args()

    db_path = args.db
    if db_path is None:
        import os
        candidate = os.path.join(args.snapshot, "amendments.db")
        if os.path.exists(candidate):
            db_path = candidate

    # Always format laws when producing any output that depends on lover/*.md.
    # --quarto and default (no flags) both need formatted Markdown to exist.
    if not args.build_history or args.format_only or args.quarto:
        print("=" * 60)
        print("Formatting laws to Markdown")
        print("=" * 60)
        results = format_all_laws(args.snapshot, args.output)
        print(f"  Wrote {len(results)} law files to {args.output}/lover/")

    if args.quarto:
        print()
        print("=" * 60)
        print("Generating Quarto book chapters")
        print("=" * 60)
        generate_quarto_config(args.output, db_path=db_path)

    if args.build_history:
        repo_path = args.repo_path
        if repo_path is None:
            import tempfile
            repo_path = tempfile.mkdtemp(prefix="law-repo-")
        print()
        print("=" * 60)
        print("Building git history")
        print("=" * 60)
        build_history(args.snapshot, repo_path)
        print(f"  Repository at: {repo_path}")


if __name__ == "__main__":
    main()
