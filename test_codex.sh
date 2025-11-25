#!/bin/bash
# Mastermind Test - Codex (Interactive)
# Tests OpenAI Codex CLI with gpt-5.1-codex-max

# ========== CONFIGURATION ==========
MAX_TURNS=12
MAX_RETRIES=3
TIMEOUT_SECONDS=60
MODEL="gpt-5.1-codex-max"
# ===================================

echo "=== Codex Mastermind Test ==="
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

# Parse Codex JSONL response
parse_codex_response() {
    python3 -c "
import sys, json, re

raw = sys.stdin.read().strip()

# Parse JSONL - look for agent_message items
for line in raw.split('\n'):
    if not line.strip():
        continue
    try:
        obj = json.loads(line)
        if obj.get('type') == 'item.completed':
            item = obj.get('item', {})
            if item.get('type') == 'agent_message':
                text = item.get('text', '')

                # Try direct parse
                try:
                    data = json.loads(text.strip())
                    guess = data.get('guess', [])
                    if isinstance(guess, list) and len(guess) == 4:
                        print(guess)
                        sys.exit(0)
                except:
                    pass

                # Try markdown block
                m = re.search(r'\`\`\`(?:json)?\s*(\{.*?\})\s*\`\`\`', text, re.DOTALL)
                if m:
                    try:
                        data = json.loads(m.group(1))
                        guess = data.get('guess', [])
                        if isinstance(guess, list) and len(guess) == 4:
                            print(guess)
                            sys.exit(0)
                    except:
                        pass

                # Try to find JSON pattern
                m = re.search(r'\{[^{}]*\"guess\"\s*:\s*\[[\d,\s]+\][^{}]*\}', text)
                if m:
                    try:
                        data = json.loads(m.group(0))
                        guess = data.get('guess', [])
                        if isinstance(guess, list) and len(guess) == 4:
                            print(guess)
                            sys.exit(0)
                    except:
                        pass
    except:
        continue

print('[]')
"
}

# Call Codex with retry logic
call_codex() {
    local prompt="$1"
    local attempt=1

    while [ $attempt -le $MAX_RETRIES ]; do
        # Call with timeout and JSONL output (no sandbox for fair comparison)
        response=$(timeout $TIMEOUT_SECONDS codex exec --json -m "$MODEL" "$prompt" 2>/dev/null)
        exit_code=$?

        # Check for timeout
        if [ $exit_code -eq 124 ]; then
            echo "  Attempt $attempt/$MAX_RETRIES: Timeout (${TIMEOUT_SECONDS}s)" >&2
            ((attempt++))
            continue
        fi

        # Check for empty response
        if [ -z "$response" ]; then
            echo "  Attempt $attempt/$MAX_RETRIES: Empty response" >&2
            ((attempt++))
            continue
        fi

        # Parse response
        guess_json=$(echo "$response" | parse_codex_response)

        # Validate we got 4 integers
        guess_array=($(echo "$guess_json" | tr -d '[],' ))
        if [ ${#guess_array[@]} -eq 4 ]; then
            echo "$guess_json"
            return 0
        fi

        echo "  Attempt $attempt/$MAX_RETRIES: Invalid JSON response" >&2
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
            prompt="You are playing Mastermind. Do NOT run any shell commands.
Secret has 4 positions, colors 0-5. Duplicates allowed. $turns_text

Previous guesses: (none yet)

Make your first guess. Respond ONLY with JSON: {\"guess\": [a,b,c,d]}"
        else
            prompt="You are playing Mastermind. Do NOT run any shell commands.
Secret has 4 positions, colors 0-5. Duplicates allowed. $turns_text

Previous guesses:
$history
Make your next guess. Respond ONLY with JSON: {\"guess\": [a,b,c,d]}"
        fi

        # Get guess from Codex
        guess_json=$(call_codex "$prompt")
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
    # If no commas, add them between each digit
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
