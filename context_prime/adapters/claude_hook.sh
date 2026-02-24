#!/usr/bin/env bash
# Context Prime — Claude Code Hook Adapter
#
# Install as a SessionStart or UserPromptSubmit hook in Claude Code.
#
# SessionStart hook (primes once at session start):
#   Add to .claude/settings.json:
#   {
#     "hooks": {
#       "SessionStart": [{
#         "matcher": "*",
#         "hooks": [{
#           "type": "command",
#           "command": "bash /path/to/context_prime/adapters/claude_hook.sh session",
#           "timeout": 30
#         }]
#       }]
#     }
#   }
#
# UserPromptSubmit hook (primes per-task):
#   {
#     "hooks": {
#       "UserPromptSubmit": [{
#         "matcher": "*",
#         "hooks": [{
#           "type": "command",
#           "command": "bash /path/to/context_prime/adapters/claude_hook.sh prompt",
#           "timeout": 30
#         }]
#       }]
#     }
#   }

set -euo pipefail

HOOK_MODE="${1:-session}"  # "session" or "prompt"
INPUT=$(cat)

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"

if [ "$HOOK_MODE" = "session" ]; then
    # Session start: lightweight project-level priming
    # Outputs context that Claude sees at session start
    python3 -m context_prime.cli prime \
        --project "$PROJECT_DIR" \
        --mode session \
        --format hook 2>/dev/null || true

elif [ "$HOOK_MODE" = "prompt" ]; then
    # Per-prompt: extract task and do task-specific priming
    USER_PROMPT=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('user_prompt', ''))
" 2>/dev/null || echo "")

    if [ -n "$USER_PROMPT" ]; then
        python3 -m context_prime.cli prime \
            --project "$PROJECT_DIR" \
            --task "$USER_PROMPT" \
            --mode task \
            --format hook 2>/dev/null || true
    fi
fi
