#!/bin/bash
# Mastermind Test - Claude Opus (DEBUG VERSION)
# Verbose output for debugging - shows prompts, raw responses, parsing details

# ========== CONFIGURATION ==========
MAX_TURNS=12
MAX_RETRIES=3
TIMEOUT_SECONDS=60
JSON_SCHEMA='{"type":"object","properties":{"guess":{"type":"array","items":{"type":"integer"},"minItems":4,"maxItems":4}},"required":["guess"]}'
# ===================================

echo "=== Claude Opus Mastermind Test (DEBUG) ==="
echo ""

# Calculate feedback using Python (accurate)
calc_feedback() {
    python3 -c "
from collections import Counter
s = '$1'.split()
g = '$2'.split()
black = sum(1 for x, y in zip(s, g) if x == y)
common = sum((Counter(s) & Counter(g)).values())
white = common - black
print(f'{black} {white}')
"
}

# Parse Claude response with debug output
parse_claude_response_debug() {
    python3 -c "
import sys, json
raw = sys.stdin.read().strip()
print('--- PARSE DEBUG ---', file=sys.stderr)
print(f'Raw length: {len(raw)} chars', file=sys.stderr)
try:
    data = json.loads(raw)

    # Handle array format (Claude CLI returns array of message objects)
    if isinstance(data, list):
        print(f'Response is array with {len(data)} elements', file=sys.stderr)
        # Look for result object with structured_output
        for item in data:
            if isinstance(item, dict) and item.get('type') == 'result':
                structured = item.get('structured_output', {})
                guess = structured.get('guess', [])
                print(f'Found structured_output.guess: {guess}', file=sys.stderr)
                if isinstance(guess, list) and len(guess) == 4:
                    print(f'Valid guess: {guess}', file=sys.stderr)
                    print(guess)
                    sys.exit(0)
        print('No valid guess in result object', file=sys.stderr)
        print('[]')
    else:
        # Handle direct object format
        print(f'Parsed JSON keys: {list(data.keys())}', file=sys.stderr)
        guess = data.get('guess', [])
        print(f'Guess value: {guess}', file=sys.stderr)
        if isinstance(guess, list) and len(guess) == 4:
            print(f'Valid guess: {guess}', file=sys.stderr)
            print(guess)
        else:
            print(f'Invalid guess format', file=sys.stderr)
            print('[]')
except Exception as e:
    print(f'Parse error: {e}', file=sys.stderr)
    print('[]')
print('--- END PARSE ---', file=sys.stderr)
" 2>&1
}

# Call Claude with retry logic (debug version)
call_claude_debug() {
    local prompt="$1"
    local attempt=1

    while [ $attempt -le $MAX_RETRIES ]; do
        echo ""
        echo "=========================================="
        echo "API Call - Attempt $attempt/$MAX_RETRIES"
        echo "=========================================="

        # Call with timeout
        echo "Calling Claude Opus with ${TIMEOUT_SECONDS}s timeout..."
        response=$(timeout $TIMEOUT_SECONDS claude --print --output-format json --json-schema "$JSON_SCHEMA" --model claude-opus-4-5-20251101 <<< "$prompt" 2>&1)
        exit_code=$?

        echo ""
        echo "--- RAW RESPONSE ---"
        echo "$response"
        echo "--- END RAW RESPONSE ---"
        echo ""
        echo "Exit code: $exit_code"

        # Check for timeout
        if [ $exit_code -eq 124 ]; then
            echo "TIMEOUT after ${TIMEOUT_SECONDS}s"
            ((attempt++))
            continue
        fi

        # Check for empty response
        if [ -z "$response" ]; then
            echo "EMPTY RESPONSE"
            ((attempt++))
            continue
        fi

        # Parse response
        echo ""
        parse_output=$(echo "$response" | parse_claude_response_debug)
        echo "$parse_output"

        # Extract just the guess array (last line that looks like a list)
        guess_json=$(echo "$parse_output" | grep -E '^\[' | tail -1)
        echo ""
        echo "Extracted guess_json: $guess_json"

        # Validate we got 4 integers
        guess_array=($(echo "$guess_json" | tr -d '[],' ))
        echo "Parsed array: [${guess_array[*]}] (${#guess_array[@]} elements)"

        if [ ${#guess_array[@]} -eq 4 ]; then
            echo "SUCCESS - Valid guess obtained"
            echo "$guess_json"
            return 0
        fi

        echo "INVALID - Retrying..."
        ((attempt++))
    done

    echo "FAILED after $MAX_RETRIES attempts"
    echo "[]"
    return 1
}

# Play one game (debug version)
play_game_debug() {
    local secret_str="$1"
    local max_turns="$2"
    local secret=(${secret_str//,/ })

    echo ""
    echo "############################################"
    echo "# GAME START"
    echo "# Secret: [${secret[*]}]"
    if [ "$max_turns" -eq 0 ]; then
        echo "# Max turns: unlimited"
    else
        echo "# Max turns: $max_turns"
    fi
    echo "############################################"
    echo ""

    local history=""
    local turn=1
    local turns_text
    if [ "$max_turns" -eq 0 ]; then
        turns_text="Unlimited turns."
    else
        turns_text="Max $max_turns turns."
    fi

    while [ "$max_turns" -eq 0 ] || [ $turn -le $max_turns ]; do
        echo ""
        echo "============================================"
        echo "TURN $turn"
        echo "============================================"

        # Build prompt
        if [ -z "$history" ]; then
            prompt="You are playing Mastermind.
Secret has 4 positions, colors 0-5. Duplicates allowed. $turns_text

Previous guesses: (none yet)

Make your first guess. Respond ONLY with JSON: {\"guess\": [a,b,c,d]}"
        else
            prompt="You are playing Mastermind.
Secret has 4 positions, colors 0-5. Duplicates allowed. $turns_text

Previous guesses:
$history
Make your next guess. Respond ONLY with JSON: {\"guess\": [a,b,c,d]}"
        fi

        echo ""
        echo "--- PROMPT ---"
        echo "$prompt"
        echo "--- END PROMPT ---"

        # Get guess from Claude (use tee to show output AND capture it)
        guess_result=$(call_claude_debug "$prompt" | tee /dev/stderr)
        guess_json=$(echo "$guess_result" | grep -E '^\[' | tail -1)
        guess_array=($(echo "$guess_json" | tr -d '[],' ))

        if [ ${#guess_array[@]} -ne 4 ]; then
            echo ""
            echo "TURN $turn: FAILED - Could not get valid guess after $MAX_RETRIES attempts"
            echo ""
            return 1
        fi

        # Calculate feedback
        feedback=$(calc_feedback "${secret[*]}" "${guess_array[*]}")
        black=$(echo $feedback | cut -d' ' -f1)
        white=$(echo $feedback | cut -d' ' -f2)

        echo ""
        echo ">>> TURN $turn RESULT: [${guess_array[*]}] -> ${black}B ${white}W <<<"
        echo ""

        # Check for win
        if [ "$black" == "4" ]; then
            echo ""
            echo "############################################"
            echo "# WIN in $turn turns!"
            echo "############################################"
            return 0
        fi

        # Add to history
        history="${history}Guess: [${guess_array[*]}] -> ${black} black, ${white} white
"
        ((turn++))
    done

    echo ""
    echo "############################################"
    echo "# LOSS - Exceeded $max_turns turns"
    echo "############################################"
    return 1
}

# Normalize secret format (accept with or without commas)
normalize_secret() {
    local input="$1"
    if [[ "$input" =~ ^[0-5]{4}$ ]]; then
        echo "${input:0:1},${input:1:1},${input:2:1},${input:3:1}"
    else
        echo "$input"
    fi
}

# Validate secret (accepts 2011 or 2,0,1,1)
validate_secret() {
    local input="$1"
    [[ "$input" =~ ^[0-5]{4}$ ]] || [[ "$input" =~ ^[0-5],[0-5],[0-5],[0-5]$ ]]
}

# Prompt for max turns
prompt_max_turns() {
    local input
    read -p "Max turns (0=unlimited) [12]: " input
    if [ -z "$input" ]; then
        echo "12"
    elif [[ "$input" =~ ^[0-9]+$ ]]; then
        echo "$input"
    else
        echo "12"
    fi
}

# Main loop
while true; do
    read -p "Enter secret (e.g., 2240 or 2,2,4,0): " SECRET

    # Validate secret format
    if ! validate_secret "$SECRET"; then
        echo "Invalid format. Use 4 digits 0-5 (e.g., 2240 or 2,2,4,0)"
        continue
    fi
    SECRET=$(normalize_secret "$SECRET")
    MAX_TURNS=$(prompt_max_turns)

    play_game_debug "$SECRET" "$MAX_TURNS"
    echo ""

    read -p "Enter new secret (or 'q' to quit): " SECRET
    if [ "$SECRET" == "q" ] || [ "$SECRET" == "Q" ]; then
        echo "Goodbye!"
        exit 0
    fi

    # Validate new secret
    while ! validate_secret "$SECRET"; do
        if [ "$SECRET" == "q" ] || [ "$SECRET" == "Q" ]; then
            echo "Goodbye!"
            exit 0
        fi
        echo "Invalid format. Use 4 digits 0-5 (e.g., 2240 or 2,2,4,0)"
        read -p "Enter new secret (or 'q' to quit): " SECRET
    done
    SECRET=$(normalize_secret "$SECRET")
    MAX_TURNS=$(prompt_max_turns)

    play_game_debug "$SECRET" "$MAX_TURNS"
    echo ""
done
