"""CLI interface for local LLM tools (Claude Code, Codex, Gemini)."""

import subprocess
from dataclasses import dataclass
from typing import Optional

from .game import GameConfig


class CLIError(Exception):
    """Base exception for CLI-related issues."""
    pass


class CLINotFoundError(CLIError):
    """Raised when the CLI executable is not found."""
    pass


class CLITimeoutError(CLIError):
    """Raised when the CLI command times out."""
    pass


@dataclass
class CLIConfig:
    """Configuration for CLI calls."""
    cli_tool: str  # 'claude', 'codex', or 'gemini'
    timeout: int = 120  # seconds


class CLIPlayer:
    """Player that uses a local CLI tool to generate guesses."""

    def __init__(self, game_config: GameConfig, cli_config: CLIConfig):
        """
        Initialize CLI player.

        Args:
            game_config: Game configuration
            cli_config: CLI tool configuration
        """
        self.game_config = game_config
        self.cli_config = cli_config
        self.system_prompt = self._build_system_prompt()

    def get_next_guess(self, game_history: list[dict], retry_count: int = 0) -> dict:
        """
        Get next guess from CLI tool.

        Returns:
            {
                "guess": list[int] | None,
                "raw_response": str,
                "parsed": bool,
                "error": str | None,
                "tokens": dict  # {"input": 0, "output": 0} - CLI doesn't report tokens
            }
        """
        try:
            # Build prompt
            prompt = self._build_prompt(game_history, retry_count)

            # Call CLI tool
            response = self._call_cli(prompt)

            # Parse response
            guess = self._parse_response(response)

            return {
                "guess": guess,
                "raw_response": response,
                "parsed": guess is not None,
                "error": None if guess is not None else "Failed to parse response",
                "tokens": {"input": 0, "output": 0}  # CLI tools don't report token counts
            }

        except Exception as e:
            return {
                "guess": None,
                "raw_response": "",
                "parsed": False,
                "error": str(e),
                "tokens": {"input": 0, "output": 0}
            }

    def _build_system_prompt(self) -> str:
        """Build system prompt based on game configuration."""
        duplicates_text = (
            "Duplicate colors are allowed."
            if self.game_config.allow_duplicates
            else "All colors must be unique."
        )

        turns_text = (
            f"You have a maximum of {self.game_config.max_turns} guesses."
            if self.game_config.max_turns
            else "You have unlimited guesses."
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
You MUST respond with a valid JSON object containing your guess.
If you want to explain your reasoning, put the JSON object at the very end of your response.

Required format:
{{"guess": [0, 1, 2, 3]}}

CRITICAL: The JSON must be valid and parseable. Wrap it in ```json code fences if including explanations."""

    def _build_json_schema(self) -> str:
        """Build JSON schema for structured output validation."""
        import json
        schema = {
            "type": "object",
            "properties": {
                "guess": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": self.game_config.num_pegs,
                    "maxItems": self.game_config.num_pegs
                }
            },
            "required": ["guess"]
        }
        return json.dumps(schema)

    def _build_prompt(self, game_history: list[dict], retry_count: int) -> str:
        """Build prompt text for CLI tool."""
        parts = [f"System: {self.system_prompt}"]

        # Build history
        if not game_history:
            parts.append("Human: Make your first guess.")
        else:
            parts.append("Human: Previous guesses:\n")
            for i, turn in enumerate(game_history, 1):
                parts.append(f"Turn {i}:")
                parts.append(f"Guess: {turn['guess']}")
                if turn.get('feedback'):
                    fb = turn['feedback']
                    parts.append(f"Feedback: {fb['black']} black, {fb['white']} white")
                elif turn.get('error'):
                    parts.append(f"Error: {turn['error']}")
                parts.append("")

            if retry_count > 0:
                parts.append("Your last guess was invalid. Please provide a valid guess in the correct JSON format.")
            else:
                parts.append("Provide your next guess.")

        parts.append("\nAssistant:")

        return "\n".join(parts)

    def _call_cli(self, prompt: str) -> str:
        """Call the CLI tool with the prompt."""
        cli_tool = self.cli_config.cli_tool

        # Build command with output format flags
        if cli_tool == 'claude':
            # Use JSON schema for structured output validation
            schema = self._build_json_schema()
            cmd = ['claude', '--print', '--output-format', 'json', '--json-schema', schema]
            stdin_input = prompt
        elif cli_tool == 'codex':
            # Codex uses exec subcommand with positional arguments
            # No JSON output format available, relies on parser
            cmd = ['codex', 'exec', prompt]
            stdin_input = None
        elif cli_tool == 'gemini':
            # Gemini uses positional arguments for prompts, not stdin
            cmd = ['gemini', '--output-format', 'json', prompt]
            stdin_input = None
        else:
            raise CLIError(f"Unknown CLI tool: {cli_tool}")

        try:
            result = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=self.cli_config.timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or "Unknown error"
                raise CLIError(f"{cli_tool} CLI error: {error_msg}")

            return result.stdout.strip()

        except subprocess.TimeoutExpired:
            raise CLITimeoutError(f"{cli_tool} CLI timed out after {self.cli_config.timeout} seconds")
        except FileNotFoundError:
            raise CLINotFoundError(
                f"{cli_tool} CLI not found. Please ensure '{cli_tool}' is installed and in PATH"
            )
        except Exception as e:
            if isinstance(e, (CLIError, CLITimeoutError, CLINotFoundError)):
                raise
            raise CLIError(f"Error calling {cli_tool}: {str(e)}")

    def _parse_response(self, response: str) -> Optional[list[int]]:
        """Extract guess from JSON response."""
        import json
        import re

        # Gemini CLI wraps responses in {"response": "...", "stats": {...}}
        # Extract the actual response content first
        try:
            wrapper = json.loads(response.strip())
            if "response" in wrapper and isinstance(wrapper["response"], str):
                response = wrapper["response"]
        except json.JSONDecodeError:
            pass

        # Strategy 1: Try direct JSON parse
        try:
            data = json.loads(response.strip())
            if "guess" in data and isinstance(data["guess"], list):
                return data["guess"]
        except json.JSONDecodeError:
            pass

        # Strategy 2: Try to extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "guess" in data and isinstance(data["guess"], list):
                    return data["guess"]
            except json.JSONDecodeError:
                pass

        # Strategy 3: Try to find last JSON object in response (without code fence)
        # Look for patterns like {"guess": [1, 2, 3, 4]} at the end
        json_pattern = r'\{\s*"guess"\s*:\s*\[[\d,\s]+\]\s*\}'
        matches = list(re.finditer(json_pattern, response))
        if matches:
            # Try parsing the last match
            last_match = matches[-1]
            try:
                data = json.loads(last_match.group(0))
                if "guess" in data and isinstance(data["guess"], list):
                    return data["guess"]
            except json.JSONDecodeError:
                pass

        return None
