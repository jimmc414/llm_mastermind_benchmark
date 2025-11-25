# CLI Flag Testing Implementation Guide

## Purpose
This document provides detailed implementation instructions for parameterized CLI flag testing in the Mastermind benchmark.

---

## Baseline Results (Completed)

| Test | Flags | Win Rate | Notes |
|------|-------|----------|-------|
| A | `--print --output-format json --json-schema` | 80% (4/5) | BEST - constrained decoding |
| B | `--print --json-schema` | 0% (0/5) | BROKEN - empty stdout |
| C | `--print` only | 60% (3/5) | Text parsing |
| D | `--print --output-format json --json-schema --tools StructuredOutput` | 40% (2/5) | 1 tool only |

---

## STEP 1: Modify CLIConfig Dataclass

**File:** `src/cli_player.py` (lines 25-29)

**Current code:**
```python
@dataclass
class CLIConfig:
    """Configuration for CLI calls."""
    cli_tool: str  # 'claude', 'codex', or 'gemini'
    timeout: int = 120  # seconds
```

**Replace with:**
```python
@dataclass
class CLIConfig:
    """Configuration for CLI calls."""
    cli_tool: str  # 'claude', 'codex', or 'gemini'
    timeout: int = 120  # seconds

    # Test configuration flags
    use_json_schema: bool = True          # Test E: False
    use_output_format_json: bool = True   # Test B: False (already tested)
    model_override: str | None = None     # Test G: 'sonnet'
    append_system_prompt: str | None = None  # Test H: strategy text
    tools_override: str | None = None     # Test J: '' for no tools, None for default
    prompt_prefix: str | None = None      # Test K: 'Ultrathink. '
    strict_schema: bool = False           # Test L: additionalProperties: false
```

---

## STEP 2: Modify _build_json_schema Method

**File:** `src/cli_player.py` (lines 123-138)

**Current code:**
```python
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
```

**Replace with:**
```python
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
    # Test L: Add strict validation
    if self.cli_config.strict_schema:
        schema["additionalProperties"] = False
    return json.dumps(schema)
```

---

## STEP 3: Modify _build_prompt Method

**File:** `src/cli_player.py` (lines 140-166)

**Add prompt prefix support at the end of the method.**

**Find this line (around line 164):**
```python
return "\n".join(parts)
```

**Replace with:**
```python
prompt = "\n".join(parts)
# Test K: Add prompt prefix (e.g., "Ultrathink. ")
if self.cli_config.prompt_prefix:
    prompt = self.cli_config.prompt_prefix + prompt
return prompt
```

---

## STEP 4: Modify _call_cli Method (Main Change)

**File:** `src/cli_player.py` (lines 168-214)

**Replace the entire `if cli_tool == 'claude':` block (lines 173-177):**

**Current code:**
```python
if cli_tool == 'claude':
    # Use JSON schema for structured output validation
    schema = self._build_json_schema()
    cmd = ['claude', '--print', '--output-format', 'json', '--json-schema', schema]
    stdin_input = prompt
```

**Replace with:**
```python
if cli_tool == 'claude':
    cmd = ['claude', '--print']

    # Output format (Test E: with json but no schema)
    if self.cli_config.use_output_format_json:
        cmd.extend(['--output-format', 'json'])

    # JSON schema for constrained decoding
    if self.cli_config.use_json_schema:
        schema = self._build_json_schema()
        cmd.extend(['--json-schema', schema])

    # Model override (Test G: sonnet comparison)
    if self.cli_config.model_override:
        cmd.extend(['--model', self.cli_config.model_override])

    # Append system prompt (Test H: strategy hints)
    if self.cli_config.append_system_prompt:
        cmd.extend(['--append-system-prompt', self.cli_config.append_system_prompt])

    # Tools override (Test J: no tools)
    if self.cli_config.tools_override is not None:
        cmd.extend(['--tools', self.cli_config.tools_override])

    stdin_input = prompt
```

---

## STEP 5: Update main.py CLI Arguments

**File:** `src/main.py`

**Add new arguments after the existing CLI arguments (around line 130):**

```python
# CLI flag testing options
parser.add_argument(
    '--no-json-schema', action='store_true',
    help='Disable JSON schema (Test E)'
)
parser.add_argument(
    '--model-override', type=str, default=None,
    help='Override model (Test G: sonnet)'
)
parser.add_argument(
    '--append-prompt', type=str, default=None,
    help='Append to system prompt (Test H)'
)
parser.add_argument(
    '--no-tools', action='store_true',
    help='Disable all tools (Test J)'
)
parser.add_argument(
    '--prompt-prefix', type=str, default=None,
    help='Prefix for prompt (Test K: Ultrathink)'
)
parser.add_argument(
    '--strict-schema', action='store_true',
    help='Use additionalProperties:false (Test L)'
)
```

**Then update CLIConfig creation (around line 200) to use these:**

```python
cli_config = CLIConfig(
    cli_tool=cli_tool,
    timeout=120,
    use_json_schema=not args.no_json_schema,
    use_output_format_json=True,
    model_override=args.model_override,
    append_system_prompt=args.append_prompt,
    tools_override='' if args.no_tools else None,
    prompt_prefix=args.prompt_prefix,
    strict_schema=args.strict_schema
)
```

---

## STEP 6: Test Execution Commands

After implementing the above changes, run tests with these commands:

### Test E: JSON without schema
```bash
python -m src.main --mode cli --runs 5 --output outputs/upgrade_test_e.jsonl --no-json-schema
```

### Test G: Sonnet model
```bash
python -m src.main --mode cli --runs 5 --output outputs/upgrade_test_g.jsonl --model-override sonnet
```

### Test H: Strategy prompt
```bash
python -m src.main --mode cli --runs 5 --output outputs/upgrade_test_h.jsonl \
  --append-prompt "Use minimax strategy for Mastermind. Eliminate maximum possibilities each turn."
```

### Test J: No tools
```bash
python -m src.main --mode cli --runs 5 --output outputs/upgrade_test_j.jsonl --no-tools
```

### Test K: Ultrathink prompt
```bash
python -m src.main --mode cli --runs 5 --output outputs/upgrade_test_k.jsonl \
  --prompt-prefix "Ultrathink. "
```

### Test L: Strict schema
```bash
python -m src.main --mode cli --runs 5 --output outputs/upgrade_test_l.jsonl --strict-schema
```

---

## STEP 7: Analyze Results

After running all tests, analyze with:

```bash
# Quick win rate check per test
for f in outputs/upgrade_test_*.jsonl; do
  echo "=== $f ==="
  grep -o '"outcome": "[^"]*"' "$f" | sort | uniq -c
done
```

Or use the reporter:
```bash
python -m src.reporter outputs/upgrade_test_*.jsonl --format markdown
```

---

## Expected Results Summary

| Test | Command Flag | Expected Win Rate | Key Question |
|------|--------------|-------------------|--------------|
| E | `--no-json-schema` | 60-70% | Does JSON format alone help? |
| G | `--model-override sonnet` | 50-60% | How much does model matter? |
| H | `--append-prompt "..."` | 80-90%? | Do strategy hints help? |
| J | `--no-tools` | 0-20% | Does constrained decoding work without tools? |
| K | `--prompt-prefix "Ultrathink. "` | 80-85%? | Does extended thinking help? |
| L | `--strict-schema` | ~80% | Does strict validation matter? |

---

## Files Modified Summary

| File | Lines | Changes |
|------|-------|---------|
| `src/cli_player.py` | 25-29 | Add CLIConfig fields |
| `src/cli_player.py` | 123-138 | Add strict_schema support |
| `src/cli_player.py` | 164 | Add prompt_prefix support |
| `src/cli_player.py` | 173-177 | Dynamic command building |
| `src/main.py` | ~130 | New CLI arguments |
| `src/main.py` | ~200 | CLIConfig initialization |

---

## Reference Documents

- `CHECKPOINT_CLI_FLAG_INVESTIGATION.md` - Full investigation background
- `claude-code-cli-reference.md` - Official CLI documentation
- `outputs/upgrade_test_a.jsonl` through `_d.jsonl` - Baseline results

---

## Resume Prompt for Next Session

```
Implement CLI flag testing per IMPLEMENTATION.md

Follow the 7 steps to add parameterized testing support:
1. Add CLIConfig fields (cli_player.py:25-29)
2. Add strict_schema support (cli_player.py:123-138)
3. Add prompt_prefix support (cli_player.py:164)
4. Modify _call_cli for dynamic command building (cli_player.py:173-177)
5. Add CLI arguments to main.py
6. Run tests E, G, H, J, K, L
7. Analyze results
```
