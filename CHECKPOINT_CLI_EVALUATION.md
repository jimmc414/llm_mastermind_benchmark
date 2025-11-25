# CLI Evaluation Checkpoint

**Date:** 2025-11-24
**Status:** Ready for final evaluation runs

---

## Final Claude CLI Configurations

Based on systematic testing, we have two optimal configurations:

### Configuration 1: Baseline (json-schema)
```bash
claude --print --output-format json --json-schema '{schema}'
```
- **Win Rate:** 80% (4/5)
- **Avg Turns:** 8.0
- Uses constrained decoding for guaranteed valid JSON

### Configuration 2: Optimal (json-schema + strategy)
```bash
claude --print --output-format json --json-schema '{schema}' \
  --append-system-prompt "Use minimax strategy for Mastermind. Eliminate maximum possibilities each turn."
```
- **Win Rate:** 100% (5/5)
- **Avg Turns:** 5.0
- **Best Win:** 2 turns!

---

## Test Results Summary

| Test | Configuration | Win Rate | Avg Turns | Key Finding |
|------|--------------|----------|-----------|-------------|
| A | `--json-schema` (baseline) | 80% | 8.0 | Constrained decoding works |
| B | No `--output-format json` | 0% | - | BROKEN - empty stdout |
| C | `--print` only | 60% | 9.7 | Text parsing fallback |
| D | `--tools StructuredOutput` | 40% | 9.0 | Tool restriction hurt |
| E | `--no-json-schema` | 0%* | - | *Parsing failure, model was correct |
| G | `--model-override sonnet` | 40% | 5.5 | Sonnet faster but less reliable |
| H | `--append-prompt strategy` | **100%** | **5.0** | **BEST - strategy prompts work!** |
| J | `--no-tools` | 80% | 7.8 | Schema works without tools |
| K | `--prompt-prefix Ultrathink` | 0% | - | DEFERRED - too slow (timeout) |
| L | `--strict-schema` | 50% | 9.0 | Strict mode slightly worse |

---

## Key Technical Findings

1. **`--json-schema` uses constrained decoding** - compiles schema into grammar, restricts token generation
2. **`--output-format json` is REQUIRED** with `--json-schema` (Test B proved this)
3. **Strategy prompts dramatically improve performance** - 100% vs 80% baseline
4. **Sonnet is faster but less reliable** - wins in 5-6 turns when it works
5. **Parsing errors ≠ model errors** - Test E showed model gave correct answers but parser couldn't extract from nested JSON

---

## Code Changes Made

### New Features Added:
1. **Per-turn logging** (`--turn-log` flag) - real-time progress monitoring
2. **Parameterized CLI config** - `CLIConfig` dataclass with test flags
3. **Reporter enhancements** - now shows min/max turns and individual win turn counts

### Files Modified:
- `src/cli_player.py` - CLIConfig with test flags, dynamic command building
- `src/main.py` - New CLI arguments, turn callback support
- `src/runner.py` - Turn callback mechanism
- `src/reporter.py` - Enhanced statistics with turn counts

---

## Next Steps for Final Evaluation

1. Run 20-50 games with Configuration 1 (baseline)
2. Run 20-50 games with Configuration 2 (strategy)
3. Compare results statistically
4. Document findings

### Suggested Commands:

```bash
# Baseline evaluation (20 runs)
python -m src.main --mode cli --runs 20 \
  --output outputs/eval_baseline.jsonl \
  --turn-log outputs/eval_baseline_turns.jsonl

# Strategy evaluation (20 runs)
python -m src.main --mode cli --runs 20 \
  --output outputs/eval_strategy.jsonl \
  --turn-log outputs/eval_strategy_turns.jsonl \
  --append-prompt "Use minimax strategy for Mastermind. Eliminate maximum possibilities each turn."
```

---

## Output Files

### Test Results:
- `outputs/upgrade_test_a.jsonl` through `_l.jsonl` - All test results
- `outputs/upgrade_test_*_turns.jsonl` - Per-turn logs (K, L)

### Documentation:
- `CHECKPOINT_CLI_FLAG_INVESTIGATION.md` - Original investigation
- `IMPLEMENTATION.md` - Implementation guide
- `CHECKPOINT_CLI_EVALUATION.md` - This file

---

## Model Information

- **Default Model:** Opus 4.5 (claude-opus-4-5-20251101)
- **Test G used:** Sonnet 4.5 (claude-sonnet-4-5-20250929)
