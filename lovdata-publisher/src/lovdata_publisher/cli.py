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
        "--history-mode",
        choices=["year", "act"],
        default="year",
        help="Commit granularity for law-history: 'year' (~28 commits) or 'act' (~2400 commits, requires LFS)",
    )
    parser.add_argument(
        "--use-lfs",
        action="store_true",
        help="Configure git-lfs for lover/*.md (recommended for --history-mode=act)",
    )
    parser.add_argument(
        "--quarto",
        action="store_true",
        help="Generate Quarto book chapters and config",
    )
    parser.add_argument(
        "--feeds-only",
        action="store_true",
        help="Regenerate Atom feeds only (skip formatting, Quarto, post-render)",
    )
    parser.add_argument(
        "--post-render",
        action="store_true",
        help="After `quarto render`, generate per-law HTML pages and merge full-text search index",
    )
    parser.add_argument(
        "--site-dir",
        default="_site",
        help="Quarto output directory (default: _site)",
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
    # --feeds-only and --post-render skip formatting because lover/*.md already exists.
    if not args.build_history and not args.feeds_only and not args.post_render or args.format_only or args.quarto:
        print("=" * 60)
        print("Formatting laws to Markdown")
        print("=" * 60)
        results = format_all_laws(args.snapshot, args.output)
        print(f"  Wrote {len(results)} law files to {args.output}/lover/")

        if db_path:
            from .historie import generate_historie
            import os
            historie_dir = os.path.join(args.output, "historie")
            count = generate_historie(db_path, historie_dir)
            print(f"  Wrote {count} historie files to {historie_dir}/")

    if args.quarto:
        print()
        print("=" * 60)
        print("Generating Quarto book chapters")
        print("=" * 60)
        generate_quarto_config(args.output, db_path=db_path)

    if args.feeds_only:
        from .feeds import generate_per_law_feeds
        import os
        print()
        print("=" * 60)
        print("Generating per-law, per-topic, and per-ministry Atom feeds")
        print("=" * 60)
        generate_per_law_feeds(
            snapshot_dir=args.snapshot,
            lover_dir=os.path.join(args.output, "lover"),
            forskrifter_dir=os.path.join(args.output, "forskrifter"),
            output_dir=os.path.join(args.site_dir, "feeds"),
        )

    if args.post_render:
        from .per_law_pages import generate_per_law_pages, merge_full_text_into_search
        from .feeds import generate_per_law_feeds
        import os
        print()
        print("=" * 60)
        print("Generating per-law HTML pages and full-text search index")
        print("=" * 60)
        generate_per_law_pages(repo_root=args.output, site_dir=args.site_dir)
        merge_full_text_into_search(repo_root=args.output, site_dir=args.site_dir)

        print()
        print("=" * 60)
        print("Generating per-law, per-topic, and per-ministry Atom feeds")
        print("=" * 60)
        generate_per_law_feeds(
            snapshot_dir=args.snapshot,
            lover_dir=os.path.join(args.output, "lover"),
            forskrifter_dir=os.path.join(args.output, "forskrifter"),
            output_dir=os.path.join(args.site_dir, "feeds"),
        )

    if args.build_history:
        repo_path = args.repo_path
        if repo_path is None:
            import tempfile
            repo_path = tempfile.mkdtemp(prefix="law-repo-")
        print()
        print("=" * 60)
        print(f"Building git history (mode={args.history_mode}, lfs={args.use_lfs})")
        print("=" * 60)
        build_history(args.snapshot, repo_path, mode=args.history_mode, use_lfs=args.use_lfs)
        print(f"  Repository at: {repo_path}")


if __name__ == "__main__":
    main()
