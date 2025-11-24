"""Utility to purge old result files."""

import argparse
import sys
from pathlib import Path
from glob import glob
from datetime import datetime, timedelta
import shutil


def get_file_age(file_path: Path) -> int:
    """Get file age in days."""
    mtime = file_path.stat().st_mtime
    file_date = datetime.fromtimestamp(mtime)
    age = datetime.now() - file_date
    return age.days


def purge_files(pattern: str, older_than: int = None, archive: bool = False,
                dry_run: bool = False, force: bool = False) -> tuple[int, int]:
    """
    Purge files matching pattern.

    Args:
        pattern: Glob pattern for files to purge
        older_than: Only purge files older than N days (None = all files)
        archive: Move to archive/ instead of delete
        dry_run: Show what would be done without doing it
        force: Skip confirmation prompt

    Returns:
        (files_processed, files_skipped) tuple
    """
    files = glob(pattern)

    if not files:
        print(f"No files found matching pattern: {pattern}")
        return (0, 0)

    # Filter by age if specified
    if older_than is not None:
        filtered_files = []
        for f_str in files:
            f = Path(f_str)
            age = get_file_age(f)
            if age >= older_than:
                filtered_files.append(f_str)
        files = filtered_files

    if not files:
        print(f"No files found older than {older_than} days")
        return (0, 0)

    # Show files to be processed
    print(f"Found {len(files)} file(s) to {'archive' if archive else 'delete'}:")
    for f in files:
        f_path = Path(f)
        age = get_file_age(f_path)
        size = f_path.stat().st_size
        print(f"  {f_path.name:50s} {size:>10,} bytes, {age} days old")

    if dry_run:
        print("\n[DRY RUN] No files were actually modified")
        return (len(files), 0)

    # Confirm unless forced
    if not force:
        response = input(f"\n{'Archive' if archive else 'Delete'} these {len(files)} file(s)? [y/N]: ")
        if response.lower() not in ['y', 'yes']:
            print("Aborted")
            return (0, len(files))

    # Process files
    processed = 0
    skipped = 0

    if archive:
        # Create archive directory
        archive_dir = Path("outputs/archive")
        archive_dir.mkdir(parents=True, exist_ok=True)

    for f_str in files:
        f = Path(f_str)
        try:
            if archive:
                dest = archive_dir / f.name
                # Handle name collisions
                counter = 1
                while dest.exists():
                    stem = f.stem
                    suffix = f.suffix
                    dest = archive_dir / f"{stem}_{counter}{suffix}"
                    counter += 1

                shutil.move(str(f), str(dest))
                print(f"  Archived: {f.name} → {dest}")
            else:
                f.unlink()
                print(f"  Deleted: {f.name}")

            processed += 1

        except Exception as e:
            print(f"  Error processing {f.name}: {e}", file=sys.stderr)
            skipped += 1

    return (processed, skipped)


def main():
    """Main purge entry point."""
    parser = argparse.ArgumentParser(
        description="Purge old Mastermind LLM benchmark result files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run to see what would be deleted
  python -m src.purge --pattern "outputs/results_*.jsonl" --dry-run

  # Delete files older than 30 days with confirmation
  python -m src.purge --older-than 30d

  # Archive all result files without confirmation
  python -m src.purge --archive --force

  # Delete specific pattern older than 7 days
  python -m src.purge --pattern "outputs/orchestrator_*.jsonl" \\
    --older-than 7d --force
        """
    )

    parser.add_argument('--pattern', type=str, default='outputs/results_*.jsonl',
                        help='Glob pattern for files to purge (default: outputs/results_*.jsonl)')
    parser.add_argument('--older-than', type=str, default=None,
                        help='Only purge files older than N days (e.g., "30d", "7d")')
    parser.add_argument('--archive', action='store_true',
                        help='Move to outputs/archive/ instead of delete')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without doing it')
    parser.add_argument('--force', action='store_true',
                        help='Skip confirmation prompt')

    args = parser.parse_args()

    # Parse older_than
    older_than_days = None
    if args.older_than:
        try:
            # Accept formats like "30d", "7d", or just "30"
            if args.older_than.endswith('d'):
                older_than_days = int(args.older_than[:-1])
            else:
                older_than_days = int(args.older_than)

            if older_than_days < 0:
                parser.error("--older-than must be positive")

        except ValueError:
            parser.error(f"Invalid --older-than format: {args.older_than}")

    print("=" * 70)
    print("MASTERMIND LLM BENCHMARK - PURGE UTILITY")
    print("=" * 70)
    print(f"Pattern: {args.pattern}")
    print(f"Older than: {older_than_days} days" if older_than_days else "Older than: N/A (all files)")
    print(f"Action: {'Archive to outputs/archive/' if args.archive else 'Delete'}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print("=" * 70)
    print()

    # Execute purge
    processed, skipped = purge_files(
        args.pattern,
        older_than=older_than_days,
        archive=args.archive,
        dry_run=args.dry_run,
        force=args.force
    )

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Processed: {processed}")
    print(f"Skipped: {skipped}")
    print("=" * 70)

    sys.exit(0 if skipped == 0 else 1)


if __name__ == '__main__':
    main()
