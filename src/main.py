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
from .runner import GameSession


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


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Mastermind LLM Benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # API mode with GPT-4
  python src/main.py --model gpt-4 --runs 10

  # Clipboard mode for web UI testing
  python src/main.py --mode clipboard --model "chatgpt-web" --runs 5

  # Custom game with specific secret
  python src/main.py --model claude-3-5-sonnet-20241022 --colors 8 --pegs 5 --secret "1,2,3,4,5"

  # Hard mode: no duplicates, limited turns
  python src/main.py --model gpt-4 --no-duplicates --max-turns 10 --runs 20

Model string examples:
  OpenAI: gpt-4, gpt-4-turbo, gpt-3.5-turbo
  Anthropic: claude-3-5-sonnet-20241022, claude-3-opus-20240229
  Google: gemini/gemini-pro, gemini/gemini-1.5-pro
        """
    )

    # Mode
    parser.add_argument('--mode', choices=['api', 'clipboard'], default='api',
                        help='Execution mode (default: api)')

    # Model (required for API mode, optional label for clipboard)
    parser.add_argument('--model', type=str,
                        help='LiteLLM model string (required for api mode, optional label for clipboard mode)')

    # Game configuration
    game_group = parser.add_argument_group('game configuration')
    game_group.add_argument('--colors', type=int, default=6,
                            help='Number of colors (default: 6)')
    game_group.add_argument('--pegs', type=int, default=4,
                            help='Number of pegs (default: 4)')
    game_group.add_argument('--no-duplicates', action='store_true',
                            help='Disallow duplicate colors (default: allow)')
    game_group.add_argument('--max-turns', type=int, default=None,
                            help='Maximum turns (default: unlimited)')
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

    # Validation
    if args.mode == 'api' and not args.model:
        parser.error("--model is required for api mode")

    if args.mode == 'clipboard' and not args.model:
        args.model = "manual"  # Default label

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

    # Create player
    if args.mode == 'api':
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
    else:
        player = ClipboardPlayer(game_config, args.model)

    # Run games
    print(f"Running {args.runs} game(s) with {args.model}")
    print(f"Config: {args.colors} colors, {args.pegs} pegs, duplicates={'yes' if game_config.allow_duplicates else 'no'}, max_turns={args.max_turns or 'unlimited'}")
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
            results_summary[result.outcome + "s"] += 1

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
