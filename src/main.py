"""CLI entry point for Mastermind LLM Benchmark."""

import argparse
import json
import random
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import asdict

from .game import GameConfig, MastermindGame
from .llm_player import LLMPlayer, LLMConfig
from .clipboard_player import ClipboardPlayer
from .cli_player import CLIPlayer, CLIConfig
from .runner import GameSession

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


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


def detect_parent_cli():
    """
    Detect if running from a CLI tool (claude, codex, or gemini).
    Returns the CLI tool name or None if not detected.
    """
    if not PSUTIL_AVAILABLE:
        return None

    try:
        current = psutil.Process()
        parent = current.parent()

        # Walk up process tree looking for CLI tools
        while parent:
            name = parent.name().lower()

            # Check for CLI tools
            for cli in ['claude', 'codex', 'gemini']:
                if cli in name:
                    return cli

            # Move to next parent
            try:
                parent = parent.parent()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                break
    except Exception:
        pass

    return None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Mastermind LLM Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # CLI auto-detection (from claude/codex/gemini CLI) - FREE
  claude --print "python -m src.main --runs 10"

  # API mode with any model - PAID
  python -m src.main --model deepseek/deepseek-chat --runs 10
  python -m src.main --model gpt-4 --runs 10
  python -m src.main --model claude-3-5-sonnet-20241022 --runs 10

  # Override: Use API even from CLI
  claude --print "python -m src.main --model gpt-4 --runs 10"

  # Clipboard mode for web UI testing (works with any web LLM)
  python -m src.main --mode clipboard --runs 5
  python -m src.main --mode clipboard --model "chatgpt-web" --runs 5

  # Custom game with specific secret
  python -m src.main --model claude-3-5-sonnet-20241022 --colors 8 --pegs 5 --secret "1,2,3,4,5"

Model string examples (API mode):
  DeepSeek: deepseek/deepseek-chat, deepseek/deepseek-coder
  OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
  Anthropic: claude-3-5-sonnet-20241022, claude-3-opus-20240229
  Google: gemini/gemini-pro, gemini/gemini-1.5-pro

CLI detection (auto-mode):
  If no --model specified, detects parent process (claude/codex/gemini)
  and uses local CLI automatically (requires CLI tool installed)
        """
    )

    # Mode
    parser.add_argument('--mode', choices=['auto', 'api', 'cli', 'clipboard'], default='auto',
                        help='Execution mode: auto (detect CLI), api (use model), cli (force CLI), clipboard (manual)')

    # Model (optional - triggers API mode if specified)
    parser.add_argument('--model', type=str,
                        help='LiteLLM model string (API mode) or tracking label (clipboard mode, default: web-ui)')

    # Game configuration
    game_group = parser.add_argument_group('game configuration')
    game_group.add_argument('--colors', type=int, default=6,
                            help='Number of colors (default: 6)')
    game_group.add_argument('--pegs', type=int, default=4,
                            help='Number of pegs (default: 4)')
    game_group.add_argument('--no-duplicates', action='store_true',
                            help='Disallow duplicate colors (default: allow)')
    game_group.add_argument('--max-turns', type=int, default=12,
                            help='Maximum turns (default: 12)')
    game_group.add_argument('--secret', type=str, default=None,
                            help='Predefined secret as comma-separated integers (e.g., "1,2,3,4")')

    # LLM configuration (API mode only)
    llm_group = parser.add_argument_group('llm configuration (api mode only)')
    llm_group.add_argument('--temperature', type=float, default=0.7,
                           help='Temperature (default: 0.7)')
    llm_group.add_argument('--max-tokens', type=int, default=500,
                           help='Max tokens (default: 500)')
    llm_group.add_argument('--parser-fallback', action='store_true',
                           help='Enable parser fallback for malformed responses')
    llm_group.add_argument('--parser-model', type=str, default='gpt-3.5-turbo',
                           help='Model for parsing fallback (default: gpt-3.5-turbo)')
    llm_group.add_argument('--max-retries', type=int, default=1,
                           help='Max retries for invalid guesses per turn (default: 1)')

    # Execution
    exec_group = parser.add_argument_group('execution')
    exec_group.add_argument('--runs', type=int, default=1,
                            help='Number of games to run (default: 1)')
    exec_group.add_argument('--output', type=str, default=None,
                            help='Output JSONL file (default: outputs/results_TIMESTAMP.jsonl)')
    exec_group.add_argument('--seed', type=int, default=None,
                            help='Random seed for reproducibility')
    exec_group.add_argument('--verbose', action='store_true',
                            help='Verbose logging')
    exec_group.add_argument('--max-api-calls', type=int, default=100,
                            help='Maximum API calls per game (safety limit, default: 100)')
    exec_group.add_argument('--timeout', type=float, default=300,
                            help='Maximum seconds per game (safety limit, default: 300)')

    args = parser.parse_args()

    # Determine execution mode
    detected_cli = None
    final_mode = args.mode

    if args.mode == 'auto':
        # Auto-detection logic
        if args.model:
            # Model specified = API mode
            final_mode = 'api'
        else:
            # No model = try to detect CLI
            detected_cli = detect_parent_cli()
            if detected_cli:
                final_mode = 'cli'
            else:
                parser.error("No --model specified and no CLI detected. Either:\n"
                           "  1. Run from a CLI tool (claude/codex/gemini)\n"
                           "  2. Specify --model for API mode\n"
                           "  3. Use --mode clipboard for manual input")
    elif args.mode == 'cli':
        # Force CLI mode
        if not args.model:
            detected_cli = detect_parent_cli()
            if not detected_cli:
                parser.error("--mode cli requires either:\n"
                           "  1. Running from a CLI tool (claude/codex/gemini)\n"
                           "  2. Specifying --model with a CLI tool name (claude|codex|gemini)")
        else:
            detected_cli = args.model if args.model in ['claude', 'codex', 'gemini'] else None
            if not detected_cli:
                parser.error("For CLI mode, --model must be one of: claude, codex, gemini")
        final_mode = 'cli'

    # Validation
    if final_mode == 'api' and not args.model:
        parser.error("--model is required for api mode")

    if final_mode == 'clipboard' and not args.model:
        args.model = "web-ui"  # Default label for web-based interfaces

    if args.colors < 2:
        parser.error("--colors must be at least 2")

    if args.pegs < 1:
        parser.error("--pegs must be at least 1")

    if not args.no_duplicates and args.colors < args.pegs:
        parser.error(f"Need at least {args.pegs} colors when duplicates are not allowed")

    # Set random seed
    if args.seed is not None:
        random.seed(args.seed)

    # Parse secret if provided
    predefined_secret = None
    if args.secret:
        predefined_secret = parse_secret(args.secret, args.pegs, args.colors)
        print(f"Using predefined secret: {predefined_secret}")

    # Setup output file
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path("outputs") / f"results_{timestamp}.jsonl"
    else:
        output_path = Path(args.output)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create game config
    game_config = GameConfig(
        num_colors=args.colors,
        num_pegs=args.pegs,
        allow_duplicates=not args.no_duplicates,
        max_turns=args.max_turns
    )

    # Create player based on final mode
    if final_mode == 'api':
        from dotenv import load_dotenv
        load_dotenv()

        llm_config = LLMConfig(
            model=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            use_parser_fallback=args.parser_fallback,
            parser_model=args.parser_model,
            max_retries=args.max_retries
        )
        player = LLMPlayer(game_config, llm_config)
        player_label = args.model
        cost_info = "(paid)"
    elif final_mode == 'cli':
        cli_config = CLIConfig(
            cli_tool=detected_cli
        )
        player = CLIPlayer(game_config, cli_config)
        player_label = f"{detected_cli}-cli"
        cost_info = "(free with subscription)"
    else:  # clipboard
        player = ClipboardPlayer(game_config, args.model)
        player_label = args.model
        cost_info = "(manual)"

    # Run games
    print(f"Running {args.runs} game(s) with {player_label} {cost_info}")
    print(f"Mode: {final_mode}")
    print(f"Config: {args.colors} colors, {args.pegs} pegs, duplicates={'yes' if game_config.allow_duplicates else 'no'}, max_turns={args.max_turns}")
    print(f"Safety limits: max {args.max_api_calls} API calls, {args.timeout}s timeout per game")
    print(f"Output: {output_path}")
    print()

    results_summary = {"wins": 0, "losses": 0, "errors": 0}

    with open(output_path, 'a') as f:
        for run in range(1, args.runs + 1):
            print(f"Game {run}/{args.runs}")

            # Create session with optional predefined secret and safety limits
            session = GameSession(
                game_config,
                player,
                args.max_retries,
                secret=predefined_secret,
                max_api_calls=args.max_api_calls,
                timeout_seconds=args.timeout
            )
            result = session.run()

            # Update summary
            outcome_key = {"win": "wins", "loss": "losses", "error": "errors"}[result.outcome]
            results_summary[outcome_key] += 1

            # Write result
            f.write(json.dumps(asdict(result)) + '\n')
            f.flush()

            # Print summary
            if result.outcome == "win":
                print(f"  Won in {result.total_turns} turns")
            elif result.outcome == "loss":
                print(f"  Lost after {result.total_turns} turns")
            else:
                print(f"  Error: {result.turns[-1].get('error', 'Unknown error') if result.turns else 'Unknown error'}")

            if args.verbose and result.turns:
                print(f"  Secret: {result.secret}")
                for turn in result.turns:
                    if turn.get('guess'):
                        fb = turn.get('feedback', {})
                        print(f"    Turn {turn['turn_number']}: {turn['guess']} -> {fb.get('black', 0)}B {fb.get('white', 0)}W")

            print()

    # Final summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total games: {args.runs}")
    print(f"Wins: {results_summary['wins']} ({results_summary['wins']/args.runs*100:.1f}%)")
    print(f"Losses: {results_summary['losses']} ({results_summary['losses']/args.runs*100:.1f}%)")
    print(f"Errors: {results_summary['errors']} ({results_summary['errors']/args.runs*100:.1f}%)")
    print(f"\nResults saved to: {output_path}")


if __name__ == '__main__':
    main()
