# Mastermind LLM Benchmark

A Python CLI tool for benchmarking LLM logical deduction capabilities through the game Mastermind. Supports:
- **100+ LLM providers** via LiteLLM API (OpenAI, Anthropic, Google, DeepSeek, etc.)
- **CLI auto-detection** for Claude Code, OpenAI Codex, and Gemini CLI tools (free with subscription)
- **Clipboard mode** for manual testing of web-based interfaces

## Overview

This tool evaluates how well language models can play Mastermind, a deduction game where players must guess a secret code through iterative feedback. Each guess receives feedback in the form of black pegs (correct color in correct position) and white pegs (correct color in wrong position), but not which positions are correct.

The benchmark is useful for assessing:

- Logical deduction under uncertainty
- Pattern recognition across sequential attempts
- Ability to maintain and update hypotheses
- Adherence to structured output formats

## Installation

```bash
pip install -r requirements.txt
```

Create a `.env` file with API keys for your chosen providers:

```bash
cp .env.example .env
# Edit .env with your API keys
```

## Quick Start

### CLI Auto-Detection (FREE with subscription)

Run from Claude Code CLI - automatically detects and uses local CLI:

```bash
claude --print "python -m src.main --runs 10"
```

From Codex or Gemini CLI:

```bash
codex --print "python -m src.main --runs 10"
gemini --print "python -m src.main --runs 10"
```

### API Mode (PAID - uses API keys)

Run with any LLM provider via API:

```bash
# DeepSeek
python -m src.main --model deepseek/deepseek-chat --runs 10

# OpenAI
python -m src.main --model gpt-4 --runs 10

# Anthropic
python -m src.main --model claude-3-5-sonnet-20241022 --runs 10

# Google
python -m src.main --model gemini/gemini-pro --runs 10
```

### Clipboard Mode (Manual Testing)

Test web UIs manually:

```bash
python -m src.main --mode clipboard --model "chatgpt-web"
```

## Configuration Options

### Mode Selection

```
--mode MODE    Execution mode: auto (default), api, cli, clipboard
```

- **auto** (default): Automatically detects CLI parent process (claude/codex/gemini) and uses CLI. Falls back to requiring --model.
- **api**: Uses LiteLLM to call any LLM provider via API (requires --model)
- **cli**: Forces CLI mode (requires running from CLI tool or --model with cli tool name)
- **clipboard**: Manual input mode for testing web UIs

### Game Parameters

```
--colors N         Number of distinct colors (default: 6)
--pegs N          Length of the secret code (default: 4)
--no-duplicates   Disallow repeated colors in the secret
--max-turns N     Maximum number of guesses (default: 12)
--secret X,Y,Z    Use a specific secret for reproducibility
```

### LLM Parameters (API mode)

```
--model NAME           LiteLLM model string (required)
--temperature N        Sampling temperature (default: 0.7)
--max-tokens N         Max response tokens (default: 500)
--parser-fallback      Use GPT-3.5 to parse malformed responses
--parser-model NAME    Model for parsing fallback
--max-retries N        Retries for invalid guesses (default: 1)
```

### Execution Parameters

```
--runs N            Number of games to run (default: 1)
--output PATH       Custom output file path
--seed N            Random seed for reproducibility
--verbose           Show detailed turn-by-turn output
--max-api-calls N   Maximum API calls per game (default: 100, safety limit)
--timeout N         Maximum seconds per game (default: 300, safety limit)
```

## Model Compatibility

### API Mode (via LiteLLM)

The tool uses LiteLLM, which provides a unified interface to 100+ LLM providers. Model string examples:

- DeepSeek: `deepseek/deepseek-chat`, `deepseek/deepseek-coder`, `deepseek/deepseek-reasoner`
- OpenAI: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`
- Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- Google: `gemini/gemini-pro`, `gemini/gemini-1.5-pro`
- Azure, AWS Bedrock, Cohere, Mistral, and 90+ more: See [LiteLLM documentation](https://docs.litellm.ai/docs/providers)

### CLI Mode (Local Tools)

Supports local CLI tools with automatic detection:

- **Claude Code CLI**: Run `claude --version` to verify installation (from Claude Max subscription)
- **OpenAI Codex CLI**: Run `codex --version` to verify installation (from ChatGPT Pro subscription)
- **Gemini CLI**: Run `gemini --version` to verify installation

When running from these CLIs, the tool automatically detects the parent process and uses the local CLI instead of API calls.

## Output Format

Results are saved as JSONL (one JSON object per line), with each game containing:

```json
{
  "config": {
    "num_colors": 6,
    "num_pegs": 4,
    "allow_duplicates": true,
    "max_turns": null
  },
  "llm_config": {
    "mode": "api",
    "model": "deepseek/deepseek-chat",
    "temperature": 0.7,
    "max_tokens": 500
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
    }
  ],
  "outcome": "win",
  "total_turns": 5,
  "timestamp": "2024-01-15T14:23:45Z",
  "duration_seconds": 12.3,
  "total_tokens": {"input": 1245, "output": 156}
}
```

## Clipboard Mode

For testing web-based LLM interfaces (ChatGPT, Claude.ai, etc.) that lack API access:

1. Run with `--mode clipboard`
2. The prompt is automatically copied to your clipboard
3. Paste it into the web interface
4. Copy the response
5. Press Enter to read from clipboard (or paste manually)
6. Repeat until game completes

This mode preserves full game history and outputs the same JSONL format as API mode.

## Analysis

Key metrics to examine:

- **Win rate**: Percentage of games solved within max_turns
- **Average turns to win**: Efficiency of the deduction strategy
- **Parse failures**: How often the model fails to follow JSON format
- **Invalid guesses**: Frequency of rule violations (wrong length, out of bounds, etc.)
- **Token usage**: Cost considerations for different models

Common patterns observed:

- Models often start with systematic coverage strategies
- Performance degrades with increased num_colors or num_pegs
- Temperature affects consistency more than win rate
- Parser fallback reduces format errors by approximately 60%

## Implementation Notes

### Safety Limits

To prevent runaway API costs, the tool includes multiple safety limits:

- **Max turns per game**: Default 12 turns (configurable with `--max-turns`)
- **Max API calls per game**: Default 100 calls (configurable with `--max-api-calls`)
- **Timeout per game**: Default 300 seconds / 5 minutes (configurable with `--timeout`)

If any limit is reached, the game terminates with `outcome: "loss"` or `outcome: "error"` and saves partial results. These limits protect against:
- LLMs getting stuck in reasoning loops
- Infinite retry loops from API errors
- Slow/hanging API responses
- Bugs causing excessive API calls
- Unexpected cost escalation

For harder games requiring more turns, increase limits accordingly:
```bash
python -m src.main --model deepseek/deepseek-chat --max-turns 20 --max-api-calls 200 --timeout 600
```

### Error Handling

The tool implements several layers of error handling:

- Network errors: 3 retries with exponential backoff
- Parse errors: Optional parser model fallback
- Invalid guesses: Configurable retries, then counted as failed turns
- Fatal errors: Partial game state saved with `outcome: "error"`
- Safety limits: Automatic termination if limits exceeded

### Deterministic Behavior

When `--seed` is specified:

- All random secret generation uses the seeded RNG
- Each game in a multi-run batch gets a different secret
- LLM sampling is not seeded (provider-dependent)

Using `--secret` with `--seed` ensures identical game conditions across runs.

### Cost Considerations

The tool logs token counts but does not estimate costs (provider pricing varies). Calculate costs post-hoc based on your pricing tier. A typical game uses 1000-3000 input tokens and 200-500 output tokens.

For expensive models, test with `--runs 1` first.

## Testing Recommendations

Validate the implementation with these edge cases:

- All correct on first guess
- All wrong colors
- Correct colors, all wrong positions
- No duplicates mode with duplicate guess
- Max turns reached without winning
- Malformed JSON responses
- Network errors during game

## Contributing

The codebase is organized into discrete modules:

- `game.py`: Core Mastermind logic (no external dependencies)
- `llm_player.py`: LiteLLM integration and response parsing
- `clipboard_player.py`: Manual input workflow
- `runner.py`: Game session management and result tracking
- `main.py`: CLI argument parsing and orchestration

All functions include type hints and docstrings.

## License

MIT
