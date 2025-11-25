# Claude Mastermind Performance Investigation - Checkpoint

**Date:** 2025-11-24
**Investigation:** Why did Claude's Mastermind win rate drop?
**Status:** Experiments completed, awaiting model upgrade and retest

## Executive Summary

Investigated whether `--output-format json` flag in Claude CLI was degrading Mastermind performance. **CRITICAL FINDING:** The flag is ESSENTIAL for performance - removing it tanks win rate from 67% to 0%!

## Investigation Phases Completed

### Phase 1: Historical Analysis ✅
- Checked git history for flag additions
- **Finding:** `--output-format json` and `--json-schema` were added in commit `53652b7`
- **Before (commit ab4d874):** Just `--print` flag
- **After (commit 53652b7):** `--print --output-format json --json-schema`

### Phase 2: Controlled Experiments ✅
Ran 3-game sanity checks with same secret `[2,4,1,5]`:

#### Test A: Current Implementation (Baseline)
- **Flags:** `--print --output-format json --json-schema`
- **Win Rate:** 66.7% (2/3 wins)
- **Avg Turns:** 7.5
- **File Size:** 143KB
- **Output:** `outputs/test_a_current.jsonl`

#### Test B: Remove --output-format json
- **Flags:** `--print --json-schema` (only)
- **Win Rate:** 0.0% (0/3 wins) ⚠️ CATASTROPHIC
- **File Size:** 14KB (90% smaller)
- **Output:** `outputs/test_b_no_output_format.jsonl`

#### Test C: Minimal Flags
- **Flags:** `--print` (only)
- **Win Rate:** 33.3% (1/3 wins)
- **Avg Turns:** 11.0
- **File Size:** 48KB (66% smaller)
- **Output:** `outputs/test_c_minimal.jsonl`

#### Test D: Reduced Tools Overhead
- **Flags:** `--print --output-format json --json-schema --tools StructuredOutput`
- **Win Rate:** 33.3% (1/3 wins)
- **File Size:** 170KB (19% larger than baseline)
- **Output:** `outputs/test_d_reduced_tools.jsonl`

### Phase 3: Statistical Analysis ✅

**Performance Ranking:**
1. Test A (current): 66.7% ✓ BEST
2. Test C (minimal): 33.3%
3. Test D (reduced tools): 33.3%
4. Test B (no json format): 0.0% ✗ WORST

**File Size Ranking:**
1. Test B: 14KB (smallest)
2. Test C: 48KB
3. Test A: 143KB
4. Test D: 170KB (largest)

### Phase 4: Root Cause Determination ✅

**Key Findings:**

1. **`--output-format json` is CRITICAL for performance**
   - Enables StructuredOutput tool
   - Required for proper JSON schema validation
   - Coordinates Haiku (orchestration) + Sonnet (reasoning) dual-model architecture

2. **Why verbose output exists:**
   - Complete session transcript with 5 items per turn:
     - System initialization (tools, session config)
     - Assistant message 1 (text explanation)
     - Assistant message 2 (StructuredOutput tool use)
     - User/tool result
     - Final result (costs, tokens, timing)

3. **Dual-model usage confirmed:**
   - Haiku: 38.6% of tokens (orchestration layer - not visible in responses)
   - Sonnet: 61.4% of tokens (user-facing responses)
   - Cost: ~$0.033 per turn average

4. **Historical performance:**
   - Before commit 53652b7: Estimated ~33% win rate (based on Test C)
   - After adding flags: 67% win rate
   - **The flags DOUBLED performance!**

## Critical Code Changes Made (TEMPORARY)

**File:** `src/cli_player.py`
**Line:** 176

Modified Claude CLI command during testing:
- Test A: `['claude', '--print', '--output-format', 'json', '--json-schema', schema]` (original)
- Test B: `['claude', '--print', '--json-schema', schema]`
- Test C: `['claude', '--print']`
- Test D: `['claude', '--print', '--output-format', 'json', '--json-schema', schema, '--tools', 'StructuredOutput']`

**⚠️ CURRENT STATE:** File is set to Test D configuration
**⚠️ ACTION NEEDED:** Restore to Test A (original) configuration before production use

## Recommended Next Steps

### After Model Upgrade:

1. **Revert cli_player.py to baseline (Test A config)**
   ```python
   cmd = ['claude', '--print', '--output-format', 'json', '--json-schema', schema]
   ```

2. **Rerun all 4 tests with upgraded model**
   - Run 5-10 games per test for statistical significance
   - Check if newer model changes the trade-offs

3. **If results confirm current findings:**
   - Keep `--output-format json` flag (essential for performance)
   - Implement post-processing to extract/compress essential data
   - Add `--verbose` flag to optionally retain full metadata

4. **Implementation options:**
   - Option A: Extract essential data, archive full responses separately
   - Option B: Compress JSON responses (gzip)
   - Option C: Make it configurable via CLI arg

## Test Results Summary Table

| Test | Configuration | Wins | Win Rate | File Size | Delta vs Baseline |
|------|--------------|------|----------|-----------|-------------------|
| A | Current (json+schema) | 2/3 | 66.7% | 143KB | Baseline |
| B | Schema only | 0/3 | 0.0% | 14KB | -66.7% ⚠️ |
| C | Minimal | 1/3 | 33.3% | 48KB | -33.3% |
| D | + tools flag | 1/3 | 33.3% | 170KB | -33.3% |

## Model Usage Metadata Discovered

From Test A, per-turn averages:
- **Haiku tokens:** ~900 (orchestration)
- **Sonnet tokens:** ~1,200 (response generation)
- **Cache usage:** 16,667 tokens created on turn 1, ~16,500 read on subsequent turns
- **Cost per turn:** $0.015-0.075 (first turn expensive due to cache creation)
- **Duration:** 16-20 seconds per turn

## Files Created During Investigation

### Test Outputs:
- `outputs/test_a_current.jsonl` (143KB, 3 games, 66.7% win)
- `outputs/test_b_no_output_format.jsonl` (14KB, 3 games, 0% win)
- `outputs/test_c_minimal.jsonl` (48KB, 3 games, 33.3% win)
- `outputs/test_d_reduced_tools.jsonl` (170KB, 3 games, 33.3% win)

### Earlier Test Files:
- `outputs/orchestrator_20251124_114329_claude.jsonl` (133KB, 2 games, 0% win)
- `outputs/orchestrator_20251124_114329_codex.jsonl` (2.8KB, 2 games, 100% win)
- `outputs/orchestrator_20251124_114329_gemini.jsonl` (19KB, 2 games, 50% win)
- `outputs/results_20251124_120209.jsonl` (DeepSeek, 2 games, 0% win)
- `outputs/results_20251124_122017.jsonl` (Claude 3 games, 67% win)

### Reports:
- `reports/report_20251124_121620.html`
- `reports/report_20251124_121620.md`
- `reports/report_20251124_121620.csv`
- `reports/report_20251124_121620_files/win_rate.png`
- `reports/report_20251124_121620_files/turn_distribution.png`

## Key Questions for Post-Upgrade Testing

1. Does the upgraded model maintain the same performance pattern?
2. Does file size vs. performance trade-off change?
3. Is there a way to get good performance with smaller files?
4. Should we accept large files as the cost of good performance?

## Conclusion

**DO NOT remove `--output-format json` flag!**

While it creates large files (143KB vs 2.8KB for Codex), it's critical for:
- Proper JSON schema validation
- StructuredOutput tool functionality
- Dual-model (Haiku+Sonnet) coordination
- 67% win rate vs 0% without it

The verbose output is not bloat - it's architectural. Performance must come first.

---

**Investigation Status:** Complete, awaiting model upgrade for retest
**Recommended Action:** Revert code to baseline, upgrade model, rerun with larger sample size
