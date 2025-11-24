"""Game session management and result tracking."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
import time

from .game import GameConfig, MastermindGame
from .llm_player import LLMPlayer
from .clipboard_player import ClipboardPlayer
from .cli_player import CLIPlayer


@dataclass
class GameResult:
    """Complete result of a game session."""
    config: dict  # GameConfig as dict
    llm_config: dict  # LLMConfig/mode info as dict
    secret: list[int]
    turns: list[dict]
    outcome: str  # "win" | "loss" | "error"
    total_turns: int
    timestamp: str
    duration_seconds: float
    total_tokens: dict  # {"input": int, "output": int}


class GameSession:
    """Manages a complete game session with retry logic."""

    def __init__(self, game_config: GameConfig, player, max_retries: int = 1, secret: Optional[list[int]] = None, max_api_calls: int = 100, timeout_seconds: float = 300):
        """
        Initialize game session.

        Args:
            game_config: Game configuration
            player: LLMPlayer or ClipboardPlayer instance
            max_retries: Maximum retries for invalid guesses per turn
            secret: Optional predefined secret code
            max_api_calls: Maximum total API calls per game (default: 100)
            timeout_seconds: Maximum time allowed per game in seconds (default: 300)
        """
        self.game_config = game_config
        self.player = player
        self.max_retries = max_retries
        self.predefined_secret = secret
        self.max_api_calls = max_api_calls
        self.timeout_seconds = timeout_seconds

    def run(self) -> GameResult:
        """Run a complete game and return results."""
        start_time = time.time()
        game = MastermindGame(self.game_config, secret=self.predefined_secret)

        turns = []
        total_tokens = {"input": 0, "output": 0}
        outcome = "loss"
        api_call_count = 0

        try:
            while not game.is_game_over():
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > self.timeout_seconds:
                    outcome = "error"
                    turns.append({"error": f"Game timeout after {self.timeout_seconds}s (safety limit)"})
                    break

                # Check API call limit
                if api_call_count >= self.max_api_calls:
                    outcome = "error"
                    turns.append({"error": f"Max API calls reached ({self.max_api_calls}) (safety limit)"})
                    break

                turn_result = self._execute_turn(game, turns)
                turns.append(turn_result)

                # Count API calls (each turn makes at least one)
                api_call_count += 1

                # Track tokens
                if "tokens" in turn_result:
                    total_tokens["input"] += turn_result["tokens"]["input"]
                    total_tokens["output"] += turn_result["tokens"]["output"]

                if game.won:
                    outcome = "win"
                    break

        except KeyboardInterrupt:
            outcome = "error"
        except Exception as e:
            outcome = "error"
            turns.append({"error": f"Fatal error: {str(e)}"})

        duration = time.time() - start_time

        return GameResult(
            config=asdict(self.game_config),
            llm_config=self._get_player_config(),
            secret=game.secret,
            turns=turns,
            outcome=outcome,
            total_turns=game.turns_taken,
            timestamp=datetime.utcnow().isoformat() + "Z",
            duration_seconds=round(duration, 2),
            total_tokens=total_tokens
        )

    def _execute_turn(self, game: MastermindGame, history: list[dict]) -> dict:
        """Execute a single turn with retry logic."""
        retry_count = 0

        while retry_count <= self.max_retries:
            # Get guess from player
            player_result = self.player.get_next_guess(history, retry_count)

            turn_data = {
                "turn_number": len(history) + 1,
                "raw_response": player_result["raw_response"],
                "parsed": player_result["parsed"],
            }

            # Add prompt if clipboard mode
            if "prompt_shown" in player_result:
                turn_data["prompt_shown"] = player_result["prompt_shown"]

            # Add tokens if available
            if "tokens" in player_result:
                turn_data["tokens"] = player_result["tokens"]

            # Check for parsing errors
            if not player_result["parsed"]:
                if retry_count < self.max_retries:
                    retry_count += 1
                    continue
                else:
                    # Max retries exceeded - count as failed turn
                    turn_data["guess"] = None
                    turn_data["feedback"] = None
                    turn_data["error"] = "Failed to get valid guess after retries"
                    game.turns += 1  # Count as a turn
                    return turn_data

            # Process guess
            guess = player_result["guess"]
            turn_data["guess"] = guess

            feedback = game.make_guess(guess)

            if not feedback["valid"]:
                turn_data["error"] = feedback["error"]
                if retry_count < self.max_retries:
                    retry_count += 1
                    continue
                else:
                    # Invalid guess after retries - counts as wasted turn
                    turn_data["feedback"] = {"black": 0, "white": 0}
                    return turn_data

            # Valid guess
            turn_data["feedback"] = {"black": feedback["black"], "white": feedback["white"]}
            turn_data["error"] = None
            return turn_data

        # Should not reach here
        raise RuntimeError("Retry logic error")

    def _get_player_config(self) -> dict:
        """Get player configuration as dict."""
        if isinstance(self.player, LLMPlayer):
            return {
                "mode": "api",
                "model": self.player.llm_config.model,
                "temperature": self.player.llm_config.temperature,
                "max_tokens": self.player.llm_config.max_tokens,
                "use_parser_fallback": self.player.llm_config.use_parser_fallback,
                "parser_model": self.player.llm_config.parser_model if self.player.llm_config.use_parser_fallback else None
            }
        elif isinstance(self.player, CLIPlayer):
            return {
                "mode": "cli",
                "model": f"{self.player.cli_config.cli_tool}-cli",
                "temperature": None,
                "max_tokens": None
            }
        else:  # ClipboardPlayer
            return {
                "mode": "clipboard",
                "model": self.player.model_label,
                "temperature": None,
                "max_tokens": None
            }
