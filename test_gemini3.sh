#!/bin/bash
# Mastermind Test - Gemini 3 Pro (Interactive)
# Tests Gemini 3 Pro Preview with JSON output mode

# ========== CONFIGURATION ==========
MAX_TURNS=12
MAX_RETRIES=3
TIMEOUT_SECONDS=60
MODEL="gemini-3-pro-preview"
# ===================================

echo "=== Gemini Mastermind Test ==="
echo "Model: $MODEL"
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

# Parse Gemini response (complex - handle YOLO prefix + nested JSON)
parse_gemini_response() {
    python3 -c "
import sys, json, re

raw = sys.stdin.read()

# Find the JSON object (starts with {) - skip any YOLO prefix text
json_start = raw.find('{')
if json_start == -1:
    print('[]')
    sys.exit(0)

json_text = raw[json_start:]

try:
    data = json.loads(json_text)
    resp = data.get('response', '')

    # Try markdown block first
    m = re.search(r'\`\`\`(?:json)?\s*(\{.*?\})\s*\`\`\`', resp, re.DOTALL)
    if m:
        parsed = json.loads(m.group(1))
        guess = parsed.get('guess', [])
        if isinstance(guess, list) and len(guess) == 4:
            print(guess)
        else:
            print('[]')
    else:
        # Try direct JSON parse
        parsed = json.loads(resp.strip())
        guess = parsed.get('guess', [])
        if isinstance(guess, list) and len(guess) == 4:
            print(guess)
        else:
            print('[]')
except:
    print('[]')
"
}

# Call Gemini with retry logic
call_gemini() {
    local prompt="$1"
    local attempt=1

    while [ $attempt -le $MAX_RETRIES ]; do
        # Call with timeout (no -s sandbox flag)
        response=$(timeout $TIMEOUT_SECONDS gemini -o json -y -m "$MODEL" "$prompt" 2>/dev/null)
        exit_code=$?

        # Check for timeout
        if [ $exit_code -eq 124 ]; then
            echo "  Attempt $attempt/$MAX_RETRIES: Timeout (${TIMEOUT_SECONDS}s) - retrying..." >&2
            sleep 3
            ((attempt++))
            continue
        fi

        # Check for empty response
        if [ -z "$response" ]; then
            echo "  Attempt $attempt/$MAX_RETRIES: Empty response - retrying..." >&2
            sleep 3
            ((attempt++))
            continue
        fi

        # Check for tool usage (model tried to use file tools instead of answering)
        tool_calls=$(echo "$response" | grep -oP '"totalCalls":\s*\K\d+' | head -1)
        if [ -n "$tool_calls" ] && [ "$tool_calls" -gt 0 ]; then
            echo "  Attempt $attempt/$MAX_RETRIES: Model used tools instead of answering - retrying..." >&2
            sleep 3
            ((attempt++))
            continue
        fi

        # Also check for tool names in response text (backup check)
        if echo "$response" | grep -qE "(read_file|search_file|replace|list_directory)"; then
            echo "  Attempt $attempt/$MAX_RETRIES: Model attempted file operations - retrying..." >&2
            sleep 3
            ((attempt++))
            continue
        fi

        # Parse response
        guess_json=$(echo "$response" | parse_gemini_response)

        # Validate we got 4 integers
        guess_array=($(echo "$guess_json" | tr -d '[],' ))
        if [ ${#guess_array[@]} -eq 4 ]; then
            echo "$guess_json"
            return 0
        fi

        echo "  Attempt $attempt/$MAX_RETRIES: Invalid JSON response - retrying..." >&2
        sleep 3
        ((attempt++))
    done

    echo "[]"
    return 1
}

# Play one game
play_game() {
    local secret_str="$1"
    local max_turns="$2"
    local secret=(${secret_str//,/ })

    echo "Secret: [${secret[*]}]"
    if [ "$max_turns" -eq 0 ]; then
        echo "Max turns: unlimited"
    else
        echo "Max turns: $max_turns"
    fi
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

        # Get guess from Gemini
        guess_json=$(call_gemini "$prompt")
        guess_array=($(echo "$guess_json" | tr -d '[],' ))

        if [ ${#guess_array[@]} -ne 4 ]; then
            echo "Turn $turn: FAILED - Could not get valid guess after $MAX_RETRIES attempts"
            return 1
        fi

        # Calculate feedback
        feedback=$(calc_feedback "${secret[*]}" "${guess_array[*]}")
        black=$(echo $feedback | cut -d' ' -f1)
        white=$(echo $feedback | cut -d' ' -f2)

        echo "Turn $turn: [${guess_array[*]}] -> ${black}B ${white}W"

        # Check for win
        if [ "$black" == "4" ]; then
            echo ""
            echo "WIN in $turn turns!"
            return 0
        fi

        # Add to history
        history="${history}Guess: [${guess_array[*]}] -> ${black} black, ${white} white
"
        ((turn++))
    done

    echo ""
    echo "LOSS - Exceeded $max_turns turns"
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

    echo ""
    play_game "$SECRET" "$MAX_TURNS"
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

    echo ""
    play_game "$SECRET" "$MAX_TURNS"
    echo ""
done
