"""LLM API interface using LiteLLM."""

from dataclasses import dataclass
from typing import Optional
import litellm
import json
import time
import re

from .game import GameConfig


@dataclass
class LLMConfig:
    """Configuration for LLM API calls."""
    model: str
    temperature: float = 0.7
    max_tokens: int = 500
    use_parser_fallback: bool = False
    parser_model: str = "gpt-3.5-turbo"
    max_retries: int = 1  # Retries for invalid guesses


class LLMPlayer:
    """Player that uses an LLM API to generate guesses."""

    def __init__(self, game_config: GameConfig, llm_config: LLMConfig):
        """
        Initialize LLM player.

        Args:
            game_config: Game configuration
            llm_config: LLM API configuration
        """
        self.game_config = game_config
        self.llm_config = llm_config
        self.system_prompt = self._build_system_prompt()

    def get_next_guess(self, game_history: list[dict], retry_count: int = 0) -> dict:
        """
        Get next guess from LLM.

        Returns:
            {
                "guess": list[int] | None,
                "raw_response": str,
                "parsed": bool,
                "error": str | None,
                "tokens": dict  # {"input": int, "output": int}
            }
        """
        try:
            # Build messages
            messages = self._build_messages(game_history, retry_count)

            # Make API call with retry logic for network errors
            response = self._api_call_with_retry(messages)

            raw_response = response.choices[0].message.content
            tokens = {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens
            }

            # Parse response
            guess = self._parse_response(raw_response)

            # If parsing failed and fallback enabled, try parser model
            if guess is None and self.llm_config.use_parser_fallback:
                guess = self._fallback_parse(raw_response)

            return {
                "guess": guess,
                "raw_response": raw_response,
                "parsed": guess is not None,
                "error": None if guess is not None else "Failed to parse response",
                "tokens": tokens
            }

        except Exception as e:
            return {
                "guess": None,
                "raw_response": "",
                "parsed": False,
                "error": str(e),
                "tokens": {"input": 0, "output": 0}
            }

    def _api_call_with_retry(self, messages: list[dict], max_attempts: int = 3):
        """Make API call with exponential backoff for network errors."""
        for attempt in range(max_attempts):
            try:
                return litellm.completion(
                    model=self.llm_config.model,
                    messages=messages,
                    temperature=self.llm_config.temperature,
                    max_tokens=self.llm_config.max_tokens
                )
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait_time)

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

    def _build_messages(self, game_history: list[dict], retry_count: int) -> list[dict]:
        """Build message array for API call."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Build history
        if not game_history:
            user_content = "Make your first guess."
        else:
            history_text = "Previous guesses:\n\n"
            for i, turn in enumerate(game_history, 1):
                history_text += f"Turn {i}:\n"
                history_text += f"Guess: {turn['guess']}\n"
                if turn.get('feedback'):
                    fb = turn['feedback']
                    history_text += f"Feedback: {fb['black']} black, {fb['white']} white\n"
                elif turn.get('error'):
                    history_text += f"Error: {turn['error']}\n"
                history_text += "\n"

            if retry_count > 0:
                user_content = history_text + "Your last guess was invalid. Please provide a valid guess in the correct JSON format."
            else:
                user_content = history_text + "Provide your next guess."

        messages.append({"role": "user", "content": user_content})
        return messages

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

    def _fallback_parse(self, response: str) -> Optional[list[int]]:
        """Use parser model to extract guess from malformed response."""
        try:
            parser_prompt = f"""Extract the Mastermind guess from this response.
The guess should be a list of {self.game_config.num_pegs} integers from 0 to {self.game_config.num_colors - 1}.

Response:
{response}

Output ONLY valid JSON in this exact format:
{{"guess": [0, 1, 2, 3]}}"""

            result = litellm.completion(
                model=self.llm_config.parser_model,
                messages=[{"role": "user", "content": parser_prompt}],
                temperature=0,
                max_tokens=100
            )

            parser_response = result.choices[0].message.content
            return self._parse_response(parser_response)

        except Exception:
            return None
