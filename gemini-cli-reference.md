# Gemini CLI Command Line Reference

A comprehensive reference for Gemini CLI command-line switches, their usage, constraints, and benefits.

**Last Updated**: November 24, 2025 | **CLI Version**: v0.17.1

---

## Overview

Gemini CLI is Google's open-source AI agent that brings Gemini directly into your terminal. It uses a reason-and-act (ReAct) loop with built-in tools and MCP servers to complete complex tasks like bug fixing, feature creation, and code analysis.

**Key Features**:
- **Gemini 3 Pro** (Preview) with state-of-the-art reasoning and 1M token context window
- Gemini 2.5 Pro/Flash fallback with automatic model routing
- Built-in tools: Google Search grounding, file operations, shell commands, web fetching
- MCP (Model Context Protocol) support for custom integrations
- Extensions system for custom functionality
- Sandboxing for safe execution
- Session management with resume/list/delete

---

## Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `gemini` | Start interactive REPL | `gemini` |
| `gemini "query"` | Execute one-shot query and exit | `gemini "explain this project"` |
| `gemini -i "query"` | Start interactive session with initial prompt | `gemini -i "let's debug this issue"` |
| `cat file \| gemini "query"` | Process piped content | `cat logs.txt \| gemini "analyze errors"` |
| `gemini mcp` | Manage MCP servers | `gemini mcp list` |
| `gemini extensions` | Manage extensions | `gemini extensions list` |

---

## CLI Flags - Complete Reference

### Prompt and Interaction Modes

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| (positional) `"query"` | Prompt as positional argument | `gemini "what does this do"` | Defaults to one-shot mode |
| `-p`, `--prompt <prompt>` | Non-interactive mode with prompt | `gemini -p "explain this code"` | **DEPRECATED**: Use positional prompt |
| `-i`, `--prompt-interactive <prompt>` | Interactive session with initial prompt | `gemini -i "help me debug"` | Continues in interactive mode after prompt |

**Behavior**:
- **Positional prompt only**: One-shot (executes and exits)
- **With `-i`**: Interactive (continues after executing prompt)
- **No prompt**: Starts interactive REPL
- **With stdin**: Appends prompt to stdin content

**Examples**:
```bash
# One-shot execution
gemini "summarize this codebase"

# Interactive with initial prompt
gemini -i "let's refactor the auth module"

# Process piped content
cat error.log | gemini "explain these errors"
```

---

### Session Management

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-r`, `--resume <session>` | Resume a previous session | `gemini --resume latest` | Use "latest" or index number |
| `--list-sessions` | List all sessions for current project and exit | `gemini --list-sessions` | Shows index, timestamp, first prompt |
| `--delete-session <index>` | Delete a session by index number | `gemini --delete-session 3` | Use `--list-sessions` to see indices |

**Session Storage**:
- Sessions are stored per-project (based on working directory)
- Each session includes full conversation history and context
- Sessions persist across Gemini CLI restarts

**Examples**:
```bash
# List available sessions
gemini --list-sessions

# Resume most recent session
gemini --resume latest

# Resume session #5
gemini --resume 5

# Delete session #3
gemini --delete-session 3
```

---

### Model Selection

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-m`, `--model <model>` | Specify the model to use | `gemini -m gemini-3-pro-preview` | Overrides default model routing |

**Available Models** (as of v0.17.1):
- `gemini-3-pro-preview` (Preview access required)
- `gemini-3-pro-preview-11-2025` (Versioned identifier)
- `gemini-2.5-pro`
- `gemini-2.5-flash`
- `gemini-2.0-flash-exp`

**Model Routing Modes** (configured via `/model` command in interactive mode):
| Mode | Behavior |
|------|----------|
| **Auto** (default) | Simple prompts → Flash; Complex prompts → Pro (or Gemini 3 if enabled) |
| **Pro** | Always uses most capable model |
| **Flash** | Always uses fastest model |

---

### Approval and Permission Control

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-y`, `--yolo` | Auto-approve ALL tools (YOLO mode) | `gemini -y "fix all bugs"` | **DANGER**: No approval prompts |
| `--approval-mode <mode>` | Set approval mode for session | `gemini --approval-mode auto_edit` | `default`, `auto_edit`, `yolo` |
| `--allowed-tools <tools...>` | Tools allowed without confirmation | `gemini --allowed-tools edit write` | Space-separated list |
| `--allowed-mcp-server-names <servers...>` | MCP servers allowed without confirmation | `gemini --allowed-mcp-server-names github slack` | Space-separated list |

**Approval Modes**:
| Mode | Description |
|------|-------------|
| `default` | Prompt for approval on all tool usage |
| `auto_edit` | Auto-approve edit tools, prompt for others |
| `yolo` | Auto-approve ALL tools (same as `-y` flag) |

**Tool Permission Examples**:
```bash
# Auto-approve file edits only
gemini --approval-mode auto_edit "refactor this module"

# Full YOLO mode (dangerous!)
gemini -y "deploy to production"

# Allow specific tools without prompts
gemini --allowed-tools edit write search "implement feature X"

# Allow specific MCP servers
gemini --allowed-mcp-server-names github gitlab "create PR"
```

**Security Warning**: YOLO mode (`-y` or `--approval-mode yolo`) disables all safety prompts. Use only in controlled environments or for trusted tasks.

---

### Output Formatting

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-o`, `--output-format <format>` | Set CLI output format | `gemini -o json "query"` | `text`, `json`, `stream-json` |

**Output Formats**:

| Format | Description | Structure | Use Case |
|--------|-------------|-----------|----------|
| `text` | Human-readable plain text | Plain text output | Interactive use, human reading |
| `json` | Full session as structured JSON | JSON object with messages and metadata | CI/CD pipelines, automation |
| `stream-json` | Real-time streaming JSONL | One JSON object per line | Real-time processing, progress monitoring |

**JSON Output Schema** (`-o json`):
```typescript
{
  messages: Array<{
    role: "user" | "model" | "system";
    content: string;
    timestamp?: string;
  }>;
  metadata: {
    model: string;
    session_id?: string;
    usage?: {
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
    };
  };
  result: string;  // Final response text
}
```

**Stream-JSON Output** (`-o stream-json`):
Each line is a separate JSON object (JSONL format):
```bash
# Process stream-json in real-time
gemini -o stream-json "analyze codebase" | while IFS= read -r line; do
  echo "$line" | jq -r '.content // .result // empty'
done
```

**Examples**:
```bash
# JSON output for automation
gemini -o json "list all TODOs" | jq -r '.result'

# Streaming JSON for real-time processing
gemini -o stream-json "long analysis task" | jq -r '.content'

# Default text output
gemini "explain this function"
```

---

### Extensions

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-e`, `--extensions <extensions...>` | Specify extensions to use | `gemini -e prettier eslint "lint this code"` | If not provided, all enabled extensions used |
| `-l`, `--list-extensions` | List all available extensions and exit | `gemini --list-extensions` | Shows installed and available extensions |

**Extension Management Commands**:
```bash
gemini extensions list              # List all extensions
gemini extensions install <name>    # Install an extension
gemini extensions uninstall <name>  # Uninstall an extension
gemini extensions enable <name>     # Enable an extension
gemini extensions disable <name>    # Disable an extension
gemini extensions update [name]     # Update extension(s)
```

**Examples**:
```bash
# Use specific extensions
gemini -e prettier typescript "format and check types"

# List available extensions
gemini --list-extensions

# Install and enable extensions
gemini extensions install prettier
gemini extensions enable prettier

# Use all enabled extensions (default)
gemini "help with my code"
```

---

### Sandbox Mode

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-s`, `--sandbox` | Run in sandboxed environment | `gemini -s "test this untrusted code"` | Isolates execution, limits file system access |

**What Sandbox Mode Does**:
- Restricts file system access to safe directories
- Limits shell command execution
- Prevents network access to sensitive endpoints
- Provides isolated execution environment

**Use Cases**:
- Testing untrusted code
- Safe experimentation
- Running potentially destructive operations
- CI/CD environments

```bash
# Run in sandbox for safety
gemini -s "execute this script I found online"

# Combine with YOLO for automated safe testing
gemini -s -y "test all unit tests"
```

---

### Experimental Features

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--experimental-acp` | Start agent in ACP mode | `gemini --experimental-acp` | Advanced conversation protocol (experimental) |

**ACP (Advanced Conversation Protocol)** is an experimental feature that enables:
- More sophisticated multi-turn reasoning
- Enhanced context management
- Improved long-running task handling

**Note**: Experimental features may change or be removed in future versions.

---

### Context Control

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--include-directories <dirs...>` | Additional directories in workspace | `gemini --include-directories ../frontend ../backend` | Comma-separated or multiple flags |

**Benefits**:
- Scopes context to relevant directories
- Reduces token usage by excluding irrelevant files
- Improves response quality with focused context

**Examples**:
```bash
# Single additional directory
gemini --include-directories ../shared "explain the shared utilities"

# Multiple directories (comma-separated)
gemini --include-directories "../frontend,../backend" "show me the API integration"

# Multiple flags
gemini --include-directories ../frontend --include-directories ../backend "refactor auth"
```

---

### Accessibility

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `--screen-reader` | Enable screen reader mode | `gemini --screen-reader` | Optimizes output for screen reader accessibility |

**Screen Reader Mode Features**:
- Verbose output descriptions
- Semantic structure markers
- Progress indicators announced
- Tool usage clearly described
- Reduced visual formatting

```bash
# Enable for accessibility
gemini --screen-reader "help me code"
```

---

### Debugging and Logging

| Flag | Description | Example | Constraints/Notes |
|------|-------------|---------|-------------------|
| `-d`, `--debug` | Run in debug mode | `gemini -d "query"` | Shows detailed execution logs |

**Debug Mode Output Includes**:
- Tool invocations with full arguments
- API request/response details
- Token usage statistics
- Model routing decisions
- Extension execution logs
- MCP server communications

```bash
# Debug a failing operation
gemini -d "why isn't this working"

# Debug with JSON output for analysis
gemini -d -o json "complex task" > debug.json
```

---

### Utility Flags

| Flag | Description | Example |
|------|-------------|---------|
| `-v`, `--version` | Show version number | `gemini --version` |
| `-h`, `--help` | Display help | `gemini --help` |

---

## Gemini 3 Pro Setup and Usage

### Prerequisites (one of the following)

| Access Method | Requirements |
|---------------|--------------|
| **Google AI Ultra** | Personal subscription (not Business) |
| **Paid API Key** | Gemini API key with Gemini 3 access |
| **Vertex AI** | Paid Vertex API key with Gemini 3 access |
| **Waitlist** | Sign up at https://goo.gle/geminicli-waitlist-signup |

### Enabling Gemini 3 Pro

1. **Update CLI**:
   ```bash
   npm install -g @google/gemini-cli@latest
   gemini --version  # Should be v0.16.x or later
   ```

2. **Enable Preview Features**:
   ```bash
   gemini
   # In interactive mode, type:
   /settings
   # Toggle "Preview Features" to true
   ```

3. **Verify Access**:
   ```bash
   gemini -m gemini-3-pro-preview "Hello"
   # If you get an error, you don't have access yet
   ```

### Gemini 3 Thinking Levels

Configure via API parameter `thinking_level`:

| Level | Use Case | Latency | Reasoning Depth |
|-------|----------|---------|-----------------|
| `low` | Quick responses, simple tasks, chat | Minimal | Basic |
| `medium` | Balanced (coming soon) | Medium | Moderate |
| `high` (default) | Complex coding, analysis, planning | Higher | Maximum |

### Pricing (Gemini 3 Pro via API)

| Usage | Price (per 1M tokens) |
|-------|----------------------|
| Input (<200k tokens) | $2 |
| Input (>200k tokens) | $4 |
| Output (<200k tokens) | $12 |
| Output (>200k tokens) | $18 |

**Free Tier Limits** (Google AI Studio):
- 5-10 RPM (requests per minute)
- 250k TPM (tokens per minute)
- 50-100 RPD (requests per day)

---

## Environment Variables

### API Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google AI API key | `AIza...` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Use Vertex AI instead of Gemini API | `1` |
| `GEMINI_MODEL` | Default model override | `gemini-3-pro-preview` |

### Feature Toggles

| Variable | Description |
|----------|-------------|
| `GEMINI_CLI_DISABLE_TELEMETRY=1` | Disable telemetry |
| `GEMINI_CLI_DISABLE_UPDATES=1` | Disable update checks |
| `GEMINI_CLI_DEBUG=1` | Enable debug mode by default |

---

## Configuration Files

### Hierarchy (highest to lowest priority)

1. **CLI arguments**: Flags passed at runtime
2. **Environment variables**: Shell environment
3. **Project settings**: `.gemini/settings.json` (project root)
4. **User settings**: `~/.gemini/settings.json`
5. **System defaults**: Built-in defaults

### Example settings.json

**Location**: `~/.gemini/settings.json` (user) or `.gemini/settings.json` (project)

```json
{
  "model": {
    "default": "gemini-3-pro-preview",
    "routing": "auto"
  },
  "experimental": {
    "previewFeatures": true
  },
  "approvalMode": "auto_edit",
  "allowedTools": ["edit", "write", "search"],
  "extensions": {
    "enabled": ["prettier", "eslint"],
    "autoUpdate": true
  },
  "ui": {
    "theme": "dark",
    "showStatusInTitle": true,
    "screenReader": false
  },
  "debug": false
}
```

### Key Configuration Paths

| OS | User Settings | Project Settings |
|----|---------------|------------------|
| **Linux/macOS** | `~/.gemini/settings.json` | `<project>/.gemini/settings.json` |
| **Windows** | `%USERPROFILE%\.gemini\settings.json` | `<project>\.gemini\settings.json` |

---

## Built-in Tools

Gemini CLI includes several built-in tools:

| Tool | Description | Approval Required |
|------|-------------|-------------------|
| **edit** | Edit existing files with targeted changes | Yes (unless `auto_edit`) |
| **write** | Create new files or overwrite existing | Yes (unless `auto_edit`) |
| **read** | Read file contents | No |
| **search** | Search for files or code patterns | No |
| **bash** | Execute shell commands | Yes |
| **google_search** | Search the web for information | No (grounding) |
| **web_fetch** | Fetch content from URLs | Yes |

**Tool Usage in YOLO Mode**:
```bash
# Auto-approve all tools
gemini -y "deploy the app"

# Auto-approve only edit tools
gemini --approval-mode auto_edit "refactor code"

# Specify allowed tools
gemini --allowed-tools edit write search "implement feature"
```

---

## MCP (Model Context Protocol)

### MCP Management Commands

```bash
gemini mcp list                    # List configured MCP servers
gemini mcp add <server>            # Add an MCP server
gemini mcp remove <server>         # Remove an MCP server
gemini mcp enable <server>         # Enable a server
gemini mcp disable <server>        # Disable a server
gemini mcp test <server>           # Test server connection
```

### MCP Configuration File

**Location**: `.gemini/mcp.json` (project) or `~/.gemini/mcp.json` (user)

```json
{
  "servers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

### Popular MCP Servers

| Server | Purpose | Installation |
|--------|---------|--------------|
| **github** | GitHub integration (issues, PRs, repos) | `npx @modelcontextprotocol/server-github` |
| **filesystem** | Extended file system access | `npx @modelcontextprotocol/server-filesystem` |
| **postgres** | PostgreSQL database access | `npx @modelcontextprotocol/server-postgres` |
| **puppeteer** | Browser automation | `npx @modelcontextprotocol/server-puppeteer` |
| **slack** | Slack integration | `npx @modelcontextprotocol/server-slack` |

---

## Slash Commands (Interactive Mode)

Available in interactive REPL:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/settings` | Open settings editor |
| `/model` | Change model or routing mode |
| `/clear` | Clear conversation history |
| `/reset` | Reset session completely |
| `/save` | Save current session |
| `/exit` or `/quit` | Exit Gemini CLI |

---

## Common Usage Patterns

### Quick One-Shot Queries

```bash
# Explain code
gemini "explain what this function does"

# Get documentation
gemini "show me examples of async/await in Python"

# Quick analysis
cat error.log | gemini "what caused these errors?"
```

### Interactive Development Sessions

```bash
# Start with a goal
gemini -i "help me implement user authentication"

# Continue existing work
gemini --resume latest

# Multi-directory project
gemini --include-directories ../api,../frontend -i "implement login flow"
```

### Automated Workflows (CI/CD)

```bash
# Code review with JSON output
gemini -o json "review this PR for security issues" > review.json

# Auto-fix linting (auto-approve edits)
gemini --approval-mode auto_edit "fix all ESLint errors"

# Test generation with specific model
gemini -m gemini-2.5-pro -o json "generate unit tests for this module"

# Sandboxed execution
gemini -s -y "run all tests and report results"
```

### Safe Automation with Approved Tools

```bash
# Only allow safe tools
gemini --allowed-tools read search "analyze this codebase"

# Auto-approve edits only, prompt for shell commands
gemini --approval-mode auto_edit "refactor authentication"

# Allow specific MCP servers
gemini --allowed-mcp-server-names github "create PR for this fix"
```

### Debugging and Troubleshooting

```bash
# Full debug output
gemini -d "why is this test failing?"

# Debug with JSON output for parsing
gemini -d -o json "diagnose issue" | jq '.messages'

# Screen reader mode for accessibility
gemini --screen-reader "help me fix this error"
```

### Session Management Workflow

```bash
# List previous sessions
gemini --list-sessions

# Resume a specific session
gemini --resume 3

# Resume and continue in interactive mode
gemini --resume latest -i "let's continue"

# Clean up old sessions
gemini --delete-session 1
gemini --delete-session 2
```

---

## Best Practices

### Security

- **Never use YOLO mode** (`-y`) on untrusted code or in production
- Use `--sandbox` when testing unknown code
- Use `--allowed-tools` to restrict capabilities in automation
- Store API keys in environment variables, not in commands
- Review tool approvals carefully before accepting

### Performance

- Use `--include-directories` to scope context to relevant code
- Choose appropriate models: Flash for simple tasks, Pro for complex reasoning
- Enable Gemini 3 Pro only when needed (higher cost, usage limits)
- Use streaming JSON (`-o stream-json`) for long-running tasks

### Development Workflow

- Start with `-i` for exploratory development
- Use `--resume` to continue complex multi-session tasks
- Save important sessions with `/save` command
- Use project-level `.gemini/settings.json` for team consistency

### Accessibility

- Enable `--screen-reader` mode for visual impairment
- Use `-o json` for programmatic parsing by assistive tools
- Verbose output helps with screen reader comprehension

### Debugging

- Use `-d` flag to understand model decisions and tool usage
- Combine debug mode with JSON output for analysis
- Check `/settings` to verify Preview Features enabled for Gemini 3

---

## Troubleshooting

### Common Issues

| Issue | Possible Causes | Solutions |
|-------|----------------|-----------|
| "Access Denied" for Gemini 3 | No subscription or waitlist approval | Check access requirements, sign up for waitlist |
| "Model not found" | Typo in model name or unavailable | Use `-m gemini-3-pro-preview` or check model list |
| Tools not working | Permission denied or missing MCP server | Check `--allowed-tools` or MCP configuration |
| High token usage | Including too many files | Use `--include-directories` to scope context |
| Session not found | Deleted or wrong project directory | Use `--list-sessions` to verify |
| Extensions failing | Extension not installed/enabled | Run `gemini extensions list` and enable |

### Getting Help

```bash
# Show help
gemini --help

# List extensions
gemini extensions list

# List sessions
gemini --list-sessions

# Test MCP servers
gemini mcp test <server-name>

# Debug mode for detailed logs
gemini -d "your query"
```

### Gemini 3 Specific Issues

| Issue | Solution |
|-------|----------|
| 404 error | Update to v0.16.x+: `npm install -g @google/gemini-cli@latest` |
| Rate limit hit | Wait or upgrade subscription |
| Capacity error | Automatic fallback to Gemini 2.5 Pro/Flash |
| Access denied | Verify Preview Features enabled in `/settings` |

---

## Gemini 3 Pro Tips

### Prompt Engineering for Gemini 3

- **Be concise and direct** - Gemini 3 doesn't need verbose prompt engineering
- **Less verbose by default** - Explicitly request detailed explanations if needed
- **Place instructions at end** when working with large datasets
- **Keep temperature at default** - Changing may cause looping or degradation

### Thinking Levels

Use higher thinking levels (`high` is default) for:
- Complex algorithmic problems
- Multi-step code refactoring
- System architecture planning
- Deep code analysis

Use lower thinking levels (`low`) for:
- Quick questions
- Simple code explanations
- Basic file operations
- Chat and exploration

### Model Selection Strategy

| Task Type | Recommended Model |
|-----------|-------------------|
| Quick questions, simple edits | Gemini 2.5 Flash |
| General development, refactoring | Gemini 2.5 Pro or Auto routing |
| Complex reasoning, large refactors | Gemini 3 Pro (if available) |
| Maximum speed | Gemini 2.0 Flash Exp |

---

## Quick Reference Card

```bash
# Interactive session
gemini                                    # Start REPL
gemini -i "let's debug"                  # Start with prompt

# One-shot execution
gemini "explain this code"               # Quick query
gemini -p "generate tests"               # Deprecated syntax

# Session management
gemini --resume latest                   # Continue last session
gemini --list-sessions                   # Show all sessions

# Output formats
gemini -o json "analyze"                 # JSON output
gemini -o stream-json "long task"        # Streaming JSON

# Safety and permissions
gemini -s "test untrusted code"          # Sandbox mode
gemini --approval-mode auto_edit         # Auto-approve edits
gemini -y "dangerous task"               # YOLO mode (dangerous!)

# Model selection
gemini -m gemini-3-pro-preview "query"   # Use Gemini 3
gemini -m gemini-2.5-flash "quick"       # Use Flash

# Extensions
gemini -e prettier eslint "format"       # Use specific extensions
gemini --list-extensions                 # Show extensions

# Context control
gemini --include-directories ../app      # Add directories

# Debugging
gemini -d "diagnose issue"               # Debug mode
gemini --screen-reader "help"            # Accessibility mode

# Piping
cat file | gemini "analyze"              # Pipe content
gemini "query" > output.txt              # Redirect output
```

---

## Version History

- **v0.17.1** (November 2025): Current version with stability improvements
- **v0.16.x** (November 2025): Gemini 3 Pro support, preview features
- **v0.15.x**: Session management improvements, UI updates
- **v0.9.x**: Interactive shell with PTY support
- **v0.8.x**: Extensions system introduced

---

## Additional Resources

- **Official Documentation**: https://geminicli.com/docs
- **Gemini 3 Guide**: https://geminicli.com/docs/get-started/gemini-3/
- **Gemini API Docs**: https://ai.google.dev/gemini-api/docs/gemini-3
- **Waitlist Signup**: https://goo.gle/geminicli-waitlist-signup
- **GitHub Repository**: https://github.com/google/gemini-cli
- **MCP Documentation**: https://modelcontextprotocol.io

---

**Note**: This reference is based on Gemini CLI v0.17.1. Some features may change in future versions. Always run `gemini --help` for the most current flag documentation.
