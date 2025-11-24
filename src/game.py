"""Core Mastermind game logic."""

from dataclasses import dataclass
from typing import Optional
import random


@dataclass
class GameConfig:
    """Configuration for a Mastermind game."""
    num_colors: int = 6
    num_pegs: int = 4
    allow_duplicates: bool = True
    max_turns: Optional[int] = None  # None = unlimited


class MastermindGame:
    """Mastermind game implementation with configurable rules."""

    def __init__(self, config: GameConfig, secret: Optional[list[int]] = None):
        """
        Initialize a new Mastermind game.

        Args:
            config: Game configuration
            secret: Optional predefined secret. If None, generates random secret.
        """
        self.config = config
        self.secret = secret if secret is not None else self._generate_secret()
        self.turns = 0
        self.won = False

    def _generate_secret(self) -> list[int]:
        """Generate random secret code according to config rules."""
        if self.config.allow_duplicates:
            return [random.randint(0, self.config.num_colors - 1)
                    for _ in range(self.config.num_pegs)]
        else:
            colors = list(range(self.config.num_colors))
            random.shuffle(colors)
            return colors[:self.config.num_pegs]

    def make_guess(self, guess: list[int]) -> dict:
        """
        Process a guess and return feedback.

        Returns:
            {
                "valid": bool,
                "error": str | None,
                "black": int,  # Only present if valid=True
                "white": int   # Only present if valid=True
            }
        """
        # Validate guess
        error = self._validate_guess(guess)
        if error:
            return {"valid": False, "error": error}

        self.turns += 1

        # Calculate feedback using standard Mastermind algorithm
        black, white = self._calculate_feedback(guess)

        if black == self.config.num_pegs:
            self.won = True

        return {"valid": True, "error": None, "black": black, "white": white}

    def _validate_guess(self, guess: list[int]) -> Optional[str]:
        """Validate guess format and values. Returns error message or None."""
        if not isinstance(guess, list):
            return "Guess must be a list"

        if len(guess) != self.config.num_pegs:
            return f"Guess must have exactly {self.config.num_pegs} positions"

        if not all(isinstance(x, int) for x in guess):
            return "All values must be integers"

        if not all(0 <= x < self.config.num_colors for x in guess):
            return f"All values must be between 0 and {self.config.num_colors - 1}"

        if not self.config.allow_duplicates and len(set(guess)) != len(guess):
            return "Duplicate colors not allowed in this game"

        return None

    def _calculate_feedback(self, guess: list[int]) -> tuple[int, int]:
        """
        Calculate black and white pegs using standard Mastermind rules.

        Algorithm:
        1. Count exact position matches (black pegs)
        2. Remove matched positions from both sequences
        3. For remaining positions, count color matches (white pegs)

        Returns:
            (black_pegs, white_pegs)
        """
        black = 0
        secret_remaining = []
        guess_remaining = []

        # Step 1: Count black pegs and collect remaining positions
        for i in range(len(self.secret)):
            if guess[i] == self.secret[i]:
                black += 1
            else:
                secret_remaining.append(self.secret[i])
                guess_remaining.append(guess[i])

        # Step 2: Count white pegs from remaining positions
        white = 0
        for color in set(guess_remaining):
            white += min(
                guess_remaining.count(color),
                secret_remaining.count(color)
            )

        return black, white

    def is_game_over(self) -> bool:
        """Check if game has ended (won or max turns reached)."""
        if self.won:
            return True
        if self.config.max_turns is not None and self.turns >= self.config.max_turns:
            return True
        return False

    @property
    def turns_taken(self) -> int:
        """Return the number of turns taken."""
        return self.turns
