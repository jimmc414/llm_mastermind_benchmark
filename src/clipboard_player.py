"""Manual input mode using clipboard for web UI interaction."""

from typing import Optional
import pyperclip
import json
import re

from .game import GameConfig


class ClipboardPlayer:
    """Player that uses manual input with clipboard assistance for web UIs."""

    def __init__(self, game_config: GameConfig, model_label: str = "manual"):
        """
        Initialize clipboard player.

        Args:
            game_config: Game configuration
            model_label: Label for the model being tested manually
        """
        self.game_config = game_config
        self.model_label = model_label
        self.system_prompt = self._build_system_prompt()

    def get_next_guess(self, game_history: list[dict], retry_count: int = 0) -> dict:
        """Get guess via manual input with clipboard assistance."""

        # Build prompt
        prompt = self._build_prompt(game_history, retry_count)

        # Copy to clipboard
        pyperclip.copy(prompt)

        # Display to user
        print("\n" + "=" * 70)
        print("PROMPT COPIED TO CLIPBOARD")
        print("=" * 70)
        print(prompt)
        print("=" * 70)
        print("\nPaste this into your LLM web interface and copy the response.")
        print("\nOptions:")
        print("  - Press Enter to paste from clipboard")
        print("  - Type/paste the response manually")
        print("  - Type 'quit' to exit")
        print()

        user_input = input("Enter response: ").strip()

        if user_input.lower() == 'quit':
            raise KeyboardInterrupt("User quit")

        # If user just pressed enter, try to paste from clipboard
        if not user_input:
            try:
                user_input = pyperclip.paste()
                print(f"\nPasted from clipboard:\n{user_input[:200]}...\n")
            except Exception:
                print("Could not paste from clipboard. Please type the response.")
                user_input = input("Enter response: ").strip()

        # Parse response
        guess = self._parse_response(user_input)

        return {
            "guess": guess,
            "raw_response": user_input,
            "parsed": guess is not None,
            "error": None if guess is not None else "Failed to parse response",
            "tokens": {"input": 0, "output": 0},
            "prompt_shown": prompt
        }

    def _build_system_prompt(self) -> str:
        """Build system prompt based on game configuration."""
        duplicates_text = (
            "Duplicate colors are allowed."
            if self.game_config.allow_duplicates
            else "All colors must be unique."
        )

        turns_text = (
            "You have unlimited guesses."
            if self.game_config.max_turns is None
            else f"You have a maximum of {self.game_config.max_turns} guesses."
        )

        return f"""You are playing Mastermind.

RULES:
- The secret code has {self.game_config.num_pegs} positions
- Each position contains a color numbered from 0 to {self.game_config.num_colors - 1}
- {duplicates_text}
- {turns_text}

FEEDBACK:
- Black pegs: correct color in correct position
- White pegs: correct color in wrong position
- You are NOT told which positions are correct

RESPONSE FORMAT:
Respond with ONLY a JSON object containing your guess.
{{"guess": [0, 1, 2, 3]}}

Do not include any other text or explanation outside the JSON object."""

    def _build_prompt(self, game_history: list[dict], retry_count: int) -> str:
        """Build complete prompt text for clipboard."""
        prompt = self.system_prompt + "\n\n"

        if not game_history:
            prompt += "Make your first guess."
        else:
            prompt += "GAME HISTORY:\n\n"
            for i, turn in enumerate(game_history, 1):
                prompt += f"Turn {i}:\n"
                prompt += f"Guess: {turn['guess']}\n"
                if turn.get('feedback'):
                    fb = turn['feedback']
                    prompt += f"Feedback: {fb['black']} black, {fb['white']} white\n"
                elif turn.get('error'):
                    prompt += f"Error: {turn['error']}\n"
                prompt += "\n"

            if retry_count > 0:
                prompt += "Your last guess was invalid. Provide a valid guess in JSON format.\n"
            else:
                prompt += "Provide your next guess in JSON format.\n"

        return prompt

    def _parse_response(self, response: str) -> Optional[list[int]]:
        """Extract guess from JSON response."""
        try:
            # Try direct JSON parse
            data = json.loads(response.strip())
            if "guess" in data and isinstance(data["guess"], list):
                return data["guess"]
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(1))
                    if "guess" in data and isinstance(data["guess"], list):
                        return data["guess"]
                except json.JSONDecodeError:
                    pass

        return None
