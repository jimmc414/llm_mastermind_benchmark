# Codex CLI Command Line Reference

A comprehensive reference for Codex CLI command-line options, subcommands, and configuration.

**Last Updated**: November 24, 2025 | **CLI Version**: v0.63.0

---

## Overview

Codex CLI is an AI-powered coding assistant that runs in your terminal. It provides intelligent code generation, refactoring, debugging, and file operations through a conversational interface.

**Key Features**:
- Interactive and non-interactive modes
- Advanced sandboxing with multiple security levels
- Flexible approval policies for command execution
- Local model support (LM Studio, Ollama)
- Cloud model integration (OpenAI, Anthropic, etc.)
- MCP (Model Context Protocol) server support
- Configuration profiles for different workflows
- Git integration with `apply` command
- Web search capabilities
- Multi-modal support (images)

---

## Quick Start

```bash
# Interactive mode
codex

# Interactive with initial prompt
codex "help me refactor this module"

# Non-interactive execution
codex exec "generate unit tests"

# With specific model
codex -m o3 "explain this code"

# Safe auto-execution mode
codex --full-auto "fix all linting errors"

# Local OSS model
codex --oss "analyze this function"
```

---

## Core Commands

### Main Commands

| Command | Aliases | Description | Example |
|---------|---------|-------------|---------|
| `codex` | - | Interactive mode (default) | `codex` |
| `codex [PROMPT]` | - | Interactive with initial prompt | `codex "help me debug"` |
| `codex exec` | `e` | Non-interactive execution | `codex exec "generate tests"` |
| `codex resume` | - | Resume previous session | `codex resume` |
| `codex apply` | `a` | Apply latest diff as `git apply` | `codex apply` |
| `codex login` | - | Manage authentication | `codex login` |
| `codex logout` | - | Remove stored credentials | `codex logout` |
| `codex mcp` | - | Manage MCP servers (experimental) | `codex mcp list` |
| `codex sandbox` | `debug` | Run in Codex sandbox | `codex sandbox bash` |
| `codex cloud` | - | Browse Codex Cloud tasks | `codex cloud` |
| `codex completion` | - | Generate shell completions | `codex completion bash` |
| `codex features` | - | Inspect feature flags | `codex features` |

---

## CLI Options - Complete Reference

### Basic Options

| Option | Description | Example | Constraints/Notes |
|--------|-------------|---------|-------------------|
| `[PROMPT]` | Initial user prompt (positional) | `codex "explain this code"` | Opens interactive mode with prompt |
| `-m`, `--model <MODEL>` | Specify model to use | `codex -m o3` | Model identifier (e.g., `o3`, `gpt-4`, `claude-sonnet-4`) |
| `-i`, `--image <FILE>...` | Attach image(s) to initial prompt | `codex -i screenshot.png "explain this UI"` | Repeatable for multiple images |
| `-C`, `--cd <DIR>` | Set working directory | `codex -C /path/to/project` | Agent uses this as workspace root |
| `-h`, `--help` | Show help | `codex --help` | Detailed help with all options |
| `-V`, `--version` | Show version | `codex --version` | Current CLI version |

---

### Model Selection

| Option | Description | Example | Constraints/Notes |
|--------|-------------|---------|-------------------|
| `-m`, `--model <MODEL>` | Specify cloud or local model | `codex -m claude-sonnet-4` | Model string depends on provider |
| `--oss` | Use local OSS model provider | `codex --oss` | Auto-detects LM Studio or Ollama |
| `--local-provider <PROVIDER>` | Specify local provider | `codex --oss --local-provider ollama` | `lmstudio` or `ollama` |

**Cloud Models**:
- OpenAI: `o3`, `o1`, `gpt-4o`, `gpt-4-turbo`
- Anthropic: `claude-sonnet-4`, `claude-opus-4`
- Google: `gemini-pro`, `gemini-flash`

**Local Models** (via `--oss`):
- Requires LM Studio or Ollama running locally
- Use `--local-provider` to specify which one
- Example: `codex --oss --local-provider ollama -m llama3`

**Examples**:
```bash
# Cloud model
codex -m claude-sonnet-4 "refactor this function"

# Local OSS model (auto-detect provider)
codex --oss "analyze codebase"

# Local OSS with specific provider
codex --oss --local-provider lmstudio -m deepseek-coder "generate tests"
```

---

### Sandbox Policies

| Option | Description | Risk Level | Use Case |
|--------|-------------|------------|----------|
| `-s`, `--sandbox read-only` | Read-only file system access | Low | Safe code analysis |
| `-s`, `--sandbox workspace-write` | Write access to workspace only | Medium | Development tasks |
| `-s`, `--sandbox danger-full-access` | Full system access (no sandbox) | **HIGH** | Trusted operations |

**Sandbox Policy Details**:

| Policy | File System | Shell Commands | Network |
|--------|-------------|----------------|---------|
| `read-only` | Read entire system | Limited safe commands | Restricted |
| `workspace-write` | Read system, write workspace | Full command access (sandboxed) | Restricted |
| `danger-full-access` | Full read/write | Full unsandboxed access | Unrestricted |

**Examples**:
```bash
# Safe read-only analysis
codex -s read-only "explain this codebase architecture"

# Development with write access
codex -s workspace-write "implement new feature"

# Full access (dangerous!)
codex -s danger-full-access "configure system settings"
```

**Security Warning**: `danger-full-access` disables all safety mechanisms. Use only in controlled environments.

---

### Approval Policies

| Option | Description | Behavior | Use Case |
|--------|-------------|----------|----------|
| `-a`, `--ask-for-approval untrusted` | Approve trusted commands only | Prompts for untrusted commands | Balanced safety |
| `-a`, `--ask-for-approval on-failure` | Approve on command failure | Escalates only when commands fail | Smooth automation |
| `-a`, `--ask-for-approval on-request` | Model decides when to ask | AI determines approval needs | Flexible automation |
| `-a`, `--ask-for-approval never` | Never ask for approval | Executes all commands automatically | Full automation (risky) |

**Approval Policy Details**:

| Policy | When Prompts Appear | Trusted Commands | Failed Commands |
|--------|---------------------|------------------|-----------------|
| `untrusted` | For untrusted commands | Auto-approved | Escalated to user |
| `on-failure` | Only on failure | Auto-approved | Escalated to user |
| `on-request` | Model decides | Auto-approved | Escalated if model requests |
| `never` | Never | Auto-approved | Returned to model |

**Trusted Commands** (examples):
- `ls`, `cat`, `grep`, `find`, `head`, `tail`
- `git status`, `git diff`, `git log`
- `npm list`, `pip list`
- Read-only operations

**Examples**:
```bash
# Prompt for risky commands
codex -a untrusted "refactor authentication"

# Only prompt on failures
codex -a on-failure "run all tests"

# Let model decide
codex -a on-request "deploy application"

# Never prompt (dangerous!)
codex -a never "automated CI job"
```

---

### Convenience Flags

| Option | Description | Equivalent To | Use Case |
|--------|-------------|---------------|----------|
| `--full-auto` | Low-friction automatic execution | `-a on-request -s workspace-write` | Safe automation |
| `--dangerously-bypass-approvals-and-sandbox` | Skip ALL safety checks | `-a never -s danger-full-access` | **EXTREMELY DANGEROUS** |

**`--full-auto` Mode**:
- Combines workspace write access with model-controlled approvals
- Balanced between safety and automation
- Recommended for most automated workflows

**`--dangerously-bypass-approvals-and-sandbox`**:
- Disables all safety mechanisms
- Intended **ONLY** for externally sandboxed environments (Docker, VMs)
- **DO NOT USE** on your main development machine

**Examples**:
```bash
# Safe automated development
codex --full-auto "implement user login feature"

# Dangerous mode (only in Docker/VM!)
docker run --rm -v $(pwd):/workspace codex-container \
  codex --dangerously-bypass-approvals-and-sandbox "system configuration"
```

---

### Configuration Override

| Option | Description | Example | Constraints/Notes |
|--------|-------------|---------|-------------------|
| `-c`, `--config <key=value>` | Override config value | `-c model="o3"` | Uses TOML syntax, dotted paths for nesting |
| `--enable <FEATURE>` | Enable a feature flag | `--enable web_search` | Equivalent to `-c features.<name>=true` |
| `--disable <FEATURE>` | Disable a feature flag | `--disable telemetry` | Equivalent to `-c features.<name>=false` |
| `-p`, `--profile <PROFILE>` | Load config profile | `codex -p production` | Profile from `~/.codex/config.toml` |

**Configuration Override Syntax**:
```bash
# Simple value
-c model="o3"

# Nested value (dotted path)
-c shell_environment_policy.inherit=all

# Array value
-c 'sandbox_permissions=["disk-full-read-access"]'

# Boolean
-c features.web_search=true

# Multiple overrides
codex -c model="claude-sonnet-4" -c features.web_search=true "query"
```

**Feature Flags**:
```bash
# Enable web search
codex --enable web_search "research this topic"

# Disable telemetry
codex --disable telemetry

# Multiple features
codex --enable web_search --disable telemetry --enable mcp
```

**Profile Example** (`~/.codex/config.toml`):
```toml
[profiles.development]
model = "gpt-4o"
sandbox = "workspace-write"
ask_for_approval = "untrusted"
features.web_search = false

[profiles.production]
model = "o3"
sandbox = "read-only"
ask_for_approval = "never"
features.web_search = true
```

Usage:
```bash
codex -p development "implement feature"
codex -p production "analyze logs"
```

---

### Additional Workspace Directories

| Option | Description | Example | Constraints/Notes |
|--------|-------------|---------|-------------------|
| `--add-dir <DIR>` | Make additional directories writable | `codex --add-dir ../shared "update shared utils"` | Repeatable, relative or absolute paths |

**Benefits**:
- Extends workspace beyond primary directory
- Useful for monorepos or multi-project tasks
- Maintains sandbox security outside specified directories

**Examples**:
```bash
# Single additional directory
codex --add-dir ../api "implement API client"

# Multiple directories
codex --add-dir ../frontend --add-dir ../backend "integrate services"

# Combined with sandbox policy
codex -s workspace-write --add-dir ../shared --add-dir ../docs "update documentation"
```

---

### Feature Flags

| Option | Description | Example |
|--------|-------------|---------|
| `--search` | Enable web search tool | `codex --search "research best practices"` |

**Web Search**:
- When enabled, native `web_search` tool is available to model
- No per-call approval required
- Model can search web for information during task execution

```bash
# With web search
codex --search "find and implement current React patterns"

# Via config
codex -c features.web_search=true "research and implement"

# Via enable flag
codex --enable web_search "lookup API documentation"
```

---

## Subcommands

### exec (Non-Interactive Execution)

**Alias**: `e`

Execute a single task and exit (non-interactive).

```bash
codex exec [OPTIONS] <PROMPT>
```

**Use Cases**:
- CI/CD pipelines
- Scripted automation
- One-off tasks
- Batch processing

**Examples**:
```bash
# Quick code generation
codex exec "generate tests for main.py"

# With specific options
codex exec -m claude-sonnet-4 -s workspace-write "refactor auth module"

# In CI/CD
codex exec --full-auto "lint and fix all code"

# With output capture
codex exec "analyze code quality" > report.txt
```

---

### resume (Session Management)

Resume a previous interactive session.

```bash
codex resume [OPTIONS]
```

**Options**:
- No arguments: Show picker to select session
- `--last`: Resume most recent session

**Examples**:
```bash
# Interactive picker
codex resume

# Resume last session
codex resume --last

# Continue specific task
codex resume  # then select from list
```

---

### apply (Git Integration)

**Alias**: `a`

Apply the latest diff produced by Codex as `git apply` to your working tree.

```bash
codex apply [OPTIONS]
```

**How it Works**:
1. Codex generates code changes during session
2. Changes are stored as diff
3. `apply` command applies diff to working tree via `git apply`

**Use Cases**:
- Review changes before committing
- Incrementally apply AI-generated modifications
- Integration with git workflow

**Examples**:
```bash
# After a codex session that generated changes
codex apply

# Review changes first
codex apply --dry-run  # if supported

# Apply and commit
codex apply && git commit -am "Applied Codex changes"
```

---

### sandbox (Debug Environment)

**Alias**: `debug`

Run commands within a Codex-provided sandbox.

```bash
codex sandbox [COMMAND] [ARGS]
```

**Use Cases**:
- Debug sandbox behavior
- Test commands in isolation
- Understand sandbox restrictions

**Examples**:
```bash
# Test bash commands
codex sandbox bash

# Run specific command
codex sandbox ls -la

# Test file operations
codex sandbox cat README.md
```

---

### login (Authentication)

Manage login credentials for cloud model providers.

```bash
codex login [OPTIONS]
```

**Supported Providers**:
- OpenAI
- Anthropic
- Google (Gemini)
- Others as configured

**Examples**:
```bash
# Interactive login
codex login

# Login to specific provider
codex login --provider anthropic

# Set API key
codex login --api-key sk-...
```

---

### logout (Remove Credentials)

Remove stored authentication credentials.

```bash
codex logout [OPTIONS]
```

**Examples**:
```bash
# Logout from all providers
codex logout

# Logout from specific provider
codex logout --provider openai
```

---

### mcp (Model Context Protocol)

**Status**: Experimental

Manage MCP servers or run Codex as an MCP server.

```bash
codex mcp [COMMAND]
```

**Commands**:
- `list` - List configured MCP servers
- `add` - Add an MCP server
- `remove` - Remove an MCP server
- `enable` - Enable an MCP server
- `disable` - Disable an MCP server

**Examples**:
```bash
# List MCP servers
codex mcp list

# Add a server
codex mcp add github

# Enable a server
codex mcp enable github
```

---

### mcp-server (Run as MCP Server)

**Status**: Experimental

Run Codex as an MCP server with stdio transport.

```bash
codex mcp-server [OPTIONS]
```

**Use Cases**:
- Integrate Codex into other tools
- Expose Codex capabilities via MCP
- Build custom MCP clients

---

### app-server (Web Server)

**Status**: Experimental

Run the app server or related tooling.

```bash
codex app-server [OPTIONS]
```

---

### cloud (Codex Cloud Integration)

**Status**: Experimental

Browse tasks from Codex Cloud and apply changes locally.

```bash
codex cloud [OPTIONS]
```

**Features**:
- Browse cloud-hosted tasks
- Apply remote changes to local workspace
- Sync with team workflows

---

### completion (Shell Completions)

Generate shell completion scripts for Codex CLI.

```bash
codex completion <SHELL>
```

**Supported Shells**:
- `bash`
- `zsh`
- `fish`
- `powershell`

**Installation**:
```bash
# Bash
codex completion bash > /etc/bash_completion.d/codex

# Zsh
codex completion zsh > ~/.zsh/completions/_codex

# Fish
codex completion fish > ~/.config/fish/completions/codex.fish
```

---

### features (Feature Flags)

Inspect available feature flags and their current status.

```bash
codex features [OPTIONS]
```

**Examples**:
```bash
# List all features
codex features

# Show specific feature
codex features --show web_search
```

---

## Configuration Files

### Configuration Hierarchy

Configuration is loaded in the following order (highest priority first):

1. **Command-line arguments**: `-c`, `--enable`, `--disable`, etc.
2. **Profile**: Selected via `-p/--profile`
3. **Project config**: `.codex/config.toml` (in current directory)
4. **User config**: `~/.codex/config.toml`
5. **System defaults**: Built-in defaults

### User Configuration File

**Location**: `~/.codex/config.toml`

```toml
# Default model
model = "claude-sonnet-4"

# Default model provider
model_provider = "anthropic"  # or "openai", "google", "oss"

# Default sandbox policy
sandbox = "workspace-write"  # "read-only", "workspace-write", "danger-full-access"

# Default approval policy
ask_for_approval = "untrusted"  # "untrusted", "on-failure", "on-request", "never"

# Feature flags
[features]
web_search = false
telemetry = true
mcp = false

# Shell environment policy
[shell_environment_policy]
inherit = "safe"  # "all", "safe", "none"

# Sandbox permissions (advanced)
sandbox_permissions = ["workspace-full-access"]

# Profiles
[profiles.dev]
model = "gpt-4o"
sandbox = "workspace-write"
ask_for_approval = "untrusted"

[profiles.prod]
model = "o3"
sandbox = "read-only"
ask_for_approval = "never"

[profiles.local]
model_provider = "oss"
model = "deepseek-coder"
sandbox = "workspace-write"
```

### Project Configuration

**Location**: `.codex/config.toml` (project root)

```toml
# Project-specific defaults
model = "claude-sonnet-4"
sandbox = "workspace-write"

# Additional writable directories
add_dirs = ["../shared", "../docs"]

# Project features
[features]
web_search = true

# Project-specific profiles
[profiles.test]
sandbox = "read-only"
ask_for_approval = "never"
```

**Benefits**:
- Share configuration with team via git
- Consistent behavior across team members
- Project-specific policies

---

## Common Usage Patterns

### Interactive Development

```bash
# Start interactive session
codex

# Start with initial prompt
codex "help me implement user authentication"

# With specific model
codex -m claude-sonnet-4 "refactor this module"

# Resume previous work
codex resume --last

# With web search enabled
codex --search "research and implement OAuth2"
```

### Safe Automation

```bash
# Full auto mode (safe automation)
codex --full-auto "fix all linting errors"

# Workspace write with trusted command approval
codex -s workspace-write -a untrusted "implement feature"

# Read-only analysis
codex -s read-only "analyze code quality"

# With additional directories
codex --full-auto --add-dir ../shared "update shared utilities"
```

### Non-Interactive Execution

```bash
# One-shot execution
codex exec "generate tests for main.py"

# With output capture
codex exec "analyze code" > analysis.txt

# In scripts
#!/bin/bash
codex exec --full-auto "run tests and fix failures"

# CI/CD pipeline
codex exec -s read-only "lint and report issues" | tee report.txt
```

### Model Selection Workflows

```bash
# Cloud models
codex -m o3 "complex reasoning task"
codex -m claude-sonnet-4 "code generation"
codex -m gpt-4o "general development"

# Local OSS models
codex --oss "quick code analysis"
codex --oss --local-provider ollama -m llama3 "explain code"
codex --oss --local-provider lmstudio -m deepseek "generate functions"
```

### Multi-Modal Tasks

```bash
# Attach images
codex -i screenshot.png "explain what this UI does"

# Multiple images
codex -i ui1.png -i ui2.png "compare these designs"

# With prompt
codex -i diagram.png "implement the architecture shown"
```

### Profile-Based Workflows

```bash
# Use development profile
codex -p dev "implement new feature"

# Use production profile (read-only)
codex -p prod "analyze production logs"

# Use local model profile
codex -p local "quick code review"
```

### Configuration Overrides

```bash
# Override single config value
codex -c model="o3" "complex task"

# Multiple overrides
codex -c model="gpt-4o" -c features.web_search=true "research and implement"

# Override nested values
codex -c shell_environment_policy.inherit=all "run environment-dependent task"

# Feature flags
codex --enable web_search --enable mcp "complex integration"
```

### Git Integration

```bash
# Generate changes
codex "refactor authentication module"

# Review and apply
codex apply

# Or combine with git
codex apply && git add -A && git commit -m "Refactored auth module"
```

---

## Security Best Practices

### Sandbox Usage

**DO**:
- Use `read-only` for code analysis and reviews
- Use `workspace-write` for most development tasks
- Use `--full-auto` for balanced automation
- Limit `--add-dir` to necessary directories only

**DON'T**:
- Use `danger-full-access` on your main machine
- Use `--dangerously-bypass-approvals-and-sandbox` outside containers
- Grant full access for untrusted or unknown tasks

### Approval Policies

**DO**:
- Use `untrusted` for interactive development
- Use `on-failure` for well-understood automated tasks
- Review untrusted commands before approving
- Test automation in safe environments first

**DON'T**:
- Use `never` without understanding the risks
- Blindly approve commands without reading them
- Use full automation for sensitive operations

### Model Selection

**DO**:
- Use cloud models for complex tasks requiring reasoning
- Use local OSS models for privacy-sensitive code
- Select appropriate model for task complexity
- Consider cost vs. capability tradeoffs

**DON'T**:
- Send proprietary code to cloud models without permission
- Use weak models for complex reasoning tasks
- Assume all models have same capabilities

### Configuration Security

**DO**:
- Store API keys in environment variables or secure credential stores
- Use profiles for different security contexts
- Review project config before running
- Keep sensitive config out of version control

**DON'T**:
- Store API keys in config.toml
- Commit credentials to git
- Share personal configuration publicly

---

## Troubleshooting

### Common Issues

| Issue | Possible Causes | Solutions |
|-------|----------------|-----------|
| "Model not found" | Invalid model name or no credentials | Check model name, run `codex login` |
| "Permission denied" | Sandbox policy too restrictive | Use `-s workspace-write` or add directory with `--add-dir` |
| "Command failed" | Untrusted command blocked | Approve command or use `-a on-failure` |
| "Cannot connect to local model" | LM Studio/Ollama not running | Start local model server, verify with `--oss` |
| "Config parse error" | Invalid TOML syntax | Check `~/.codex/config.toml` syntax |
| "Feature not available" | Feature flag disabled | Use `--enable <feature>` or check config |

### Debug Mode

```bash
# Enable verbose logging
codex -c log_level="debug" "query"

# Check feature flags
codex features

# Test sandbox
codex sandbox bash
```

### Getting Help

```bash
# Main help
codex --help

# Subcommand help
codex exec --help
codex resume --help

# Feature inspection
codex features

# Check version
codex --version
```

---

## Quick Reference Card

```bash
# Interactive modes
codex                                     # Start REPL
codex "prompt"                           # Interactive with prompt
codex -i image.png "query"               # With image

# Non-interactive
codex exec "task"                        # One-shot execution
codex exec --full-auto "automated task"  # Safe automation

# Model selection
codex -m o3 "query"                      # Specific cloud model
codex --oss "query"                      # Local OSS model
codex --oss --local-provider ollama      # Specific local provider

# Security levels
codex -s read-only                       # Safe analysis
codex -s workspace-write                 # Development
codex --full-auto                        # Balanced automation
codex -s danger-full-access              # Full access (dangerous!)

# Approval policies
codex -a untrusted                       # Prompt for risky commands
codex -a on-failure                      # Only prompt on failure
codex -a on-request                      # Model decides
codex -a never                           # Never prompt (risky!)

# Configuration
codex -c model="o3"                      # Override config
codex --enable web_search                # Enable feature
codex -p production                      # Use profile

# Session management
codex resume                             # Resume session (picker)
codex resume --last                      # Resume most recent

# Git integration
codex apply                              # Apply latest diff

# Additional features
codex --search "query"                   # Enable web search
codex --add-dir ../shared                # Additional directory
codex -C /path/to/project                # Set working directory

# Help and info
codex --help                             # Show help
codex --version                          # Show version
codex features                           # List features
```

---

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `CODEX_CONFIG_DIR` | Override config directory | `~/.codex` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `GOOGLE_API_KEY` | Google API key | `AIza...` |

---

## Advanced Configuration

### Sandbox Permissions

Advanced sandbox permission configuration (in config.toml):

```toml
sandbox_permissions = [
  "workspace-full-access",
  "disk-full-read-access",
  "network-localhost"
]
```

### Shell Environment Policy

Control which environment variables are inherited:

```toml
[shell_environment_policy]
inherit = "safe"  # "all", "safe", or "none"

# Custom allowed variables
allowed_vars = ["PATH", "HOME", "USER"]

# Blocked variables
blocked_vars = ["AWS_SECRET", "API_KEY"]
```

### Model Provider Configuration

```toml
model_provider = "anthropic"  # "openai", "google", "anthropic", "oss"

[model_providers.openai]
api_key_env = "OPENAI_API_KEY"
base_url = "https://api.openai.com/v1"

[model_providers.oss]
provider = "ollama"  # or "lmstudio"
base_url = "http://localhost:11434"
```

---

## Tips and Tricks

### Efficient Workflows

1. **Use profiles** for different contexts (dev, prod, review)
2. **Enable web search** for research-heavy tasks
3. **Use `--full-auto`** for routine automated tasks
4. **Resume sessions** to continue complex multi-step work
5. **Apply diffs** incrementally to review changes

### Performance Optimization

1. **Choose appropriate models**: Fast models for simple tasks, powerful for complex
2. **Use local models** for repetitive tasks (no API latency)
3. **Limit context** with `-C` and `--add-dir` to only needed directories
4. **Cache configurations** in profiles for quick access

### Safety First

1. **Start restrictive**: Begin with `read-only`, escalate as needed
2. **Test in sandbox**: Use `codex sandbox` to test commands
3. **Review changes**: Check diffs before applying
4. **Use profiles**: Separate dev and prod configurations
5. **Incremental automation**: Start with `untrusted`, move to `on-failure` when confident

---

## Additional Resources

- **Official Documentation**: https://codex.dev/docs
- **GitHub Repository**: https://github.com/codex/cli
- **Configuration Examples**: https://codex.dev/docs/configuration
- **Community**: https://discord.gg/codex

---

**Note**: This reference is based on Codex CLI v0.63.0. Features and options may change in future versions. Always run `codex --help` for the most current documentation.
