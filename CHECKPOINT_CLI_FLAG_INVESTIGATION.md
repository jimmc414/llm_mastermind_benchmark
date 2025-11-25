# Claude CLI Flag Investigation Checkpoint

**Date:** 2025-11-24
**Purpose:** Systematic analysis of Claude CLI flags that could affect Mastermind benchmark performance
**Status:** Pre-test analysis complete, ready for systematic testing

---

## Executive Summary

We discovered that `--json-schema` uses **constrained decoding** (not just validation) which guarantees valid JSON output. This explains why Test A (80% win rate) significantly outperforms Test C (60% win rate).

Key finding: The combination `--output-format json --json-schema` is essential for optimal performance.

---

## Test Results So Far (Opus 4.5)

| Test | Flags | Win Rate | File Size | Analysis |
|------|-------|----------|-----------|----------|
| **A** | `--print --output-format json --json-schema` | **80%** (4/5) | 231KB | BEST - constrained decoding |
| **B** | `--print --json-schema` (no output-format) | **0%** (0/5) | 13KB | BROKEN - empty stdout |
| **C** | `--print` only | **60%** (3/5) | 70KB | Works via text parsing |
| **D** | `--print --output-format json --json-schema --tools StructuredOutput` | **40%** (2/5) | 272KB | Crippled - only 1 tool |

---

## First Principles Analysis: What Could Affect Mastermind Score?

### Category 1: OUTPUT MECHANICS (How Claude delivers the answer)

These flags affect HOW Claude formats and delivers its response:

| Flag | Could Affect Score? | Mechanism | Priority |
|------|---------------------|-----------|----------|
| `--output-format json` | **YES** | Determines output format (text vs JSON transcript) | HIGH |
| `--json-schema` | **YES** | Enables constrained decoding, guarantees valid JSON | HIGH |
| `--output-format text` | **YES** | Default - requires text parsing (error-prone) | HIGH |
| `--output-format stream-json` | Maybe | Streaming might affect context handling | LOW |

### Category 2: MODEL SELECTION (Which AI does the work)

| Flag | Could Affect Score? | Mechanism | Priority |
|------|---------------------|-----------|----------|
| `--model opus` | **YES** | Different models have different reasoning ability | HIGH |
| `--model sonnet` | **YES** | Sonnet vs Opus comparison | HIGH |
| `--fallback-model` | Maybe | If primary overloaded, fallback might be weaker | LOW |

### Category 3: TOOL AVAILABILITY (What Claude can use)

| Flag | Could Affect Score? | Mechanism | Priority |
|------|---------------------|-----------|----------|
| `--tools ""` | **YES** | No tools = no StructuredOutput = must parse text | HIGH |
| `--tools default` | **YES** | All tools available | HIGH |
| `--tools "X,Y,Z"` | **YES** | Restricting tools might break orchestration | HIGH |
| `--allowedTools` | Maybe | Adds tools, shouldn't hurt | LOW |
| `--disallowedTools` | Maybe | Removing tools could affect behavior | MEDIUM |

### Category 4: CONTEXT & REASONING (How Claude thinks)

| Flag | Could Affect Score? | Mechanism | Priority |
|------|---------------------|-----------|----------|
| `--system-prompt` | **YES** | Changes how Claude approaches the task | HIGH |
| `--append-system-prompt` | **YES** | Adds instructions to default prompt | HIGH |
| `--max-turns` | Maybe | Limiting turns could cut off reasoning | MEDIUM |
| Prompt keywords: "Ultrathink" | Maybe | Could trigger deeper analysis | MEDIUM |

### Category 5: SESSION & STATE (Context preservation)

| Flag | Could Affect Score? | Mechanism | Priority |
|------|---------------------|-----------|----------|
| `--continue` | Maybe | Preserves context across calls | LOW |
| `--resume` | Maybe | Resumes previous session state | LOW |
| `--session-id` | Maybe | Forces specific session | LOW |

### Category 6: PERMISSION & SAFETY (Shouldn't affect reasoning)

| Flag | Could Affect Score? | Mechanism | Priority |
|------|---------------------|-----------|----------|
| `--permission-mode` | Unlikely | Controls tool approval, not reasoning | LOW |
| `--dangerously-skip-permissions` | Unlikely | Safety bypass, shouldn't affect logic | LOW |

### Category 7: ENVIRONMENT (External factors)

| Flag | Could Affect Score? | Mechanism | Priority |
|------|---------------------|-----------|----------|
| `--add-dir` | Unlikely | Adds context directories | LOW |
| `--verbose` | Unlikely | Logging only | LOW |
| `--debug` | Unlikely | Debug output only | LOW |

---

## HIGH PRIORITY Tests Needed

Based on first-principles analysis, these flag combinations could meaningfully affect Mastermind performance:

### Test E: `--output-format json` without `--json-schema`
**Hypothesis:** Without constrained decoding, Claude might produce invalid JSON
```bash
cmd = ['claude', '--print', '--output-format', 'json']
```
**Expected:** Lower win rate than Test A (maybe ~60-70%?)

### Test F: `--json-schema` with stricter schema
**Hypothesis:** Adding `additionalProperties: false` might help
```bash
--json-schema '{"type":"object","properties":{"guess":{"type":"array","items":{"type":"integer"}}},"required":["guess"],"additionalProperties":false}'
```
**Expected:** Same or slightly better than Test A

### Test G: `--model sonnet` vs `--model opus`
**Hypothesis:** Model capability directly affects reasoning
```bash
cmd = ['claude', '--print', '--output-format', 'json', '--json-schema', schema, '--model', 'sonnet']
```
**Expected:** Lower win rate than Opus (maybe ~50-60%?)

### Test H: With `--append-system-prompt` for Mastermind strategy
**Hypothesis:** Better instructions could improve performance
```bash
--append-system-prompt "Use minimax strategy for Mastermind. Eliminate maximum possibilities each turn."
```
**Expected:** Potentially higher win rate

### Test I: `--tools default` explicit
**Hypothesis:** Verify explicit default matches implicit default
```bash
cmd = ['claude', '--print', '--output-format', 'json', '--json-schema', schema, '--tools', 'default']
```
**Expected:** Same as Test A (80%)

### Test J: `--tools ""` (no tools)
**Hypothesis:** Without tools, must rely on text parsing
```bash
cmd = ['claude', '--print', '--output-format', 'json', '--json-schema', schema, '--tools', '']
```
**Expected:** Lower win rate or broken (constrained decoding might still work?)

---

## Medium Priority Tests

### Test K: Prompt with "Ultrathink" keyword
**Hypothesis:** Triggers extended thinking mode
```bash
prompt = "Ultrathink. " + original_prompt
```

### Test L: `--max-turns 1` (single turn per call)
**Hypothesis:** Already our mode, but verify behavior

---

## Key Technical Findings

### 1. Dual-Model Architecture Confirmed
Claude Code uses TWO models per turn:
- **Haiku 4.5**: Orchestration layer (~$0.002-0.005/turn)
- **Opus 4.5**: Reasoning layer (~$0.03-0.13/turn)

### 2. Tool Counts by Configuration
- Test A (baseline): **18 tools** including StructuredOutput
- Test D (--tools StructuredOutput): **1 tool** - BROKEN
- Without --json-schema: **17 tools** (no StructuredOutput)

### 3. Constrained Decoding
The `--json-schema` flag:
- Compiles schema into a grammar
- Restricts token generation at decode time
- NOT just post-validation
- First use has compilation latency (cached 24h)

### 4. Schema Limitations
- No recursive schemas
- Numerical constraints (min/max) need post-validation
- `additionalProperties: false` recommended for strict matching

---

## Current Implementation

**File:** `src/cli_player.py` line 176

```python
if cli_tool == 'claude':
    schema = self._build_json_schema()
    cmd = ['claude', '--print', '--output-format', 'json', '--json-schema', schema]
    stdin_input = prompt
```

**JSON Schema Used:**
```json
{
  "type": "object",
  "properties": {
    "guess": {
      "type": "array",
      "items": {"type": "integer"},
      "minItems": 4,
      "maxItems": 4
    }
  },
  "required": ["guess"]
}
```

---

## Output Files Created

- `outputs/upgrade_test_a.jsonl` - 231KB, 5 games, 80% win
- `outputs/upgrade_test_b.jsonl` - 13KB, 5 games, 0% win (broken)
- `outputs/upgrade_test_c.jsonl` - 70KB, 5 games, 60% win
- `outputs/upgrade_test_d.jsonl` - 272KB, 5 games, 40% win

---

## Questions to Answer

1. **Does `--output-format json` alone enable any structured output capability?**
2. **Is the StructuredOutput tool REQUIRED when using `--json-schema`?**
3. **Does `--tools ""` disable constrained decoding?**
4. **How much does model choice (Opus vs Sonnet) affect win rate?**
5. **Can prompt engineering ("Ultrathink") improve performance?**

---

## Reference Documents

- `claude-code-cli-reference.md` - Updated CLI documentation
- `INVESTIGATION_CHECKPOINT.md` - Previous investigation findings
- `claude --help` output - Authoritative flag list

---

## Next Steps

1. Run Test E (`--output-format json` without schema)
2. Run Test G (`--model sonnet` comparison)
3. Run Test J (`--tools ""` to test constrained decoding without tools)
4. Analyze results and determine optimal configuration
5. Update `cli_player.py` if better configuration found
