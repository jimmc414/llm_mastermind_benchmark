# Claude Code CLI Command Line Reference

A comprehensive reference for Claude Code command-line switches, their usage, constraints, and benefits.

**Last Updated**: November 24, 2025 | **CLI Version**: 2.0.x+

---

## Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `claude` | Start interactive REPL | `claude` |
| `claude "query"` | Start REPL with initial prompt | `claude "explain this project"` |
| `claude -p "query"` | Non-interactive print mode, then exit | `claude -p "summarize README.md"` |
| `cat file \| claude -p "query"` | Process piped content | `cat logs.txt \| claude -p "explain"` |
| `claude -c` | Continue most recent conversation | `claude -c` |
| `claude -r <session-id>` | Resume specific session by ID | `claude -r "abc123" "finish this"` |
| `claude update` | Update to latest version | `claude update` |
| `claude doctor` | Diagnose installation issues | `claude doctor` |
| `claude mcp` | Configure MCP servers | `claude mcp list` |
| `claude config` | Manage configuration | `claude config list` |
| `claude plugin` | Manage Claude Code plugins | `claude plugin list` |
| `claude install [target]` | Install native build (stable, latest, or version) | `claude install stable` |
| `claude setup-token` | Set up long-lived auth token (requires subscription) | `claude setup-token` |
| `claude migrate-installer` | Migrate from global npm to local installation | `claude migrate-installer` |

---

## CLI Flags - Complete Reference

### Session Management

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-c`, `--continue` | Continue the most recent conversation in current directory | `claude --continue` | Loads full conversation history |
| `-r`, `--resume [sessionId]` | Resume a conversation by ID or interactively select one | `claude --resume abc123` | Without ID, shows interactive picker |
| `--fork-session` | Create new session ID when resuming (don't reuse original) | `claude --resume abc123 --fork-session` | Use with `--resume` or `--continue` |
| `--session-id <uuid>` | Use a specific session ID (must be valid UUID) | `claude --session-id 123e4567-...` | Must be valid UUID format |
| `--setting-sources <sources>` | Control which settings to load | `claude --setting-sources "user,project"` | Comma-separated: `user`, `project`, `local` |

**Benefits**: 
- Session management preserves context across work sessions
- `--fork-session` allows branching conversations without modifying the original
- `--setting-sources` enables consistent behavior in CI (e.g., only load `project` settings)

---

### Model Selection

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--model <model>` | Set model for current session | `claude --model sonnet` | Accepts aliases (`sonnet`, `opus`) or full names |
| `--fallback-model <model>` | Fallback when default is overloaded | `claude -p --fallback-model claude-haiku-...` | Only works with `--print` |

**Model Aliases**:
- `sonnet` → Latest Sonnet model (e.g., `claude-sonnet-4-5-20250929`)
- `opus` → Latest Opus model
- Full model strings also accepted: `claude-sonnet-4-5-20250929`, `claude-opus-4-20250514`

**Benefits**: Allows cost/capability optimization per task. Use Opus for complex reasoning, Sonnet for routine tasks.

---

### Output Formatting

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-p`, `--print` | Print response and exit (non-interactive) | `claude -p "query"` | Skips workspace trust dialog |
| `--output-format <format>` | Output format: `text`, `json`, `stream-json` | `claude -p --output-format json` | Only works with `--print` |
| `--input-format <format>` | Input format: `text`, `stream-json` | `claude -p --input-format stream-json` | Only works with `--print` |
| `--include-partial-messages` | Include partial message chunks as they arrive | `claude -p --include-partial-messages` | Only with `--print` and `--output-format=stream-json` |
| `--replay-user-messages` | Re-emit user messages from stdin to stdout | `claude --input-format stream-json --replay-user-messages` | Only with `stream-json` input/output |
| `--json` | **DEPRECATED** - Use `--output-format json` | - | Legacy flag |

**Output Format Details**:

| Format | Description | Structure |
|--------|-------------|-----------|
| `text` | Human-readable plain text | Plain response text |
| `json` | Full session transcript as JSON array | Array of messages with metadata |
| `stream-json` | Real-time streaming JSONL | Separate JSON objects per line |

**JSON Output Schema** (`--output-format json`):

The output is a **JSON array of messages** (not a simple object). Each message follows this schema:

```typescript
type SDKMessage = 
  // Initial system message
  | { type: "init"; session_id: string; /* ...config data... */ }
  
  // Assistant message
  | { type: "assistant"; message: Message; session_id: string; }
  
  // User message  
  | { type: "user"; message: MessageParam; session_id: string; }
  
  // Final result message (always last)
  | { 
      type: "result"; 
      subtype: "success" | "error_max_turns" | "error_during_execution";
      duration_ms: number;
      duration_api_ms: number; 
      is_error: boolean;
      num_turns: number;
      result: string;          // Final text response
      session_id: string;
      total_cost_usd: number;
    }
```

**Parsing JSON Output with jq**:
```bash
# Get the final result text
claude -p "query" --output-format json | jq -r '.[-1].result'

# Get the total cost
claude -p "query" --output-format json | jq '.[-1].total_cost_usd'

# Get the session ID for resuming
claude -p "query" --output-format json | jq -r '.[-1].session_id'

# Extract all assistant messages
claude -p "query" --output-format json | jq '[.[] | select(.type == "assistant")]'
```

**Stream-JSON Output** (`--output-format stream-json`):

Each line is a separate JSON object (JSONL format):
1. First: `init` message with session info
2. Middle: `user` and `assistant` messages as they occur
3. Last: `result` message with final stats

```bash
# Process stream-json in real-time
claude -p "query" --output-format stream-json | while read -r line; do
  type=$(echo "$line" | jq -r '.type')
  case "$type" in
    "assistant") echo "$line" | jq -r '.message.content[0].text' ;;
    "result") echo "Done! Cost: $(echo "$line" | jq '.total_cost_usd')" ;;
  esac
done
```

### Structured Output with JSON Schema (v2.0+)

| Flag | Description | Example |
|------|-------------|---------|
| `--json-schema <schema>` | Enforce JSON schema compliance on Claude's response | `--json-schema '{"type":"object","properties":{"name":{"type":"string"}}}'` |

**How it works**: Uses constrained decoding to guarantee Claude's response matches your schema. The schema is compiled into a grammar that restricts token generation.

```bash
# Inline schema
claude -p "List 3 countries with capitals" \
  --output-format json \
  --json-schema '{"type":"array","items":{"type":"object","properties":{"country":{"type":"string"},"capital":{"type":"string"}},"required":["country","capital"]}}'

# Schema from file (using shell substitution)
claude -p "Extract contact info" \
  --output-format json \
  --json-schema "$(cat contact.schema.json)"
```

**Schema Limitations** (same as Anthropic API):
- No recursive schemas
- Use `additionalProperties: false` for strict validation
- Numerical constraints (min/max) require post-validation
- First request with a new schema has compilation latency (cached 24h after)

**Extracting structured data**:
```bash
# The structured data is in the result field of the last message
claude -p "Extract person info from: John Smith, age 30, engineer" \
  --output-format json \
  --json-schema '{"type":"object","properties":{"name":{"type":"string"},"age":{"type":"integer"},"job":{"type":"string"}},"required":["name","age","job"]}' \
  | jq -r '.[-1].result'
# Output: {"name":"John Smith","age":30,"job":"engineer"}
```

**Benefits**: 
- `json` enables CI/CD integration with full conversation logs
- `stream-json` enables real-time progress monitoring for long tasks
- Session ID in output allows programmatic session resumption

---

### Permission Control

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--allowedTools <tools...>` | Tools allowed without prompting | `--allowedTools "Bash(git:*)" "Read"` | Space or comma-separated |
| `--disallowedTools <tools...>` | Tools explicitly disallowed | `--disallowedTools "Bash(rm:*)"` | Takes precedence over allowed |
| `--tools <tools...>` | Specify available tools from built-in set | `--tools "Bash,Edit,Read"` | Use `""` for none, `"default"` for all. Only with `--print` |
| `--permission-mode <mode>` | Set permission mode for session | `claude --permission-mode plan` | See modes below |
| `--permission-prompt-tool <tool>` | MCP tool to handle permission prompts | `claude -p --permission-prompt-tool mcp_auth` | For non-interactive automation |
| `--dangerously-skip-permissions` | Bypass ALL permission checks | `claude --dangerously-skip-permissions` | **DANGER**: Only in isolated containers |
| `--allow-dangerously-skip-permissions` | Enable bypass as an *option* without default | `claude --allow-dangerously-skip-permissions` | Safer than always-on bypass |

**Permission Modes**:
| Mode | Description |
|------|-------------|
| `default` | Prompts for all tool usage |
| `acceptEdits` | Auto-accept file edits, prompt for others |
| `plan` | Read-only mode, no edits |
| `dontAsk` | Don't ask for permissions (similar to acceptEdits) |
| `bypassPermissions` | Skip all prompts (dangerous) |

**Tool Permission Patterns**:
```bash
# Allow all git commands
--allowedTools "Bash(git:*)"

# Allow specific npm commands
--allowedTools "Bash(npm run test:*)"

# Allow read operations
--allowedTools "Read" "Grep" "Glob"

# Block destructive operations
--disallowedTools "Bash(rm:*)" "Bash(sudo:*)"
```

**Security Warning**: `--dangerously-skip-permissions` is intended **only** for Docker containers without internet access. Risks include:
- Arbitrary file deletion/modification
- System corruption
- Data exfiltration via prompt injection

---

### System Prompt Customization

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--system-prompt <prompt>` | Complete control over system prompt | `claude --system-prompt "You are..."` | **Removes** all default instructions |
| `--system-prompt-file <file>` | Load system prompt from file | `claude --system-prompt-file ./prompt.txt` | Mutually exclusive with `--system-prompt` |
| `--append-system-prompt <prompt>` | Add to default system prompt | `claude -p --append-system-prompt "Always use TypeScript"` | **Recommended** - preserves defaults |

**Recommendations**:
- Use `--append-system-prompt` for most cases (preserves built-in capabilities)
- Use `--system-prompt` only when you need complete control
- `--system-prompt` and `--system-prompt-file` cannot be used together

---

### Subagents

| Flag | Description | Example |
|------|-------------|---------|
| `--agents <json>` | Define custom subagents inline | See example below |

**Subagent JSON Structure**:
```bash
claude --agents '{
  "code-reviewer": {
    "description": "Expert code reviewer. Use proactively after code changes.",
    "prompt": "You are a senior code reviewer. Focus on quality and security.",
    "tools": ["Read", "Grep", "Glob", "Bash"],
    "model": "sonnet"
  },
  "debugger": {
    "description": "Debugging specialist for errors and test failures.",
    "prompt": "You are an expert debugger. Analyze errors and provide fixes."
  }
}'
```

**Subagent Fields**:
- `description`: When to invoke (include "proactively" for auto-invocation)
- `prompt`: System prompt for the subagent
- `tools`: Array of allowed tools (inherits all if omitted)
- `model`: Model to use (`sonnet`, `opus`, or `inherit`)

---

### Directory and Context Control

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--add-dir <directories...>` | Add additional working directories | `claude --add-dir ../frontend ../backend` | Validates paths exist |
| `--max-turns <n>` | Limit conversation turns | `claude -p --max-turns 5 "query"` | Controls costs in automation |

**Benefits**:
- `--add-dir` scopes context to relevant paths, reducing noise
- `--max-turns` prevents runaway costs in automated workflows

---

### MCP (Model Context Protocol)

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--mcp-config <configs...>` | Load MCP servers from JSON files | `claude --mcp-config ./mcp-servers.json` | Space-separated |
| `--strict-mcp-config` | Only use MCP servers from `--mcp-config` | `claude --mcp-config ./a.json --strict-mcp-config` | Ignores other MCP configs |
| `--mcp-debug` | **DEPRECATED** - Enable MCP debug output | `claude --mcp-debug` | Use `--debug` instead |

---

### Plugins (v2.0+)

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--plugin-dir <paths...>` | Load plugins from directories (session only) | `claude --plugin-dir ./my-plugins` | Repeatable for multiple dirs |

**Plugin Commands**:
```bash
claude plugin list              # List installed plugins
claude plugin install <name>    # Install a plugin
claude plugin remove <name>     # Remove a plugin
```

---

### Debugging and Logging

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-d`, `--debug [filter]` | Enable debug mode with optional filtering | `claude --debug "api,hooks"` | Filter: `"api,hooks"` or `"!statsig,!file"` |
| `--verbose` | Override verbose mode from config | `claude --verbose` | Shows expanded logging |

**Debug Filter Examples**:
- `--debug "api,hooks"` - Only show api and hooks debug output
- `--debug "!statsig,!file"` - Show all except statsig and file

---

### IDE Integration

| Flag | Description | Example |
|------|-------------|---------|
| `--ide` | Auto-connect to IDE on startup | `claude --ide` |

---

### Settings and Configuration

| Flag | Description | Example |
|------|-------------|---------|
| `--settings <file-or-json>` | Load additional settings from JSON | `claude --settings ./settings.json` |

---

### Utility Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-v`, `--version` | Show installed CLI version | `claude --version` |
| `-h`, `--help` | Display help | `claude --help` |

---

## Environment Variables

### API Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | API key for authentication | `sk-your-key-here` |
| `ANTHROPIC_AUTH_TOKEN` | Custom Authorization header | Adds "Bearer " prefix |
| `ANTHROPIC_MODEL` | Default model override | `claude-sonnet-4-20250514` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | Default for `sonnet` alias | `claude-sonnet-4-20250514` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | Default for `opus` alias | `claude-opus-4-20250514` |

### Provider Configuration

| Variable | Description |
|----------|-------------|
| `CLAUDE_CODE_USE_BEDROCK=1` | Use Amazon Bedrock |
| `CLAUDE_CODE_USE_VERTEX=1` | Use Google Vertex AI |
| `CLAUDE_CODE_SKIP_BEDROCK_AUTH=1` | Skip AWS auth (for LLM gateway) |
| `CLAUDE_CODE_SKIP_VERTEX_AUTH=1` | Skip Google auth (for LLM gateway) |

### Behavior Control

| Variable | Description | Default |
|----------|-------------|---------|
| `BASH_DEFAULT_TIMEOUT_MS` | Default bash command timeout | `60000` |
| `BASH_MAX_TIMEOUT_MS` | Maximum bash timeout | `300000` |
| `BASH_MAX_OUTPUT_LENGTH` | Max chars before truncation | `20000` |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | Max output tokens | `4096` |
| `MAX_THINKING_TOKENS` | Force thinking budget | `0` (disabled) |
| `MCP_TIMEOUT` | MCP server startup timeout | `120000` |
| `MCP_TOOL_TIMEOUT` | MCP tool execution timeout | `60000` |
| `MAX_MCP_OUTPUT_TOKENS` | Max tokens in MCP responses | `25000` |

### Feature Toggles

| Variable | Description |
|----------|-------------|
| `DISABLE_AUTOUPDATER=1` | Disable automatic updates |
| `DISABLE_TELEMETRY=1` | Opt out of telemetry |
| `DISABLE_ERROR_REPORTING=1` | Opt out of Sentry |
| `DISABLE_BUG_COMMAND=1` | Disable `/bug` command |
| `DISABLE_COST_WARNINGS=1` | Hide cost warnings |
| `DISABLE_NON_ESSENTIAL_MODEL_CALLS=1` | Skip non-critical model calls |
| `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1` | Disable all non-essential traffic |
| `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1` | Stop auto-updating terminal title |
| `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` | Return to project dir after Bash |
| `CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL=1` | Skip auto-install of IDE extensions |
| `USE_BUILTIN_RIPGREP=0` | Use system `rg` instead of bundled |

### Proxy Configuration

| Variable | Description |
|----------|-------------|
| `HTTP_PROXY` | HTTP proxy URL |
| `HTTPS_PROXY` | HTTPS proxy URL |

---

## Common Usage Patterns

### CI/CD Integration

```bash
# Automated code review with JSON output
claude -p "Review this PR for issues" --output-format json > review.json
result=$(cat review.json | jq -r '.[-1].result')
cost=$(cat review.json | jq '.[-1].total_cost_usd')

# Lint fixing with bounded turns
claude -p "Fix all lint errors" --max-turns 10 --allowedTools "Edit" "Bash(npm run lint:*)"

# Headless mode for GitHub Actions
claude -p "Label this issue" \
  --output-format stream-json \
  --allowedTools "Bash(gh:*)"

# Session resumption in pipelines
session_id=$(claude -p "Start review" --output-format json | jq -r '.[-1].session_id')
claude --resume "$session_id" -p "Check compliance"
claude --resume "$session_id" -p "Generate summary"
```

### Safe Automation

```bash
# Scoped permissions for git operations
claude --allowedTools "Bash(git add:*)" "Bash(git commit:*)" "Bash(git status:*)"

# Read-only analysis (Plan Mode)
claude --permission-mode plan "Analyze this codebase architecture"

# Block dangerous operations
claude --disallowedTools "Bash(rm:*)" "Bash(sudo:*)" "Bash(chmod:*)"

# Auto-accept edits mode
claude --permission-mode acceptEdits "Refactor this module"
```

### Context Management

```bash
# Multi-directory project
claude --add-dir ../frontend ../backend ../shared "Explain the data flow"

# Resume previous work
claude --continue "Now add the unit tests we discussed"

# Specific session
claude --resume abc123-def456-... "Continue implementing the feature"
```

### Extended Thinking

Trigger deeper analysis with keywords in your prompt:
- `"Think."` - Small planning boost
- `"Think harder."` - Medium depth  
- `"Ultrathink."` - Maximum analysis depth

```bash
claude -p "Ultrathink. Design a migration plan from REST to gRPC."
```

### Automated Agents

```bash
# SRE incident investigation agent
claude -p "Incident: Payment API returning 500 errors (Severity: high)" \
  --append-system-prompt "You are an SRE expert. Diagnose the issue and provide immediate action items." \
  --output-format json \
  --allowedTools "Bash,Read,WebSearch,mcp__datadog" \
  --mcp-config monitoring-tools.json

# Security audit agent for PRs
gh pr diff 123 | claude -p \
  --append-system-prompt "You are a security engineer. Review for vulnerabilities." \
  --output-format json \
  --allowedTools "Read,Grep" > audit.json
```

---

## Hooks

Hooks execute shell commands at various lifecycle points. Configure in `.claude/settings.json`:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write(*.py)",
        "hooks": [
          { "type": "command", "command": "python -m black $CLAUDE_FILE_PATHS" }
        ]
      }
    ]
  }
}
```

**Hook Events**:
- `PreToolUse` - Before tool execution
- `PostToolUse` - After tool completion  
- `Notification` - When Claude sends notifications
- `Stop` - When Claude finishes responding

**Environment Variables in Hooks**:
- `$CLAUDE_FILE_PATHS` - Files affected by the operation
- `$CLAUDE_PROJECT_DIR` - Project root directory

**Exit Codes**:
- `0` - Success
- `2` - Block operation and show message to Claude
- Other - Error

---

## Configuration Files

### Hierarchy (highest to lowest priority)

1. **Enterprise policy**: `/etc/claude-code/CLAUDE.md` (Linux), `/Library/Application Support/ClaudeCode/CLAUDE.md` (macOS)
2. **CLI arguments**: Flags passed at runtime
3. **Project local**: `.claude/settings.local.json`
4. **Project shared**: `.claude/settings.json`
5. **User global**: `~/.claude/settings.json`

### Example settings.json

```json
{
  "model": "claude-sonnet-4-20250514",
  "permissions": {
    "allow": ["Read", "Grep", "Glob", "Bash(git:*)"],
    "deny": ["Bash(rm:*)", "Read(./.env)"]
  },
  "verbose": true,
  "autoUpdates": true,
  "theme": "dark"
}
```

---

## Tool Reference

| Tool | Description | Permission Required |
|------|-------------|---------------------|
| `Read` / `FileReadTool` | Read file contents | No |
| `Write` / `FileWriteTool` | Create/overwrite files | Yes |
| `Edit` / `FileEditTool` | Targeted file edits | Yes |
| `MultiEdit` | Multiple edits in one operation | Yes |
| `Bash` / `BashTool` | Execute shell commands | Yes |
| `Grep` / `GrepTool` | Search patterns in files | No |
| `Glob` / `GlobTool` | Find files by pattern | No |
| `LS` / `LSTool` | List files/directories | No |
| `AgentTool` | Run sub-agents for complex tasks | No |
| `NotebookReadTool` | Read Jupyter notebooks | No |
| `NotebookEditTool` | Modify Jupyter notebooks | Yes |
| `WebFetch` | Fetch web content | Yes |
| `WebSearch` | Search the web | Yes |

**MCP Tools**: Follow pattern `mcp__<server>__<tool>` (e.g., `mcp__github__search_repositories`)

---

## Best Practices

### Security
- Never use `--dangerously-skip-permissions` outside isolated containers
- Use explicit `--allowedTools` lists rather than blanket permissions
- Block destructive operations with `--disallowedTools`
- Store secrets in environment variables, not commands

### Performance
- Use `--add-dir` to scope context to relevant directories
- Set `--max-turns` for bounded automation tasks
- Use `--output-format json` for efficient parsing in pipelines

### Debugging
- Use `--verbose` for turn-by-turn output
- Use `--debug` with filters for targeted troubleshooting
- Run `claude doctor` for installation diagnostics

### Automation
- Always use `--print` mode for scripts and CI/CD
- Combine `--output-format stream-json` for real-time progress
- Use `--fallback-model` for resilience against overload

---

## SDK Usage

Claude Code includes TypeScript and Python SDKs for building custom agents.

### TypeScript SDK

```bash
npm install @anthropic-ai/claude-code
```

```typescript
import { query, ClaudeAgentOptions } from '@anthropic-ai/claude-code';

const options: ClaudeAgentOptions = {
  systemPrompt: "You are an expert code reviewer",
  permissionMode: 'acceptEdits',
  cwd: "/home/user/project"
};

for await (const message of query({
  prompt: "Review this codebase for security issues",
  options
})) {
  if (message.type === 'assistant') {
    console.log(message.message.content);
  } else if (message.type === 'result') {
    console.log(`Done! Cost: $${message.total_cost_usd}`);
  }
}
```

### Python SDK

```bash
pip install claude-code-sdk
```

```python
import asyncio
from claude_code_sdk import query, ClaudeAgentOptions

async def main():
    options = ClaudeAgentOptions(
        system_prompt="You are an expert Python developer",
        permission_mode='acceptEdits',
        cwd="/home/user/project"
    )
    
    async for message in query(
        prompt="Create a Python web server",
        options=options
    ):
        if message.type == 'result':
            print(f"Cost: ${message.total_cost_usd}")

asyncio.run(main())
```

### SDK vs CLI

| Feature | CLI | SDK |
|---------|-----|-----|
| Interactive sessions | ✓ | ✗ |
| Programmatic control | Limited | Full |
| Custom agents | Via `--agents` | Native |
| Error handling | Exit codes | Exceptions |
| Streaming | `stream-json` | Native async |

---

## Slash Commands

Create custom commands in `.claude/commands/` or `~/.claude/commands/`:

```markdown
<!-- .claude/commands/review.md -->
---
allowed-tools: Read, Grep
description: Review code for best practices
---

Review the following code for:
1. Security vulnerabilities
2. Performance issues
3. Code style violations

$ARGUMENTS
```

Use with `/review <file.py>` in interactive mode or:

```bash
# Run custom commands in headless mode
claude -p "/review src/main.py"
```

**Special Variables**:
- `$ARGUMENTS` - Arguments passed to the command
- `@{path}` - Embed file/directory contents
