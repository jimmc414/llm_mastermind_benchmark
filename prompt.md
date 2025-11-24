```markdown
# Mastermind LLM Benchmark - Complete Implementation Specification

## Project Overview
Build a Python CLI tool that benchmarks LLM logical deduction capabilities by having them play Mastermind. Supports configurable game parameters, multiple LLM providers via LiteLLM, manual clipboard mode for web UIs, and comprehensive data logging.

## Technical Requirements

### Dependencies
```
python>=3.10
litellm>=1.0.0
python-dotenv>=1.0.0
pyperclip>=1.8.0
```

### Project Structure
```
mastermind-benchmark/
├── README.md
├── requirements.txt
├── .env.example
├── src/
│   ├── __init__.py
│   ├── game.py          # Core Mastermind game logic
│   ├── llm_player.py    # LLM interface and response parsing
│   ├── clipboard_player.py  # Manual input mode
│   ├── runner.py        # Game session management
│   └── main.py          # CLI entry point
├── prompts/
│   └── system_prompt.txt
└── outputs/
    └── .gitkeep
```

## Module Specifications

### 1. game.py - MastermindGame Class

**Core Configuration:**
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class GameConfig:
    num_colors: int = 6
    num_pegs: int = 4
    allow_duplicates: bool = True
    max_turns: Optional[int] = None  # None = unlimited
```

**Game Class:**
```python
class MastermindGame:
    def __init__(self, config: GameConfig, secret: Optional[list[int]] = None):
        """
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
        import random
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
        return self.turns
```

### 2. llm_player.py - LLM API Interface

**Configuration:**
```python
@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.7
    max_tokens: int = 500
    use_parser_fallback: bool = False
    parser_model: str = "gpt-3.5-turbo"
    max_retries: int = 1  # Retries for invalid guesses
```

**LLM Player Class:**
```python
import litellm
import json
import time
from typing import Optional

class LLMPlayer:
    def __init__(self, game_config: GameConfig, llm_config: LLMConfig):
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
{"guess": [0, 1, 2, 3]}

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
            import re
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
```

### 3. clipboard_player.py - Manual Input Mode

```python
import pyperclip

class ClipboardPlayer:
    def __init__(self, game_config: GameConfig, model_label: str = "manual"):
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
        """Same as LLMPlayer._build_system_prompt()."""
        # [Identical implementation to LLMPlayer]
        pass
    
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
        """Same as LLMPlayer._parse_response()."""
        # [Identical implementation to LLMPlayer]
        pass
```

### 4. runner.py - GameSession Management

```python
from dataclasses import dataclass, asdict
from datetime import datetime
import time
from typing import Optional

@dataclass
class GameResult:
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
    def __init__(self, game_config: GameConfig, player, max_retries: int = 1):
        self.game_config = game_config
        self.player = player
        self.max_retries = max_retries
    
    def run(self) -> GameResult:
        """Run a complete game and return results."""
        start_time = time.time()
        game = MastermindGame(self.game_config)
        
        turns = []
        total_tokens = {"input": 0, "output": 0}
        outcome = "loss"
        
        try:
            while not game.is_game_over():
                turn_result = self._execute_turn(game, turns)
                turns.append(turn_result)
                
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
        else:  # ClipboardPlayer
            return {
                "mode": "clipboard",
                "model": self.player.model_label,
                "temperature": None,
                "max_tokens": None
            }
```

### 5. main.py - CLI Entry Point

```python
import argparse
import json
import random
import sys
from pathlib import Path
from datetime import datetime

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
    print(f"Output: {output_path}")
    print()
    
    results_summary = {"wins": 0, "losses": 0, "errors": 0}
    
    with open(output_path, 'a') as f:
        for run in range(1, args.runs + 1):
            print(f"Game {run}/{args.runs}")
            
            # Use predefined secret if provided, else generate new one
            if predefined_secret:
                game_config_with_secret = GameConfig(
                    num_colors=game_config.num_colors,
                    num_pegs=game_config.num_pegs,
                    allow_duplicates=game_config.allow_duplicates,
                    max_turns=game_config.max_turns
                )
                # Pass secret to game in runner
                session = GameSession(game_config_with_secret, player, args.max_retries)
                # Modify runner to accept optional secret - OR simpler: create game with secret
                # For simplicity, modify GameConfig to include secret
                from dataclasses import replace
                temp_game = MastermindGame(game_config, secret=predefined_secret)
                game_config_for_session = game_config
            else:
                game_config_for_session = game_config
            
            session = GameSession(game_config_for_session, player, args.max_retries)
            
            # If predefined secret, need to pass to game somehow
            # Simplest: modify GameSession to accept optional secret parameter
            result = session.run()
            
            # If predefined_secret, override the result's secret
            if predefined_secret:
                result.secret = predefined_secret
            
            # Update summary
            results_summary[result.outcome + "s"] += 1
            
            # Write result
            f.write(json.dumps(asdict(result)) + '\n')
            f.flush()
            
            # Print summary
            if result.outcome == "win":
                print(f"  ✓ Won in {result.total_turns} turns")
            elif result.outcome == "loss":
                print(f"  ✗ Lost after {result.total_turns} turns")
            else:
                print(f"  ! Error: {result.turns[-1].get('error', 'Unknown error')}")
            
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
```

## Additional Files

### .env.example
```
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# Google
GOOGLE_API_KEY=...

# Add other provider keys as needed
```

### requirements.txt
```
litellm>=1.0.0
python-dotenv>=1.0.0
pyperclip>=1.8.0
```

## README.md Structure

Include sections on:

1. **Overview** - What this benchmarks and why
2. **Installation** - pip install, API key setup
3. **Quick Start** - Basic usage examples
4. **Configuration** - All CLI flags explained
5. **Output Format** - JSONL structure documented
6. **Model Compatibility** - Tested models and known issues
7. **Analysis Tips** - What metrics to look for
8. **Contributing** - How to add new features

## Implementation Notes

### Error Handling Details

1. **Network errors (API calls):** 3 retries with exponential backoff (1s, 2s, 4s)
2. **Parse errors:** 1 retry with parser fallback if enabled, else fail
3. **Invalid guesses:** Up to `--max-retries` attempts (default 1), then counts as wasted turn with 0B/0W feedback
4. **Fatal errors:** Save partial game data with `outcome="error"`

### Deterministic Behavior

When `--seed` is provided:
- All random secret generation uses the seeded RNG
- Each game in a multi-run batch gets a different secret (unless `--secret` is specified)
- LLM sampling is NOT seeded (depends on provider support)

### Clipboard Mode Workflow

1. Program builds prompt with system message + history
2. Copies prompt to clipboard automatically
3. User pastes into web UI (ChatGPT, Claude.ai, etc.)
4. User copies LLM response
5. Press Enter to paste from clipboard, or type/paste manually
6. Program parses response and continues game
7. Repeat until game ends

### Cost Considerations

- Only token counts are logged (input/output)
- No cost estimation (provider pricing changes frequently)
- Users calculate costs post-hoc based on their pricing tier
- Batch mode can be expensive - start with `--runs 1` to test

### Validation Edge Cases

- Empty guesses: Reject with clear error
- Float values: Reject (must be integers)
- Out of range: Reject with min/max values
- Wrong length: Reject with expected length
- Non-list types: Reject with format explanation

### Testing Recommendations

Test these scenarios:
1. All correct on first guess
2. All wrong colors
3. Correct colors, all wrong positions  
4. No duplicates mode with duplicate guess
5. Max turns reached without winning
6. Malformed JSON responses
7. Network errors during game
8. Clipboard mode complete workflow

## Output Format Example

```json
{
  "config": {
    "num_colors": 6,
    "num_pegs": 4,
    "allow_duplicates": true,
    "max_turns": 12
  },
  "llm_config": {
    "mode": "api",
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 500,
    "use_parser_fallback": false,
    "parser_model": null
  },
  "secret": [3, 1, 4, 2],
  "turns": [
    {
      "turn_number": 1,
      "guess": [0, 1, 2, 3],
      "feedback": {"black": 1, "white": 2},
      "raw_response": "{\"guess\": [0, 1, 2, 3]}",
      "parsed": true,
      "error": null,
      "tokens": {"input": 245, "output": 28}
    },
    {
      "turn_number": 2,
      "guess": [3, 1, 4, 2],
      "feedback": {"black": 4, "white": 0},
      "raw_response": "{\"guess\": [3, 1, 4, 2]}",
      "parsed": true,
      "error": null,
      "tokens": {"input": 312, "output": 32}
    }
  ],
  "outcome": "win",
  "total_turns": 2,
  "timestamp": "2024-01-15T14:23:45Z",
  "duration_seconds": 8.3,
  "total_tokens": {"input": 557, "output": 60}
}
```

## Final Checklist

- [ ] All modules have type hints
- [ ] All functions have docstrings
- [ ] Error messages are clear and actionable
- [ ] CLI help text is comprehensive
- [ ] Output format is consistent and complete
- [ ] Clipboard mode works smoothly
- [ ] API mode handles all common errors
- [ ] README covers all use cases
- [ ] .env.example lists all required keys
- [ ] Code is production-quality

This specification is complete and unambiguous. Implement exactly as written.
```