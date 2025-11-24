# Mastermind LLM Benchmark

A Python CLI tool for benchmarking LLM logical deduction capabilities through the game Mastermind. Supports multiple LLM providers via LiteLLM and includes a manual clipboard mode for testing web-based interfaces.

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

Run a single game with DeepSeek:

```bash
python -m src.main --model deepseek/deepseek-chat
```

Run 10 games and save detailed results:

```bash
python -m src.main --model deepseek/deepseek-chat --runs 10 --verbose
```

Test a web UI manually using clipboard mode:

```bash
python src/main.py --mode clipboard --model "chatgpt-web"
```

## Configuration Options

### Game Parameters

```
--colors N         Number of distinct colors (default: 6)
--pegs N          Length of the secret code (default: 4)
--no-duplicates   Disallow repeated colors in the secret
--max-turns N     Limit total guesses (default: unlimited)
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
--runs N        Number of games to run (default: 1)
--output PATH   Custom output file path
--seed N        Random seed for reproducibility
--verbose       Show detailed turn-by-turn output
```

## Model Compatibility

The tool uses LiteLLM, which provides a unified interface to most major providers. Model string examples:

- DeepSeek: `deepseek/deepseek-chat`, `deepseek/deepseek-coder`, `deepseek/deepseek-reasoner`
- OpenAI: `gpt-4`, `gpt-4-turbo`, `gpt-3.5-turbo`
- Anthropic: `claude-3-5-sonnet-20241022`, `claude-3-opus-20240229`
- Google: `gemini/gemini-pro`, `gemini/gemini-1.5-pro`
- Others: See [LiteLLM documentation](https://docs.litellm.ai/docs/providers)

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

### Error Handling

The tool implements several layers of error handling:

- Network errors: 3 retries with exponential backoff
- Parse errors: Optional parser model fallback
- Invalid guesses: Configurable retries, then counted as failed turns
- Fatal errors: Partial game state saved with `outcome: "error"`

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
