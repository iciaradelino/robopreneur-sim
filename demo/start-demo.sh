#!/usr/bin/env bash
# Opens every node of the demo in its own tmux pane, tiled 3x2:
#
#   | chain   | master  | robot_1 |
#   | robot_2 | human_1 | human_2 |
#
# Move between panes with Ctrl-b + arrow keys, zoom one with Ctrl-b z.
# Killing the session (tmux kill-session -t robopreneur-demo) wipes the chain.
#
# Usage:  ./start-demo.sh   (from demo/, inside WSL)

set -euo pipefail

demo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
py="$demo/.venv/bin/python"
session="robopreneur-demo"

if ! command -v tmux >/dev/null; then
    echo "tmux not found - install it with: sudo apt install tmux" >&2
    exit 1
fi
if [[ ! -x "$py" ]]; then
    echo "Python venv not found at $py - run the setup steps in demo/README.md first." >&2
    exit 1
fi
if (exec 3<>/dev/tcp/127.0.0.1/8545) 2>/dev/null; then
    echo "Port 8545 is already in use - stop the running Ganache first, the demo needs a fresh chain." >&2
    exit 1
fi
if tmux has-session -t "$session" 2>/dev/null; then
    echo "tmux session '$session' already exists - attach with: tmux attach -t $session" >&2
    exit 1
fi

# Build the 3x2 grid: split into two rows, then each row into three equal columns.
new_pane() { tmux split-window -d -c "$demo" -P -F '#{pane_id}' "$@"; }
chain=$(tmux new-session -d -s "$session" -c "$demo" -P -F '#{pane_id}')
robot_2=$(new_pane -v -t "$chain")
master=$(new_pane -h -l 67% -t "$chain")
robot_1=$(new_pane -h -l 50% -t "$master")
human_1=$(new_pane -h -l 67% -t "$robot_2")
human_2=$(new_pane -h -l 50% -t "$human_1")

# Pane titles come from a pane option, so the shell's own title escapes can't overwrite them
tmux set-option -t "$session" pane-border-status top
tmux set-option -t "$session" pane-border-format ' #{@node} '

run() {  # run <pane> <title> <command>: the shell stays open after the command exits
    tmux set-option -p -t "$1" @node "$2"
    tmux send-keys -t "$1" "$3" Enter
}
run "$chain"   chain   "npm run ganache"
run "$master"  master  "'$py' master.py"
run "$robot_1" robot_1 "'$py' agent.py robot_1"
run "$robot_2" robot_2 "'$py' agent.py robot_2"
run "$human_1" human_1 "'$py' agent.py human_1"
run "$human_2" human_2 "'$py' agent.py human_2"

tmux select-pane -t "$master"
if [[ -n "${TMUX:-}" ]]; then
    tmux switch-client -t "$session"
else
    tmux attach -t "$session"
fi
