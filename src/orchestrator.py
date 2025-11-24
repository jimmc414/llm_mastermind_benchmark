"""Orchestrator for batch testing multiple models with same secret."""

import argparse
import subprocess
import json
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Optional


def parse_secret(secret_str: str, num_pegs: int, num_colors: int) -> list[int]:
    """Parse secret from comma-separated string."""
    try:
        secret = [int(x.strip()) for x in secret_str.split(',')]
        if len(secret) != num_pegs:
            raise ValueError(f"Secret must have {num_pegs} values")
        if not all(0 <= x < num_colors for x in secret):
            raise ValueError(f"Secret values must be between 0 and {num_colors - 1}")
        return secret
    except Exception as e:
        raise ValueError(f"Invalid secret format: {e}")


def determine_model_mode(model: str) -> tuple[str, str]:
    """
    Determine if model is CLI or API mode.

    Returns:
        (mode, model_identifier) tuple
        mode: 'cli' or 'api'
        model_identifier: CLI tool name or API model string
    """
    cli_tools = ['claude', 'codex', 'gemini']
    if model.lower() in cli_tools:
        return ('cli', model.lower())
    else:
        return ('api', model)


def run_single_model(
    model: str,
    secret: list[int],
    runs: int,
    colors: int,
    pegs: int,
    no_duplicates: bool,
    max_turns: int,
    output_file: Path,
    verbose: bool,
    max_retries: int
) -> dict:
    """
    Run benchmark for a single model.

    Returns:
        Summary dict with results
    """
    mode, model_id = determine_model_mode(model)

    # Build command
    cmd = [
        sys.executable, '-m', 'src.main',
        '--mode', mode,
        '--model', model_id,
        '--secret', ','.join(map(str, secret)),
        '--runs', str(runs),
        '--colors', str(colors),
        '--pegs', str(pegs),
        '--max-turns', str(max_turns),
        '--output', str(output_file)
    ]

    if no_duplicates:
        cmd.append('--no-duplicates')

    if verbose:
        cmd.append('--verbose')

    # Run with retries
    for attempt in range(max_retries + 1):
        try:
            if verbose:
                print(f"Running {model} (attempt {attempt + 1}/{max_retries + 1})...")

            result = subprocess.run(
                cmd,
                capture_output=not verbose,
                text=True,
                timeout=600  # 10 minute timeout per model
            )

            if result.returncode == 0:
                # Success - read and parse results
                if output_file.exists() and output_file.stat().st_size > 0:
                    with open(output_file, 'r') as f:
                        results = [json.loads(line) for line in f]

                    # Calculate summary statistics
                    wins = sum(1 for r in results if r['outcome'] == 'win')
                    losses = sum(1 for r in results if r['outcome'] == 'loss')
                    errors = sum(1 for r in results if r['outcome'] == 'error')
                    avg_turns = sum(r['total_turns'] for r in results if r['outcome'] == 'win') / wins if wins > 0 else 0
                    total_duration = sum(r['duration_seconds'] for r in results)

                    return {
                        'model': model,
                        'mode': mode,
                        'status': 'success',
                        'runs': runs,
                        'wins': wins,
                        'losses': losses,
                        'errors': errors,
                        'win_rate': wins / runs if runs > 0 else 0,
                        'avg_turns_when_won': round(avg_turns, 2),
                        'total_duration': round(total_duration, 2),
                        'output_file': str(output_file)
                    }
                else:
                    raise RuntimeError(f"Output file empty or missing: {output_file}")

            else:
                error_msg = result.stderr if result.stderr else "Unknown error"
                if attempt < max_retries:
                    print(f"  Failed (attempt {attempt + 1}), retrying... Error: {error_msg[:100]}")
                    continue
                else:
                    return {
                        'model': model,
                        'mode': mode,
                        'status': 'failed',
                        'error': error_msg[:500],
                        'output_file': str(output_file)
                    }

        except subprocess.TimeoutExpired:
            if attempt < max_retries:
                print(f"  Timeout (attempt {attempt + 1}), retrying...")
                continue
            else:
                return {
                    'model': model,
                    'mode': mode,
                    'status': 'timeout',
                    'error': 'Execution timeout (10 minutes)',
                    'output_file': str(output_file)
                }

        except Exception as e:
            if attempt < max_retries:
                print(f"  Error (attempt {attempt + 1}), retrying... {str(e)[:100]}")
                continue
            else:
                return {
                    'model': model,
                    'mode': mode,
                    'status': 'error',
                    'error': str(e)[:500],
                    'output_file': str(output_file)
                }

    # Should never reach here
    return {
        'model': model,
        'mode': mode,
        'status': 'failed',
        'error': 'Max retries exceeded',
        'output_file': str(output_file)
    }


def main():
    """Main orchestrator entry point."""
    parser = argparse.ArgumentParser(
        description="Orchestrator for batch testing multiple models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test 3 CLI models with same secret
  python -m src.orchestrator --models "claude,gemini,codex" --secret "1,2,3,4" --runs 5

  # Test CLI and API models in parallel
  python -m src.orchestrator \\
    --models "claude,gpt-4,deepseek/deepseek-chat" \\
    --secret "0,5,3,2" --runs 10 --parallel

  # Custom difficulty
  python -m src.orchestrator \\
    --models "claude,gemini" --secret "1,2,3,4,5" \\
    --colors 8 --pegs 5 --runs 3
        """
    )

    # Required
    parser.add_argument('--models', type=str, required=True,
                        help='Comma-separated list of models (CLI: claude/codex/gemini, API: model strings)')
    parser.add_argument('--secret', type=str, required=True,
                        help='Fixed secret as comma-separated integers (e.g., "1,2,3,4")')

    # Game configuration
    parser.add_argument('--colors', type=int, default=6,
                        help='Number of colors (default: 6)')
    parser.add_argument('--pegs', type=int, default=4,
                        help='Number of pegs (default: 4)')
    parser.add_argument('--no-duplicates', action='store_true',
                        help='Disallow duplicate colors')
    parser.add_argument('--max-turns', type=int, default=12,
                        help='Maximum turns (default: 12)')

    # Execution
    parser.add_argument('--runs', type=int, default=1,
                        help='Number of games per model (default: 1)')
    parser.add_argument('--parallel', action='store_true',
                        help='Run models in parallel (default: sequential)')
    parser.add_argument('--max-retries', type=int, default=0,
                        help='Retry failed runs (default: 0)')
    parser.add_argument('--output-dir', type=str, default='outputs',
                        help='Output directory (default: outputs)')
    parser.add_argument('--batch-name', type=str, default=None,
                        help='Batch name (default: orchestrator_TIMESTAMP)')
    parser.add_argument('--verbose', action='store_true',
                        help='Verbose logging')

    args = parser.parse_args()

    # Parse models
    models = [m.strip() for m in args.models.split(',')]
    if not models:
        parser.error("--models must contain at least one model")

    # Validate secret
    try:
        secret = parse_secret(args.secret, args.pegs, args.colors)
    except ValueError as e:
        parser.error(str(e))

    # Generate batch name
    if args.batch_name:
        batch_name = args.batch_name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_name = f"orchestrator_{timestamp}"

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("MASTERMIND LLM BENCHMARK - ORCHESTRATOR")
    print("=" * 70)
    print(f"Batch name: {batch_name}")
    print(f"Models: {', '.join(models)}")
    print(f"Secret: {secret}")
    print(f"Config: {args.colors} colors, {args.pegs} pegs, "
          f"duplicates={'yes' if not args.no_duplicates else 'no'}, "
          f"max_turns={args.max_turns}")
    print(f"Runs per model: {args.runs}")
    print(f"Execution: {'parallel' if args.parallel else 'sequential'}")
    print(f"Output directory: {output_dir}")
    print("=" * 70)
    print()

    # Prepare tasks
    tasks = []
    for model in models:
        output_file = output_dir / f"{batch_name}_{model.replace('/', '_')}.jsonl"
        tasks.append((
            model,
            secret,
            args.runs,
            args.colors,
            args.pegs,
            args.no_duplicates,
            args.max_turns,
            output_file,
            args.verbose,
            args.max_retries
        ))

    # Run tasks
    results = []

    if args.parallel:
        print("Running models in parallel...")
        with ProcessPoolExecutor(max_workers=len(models)) as executor:
            futures = {executor.submit(run_single_model, *task): task[0] for task in tasks}

            for future in as_completed(futures):
                model = futures[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result['status'] == 'success':
                        print(f"✓ {model}: {result['wins']}/{result['runs']} wins "
                              f"({result['win_rate']*100:.1f}%), "
                              f"avg turns: {result['avg_turns_when_won']}")
                    else:
                        print(f"✗ {model}: {result['status']} - {result.get('error', 'Unknown error')[:80]}")

                except Exception as e:
                    print(f"✗ {model}: Unexpected error - {str(e)[:80]}")
                    results.append({
                        'model': model,
                        'status': 'error',
                        'error': str(e)
                    })

    else:
        print("Running models sequentially...")
        for i, task in enumerate(tasks, 1):
            model = task[0]
            print(f"[{i}/{len(tasks)}] Testing {model}...")

            result = run_single_model(*task)
            results.append(result)

            if result['status'] == 'success':
                print(f"  ✓ {result['wins']}/{result['runs']} wins "
                      f"({result['win_rate']*100:.1f}%), "
                      f"avg turns: {result['avg_turns_when_won']}")
            else:
                print(f"  ✗ {result['status']}: {result.get('error', 'Unknown error')[:80]}")
            print()

    # Save summary
    summary = {
        'batch_name': batch_name,
        'timestamp': datetime.now().isoformat() + 'Z',
        'config': {
            'secret': secret,
            'colors': args.colors,
            'pegs': args.pegs,
            'allow_duplicates': not args.no_duplicates,
            'max_turns': args.max_turns,
            'runs_per_model': args.runs
        },
        'execution': {
            'parallel': args.parallel,
            'max_retries': args.max_retries
        },
        'results': results
    }

    summary_file = output_dir / f"{batch_name}_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    # Print final summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] != 'success']

    if successful:
        print(f"\nSuccessful models ({len(successful)}/{len(results)}):")
        for r in successful:
            print(f"  {r['model']:30s} {r['wins']:3d}/{r['runs']} wins "
                  f"({r['win_rate']*100:5.1f}%) avg turns: {r['avg_turns_when_won']:5.1f}")

    if failed:
        print(f"\nFailed models ({len(failed)}/{len(results)}):")
        for r in failed:
            print(f"  {r['model']:30s} {r['status']}: {r.get('error', 'Unknown')[:50]}")

    print(f"\nSummary saved to: {summary_file}")
    print("=" * 70)

    # Exit code: 0 if all successful, 1 if any failed
    sys.exit(0 if not failed else 1)


if __name__ == '__main__':
    main()
