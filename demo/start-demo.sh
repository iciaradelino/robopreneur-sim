#!/usr/bin/env bash
# Opens every node of the demo in its own Windows Terminal window, roughly tiled 3x2:
#
#   | chain   | master  | robot_1 |
#   | robot_2 | human_1 | human_2 |
#
# Each node runs in its own tmux session on a private socket, so closing a window only
# detaches it: reopen one with  tmux -L robopreneur-demo attach -t <node>.
# tmux -L robopreneur-demo kill-server stops everything and wipes the chain.
#
# Usage:  ./start-demo.sh   (from demo/, inside WSL)

set -euo pipefail

demo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
py="$demo/.venv/bin/python"
sock="robopreneur-demo"
tm() { tmux -L "$sock" "$@"; }

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
if tm has-session 2>/dev/null; then
    echo "The demo is already running - stop it with: tmux -L $sock kill-server" >&2
    exit 1
fi

nodes=(chain master robot_1 robot_2 human_1 human_2)
declare -A cmds=(
    [chain]="npm run ganache"
    [master]="'$py' master.py"
    [robot_1]="'$py' agent.py robot_1"
    [robot_2]="'$py' agent.py robot_2"
    [human_1]="'$py' agent.py human_1"
    [human_2]="'$py' agent.py human_2"
)

# Typed into a shell rather than run directly, so the shell stays open after the command exits
for node in "${nodes[@]}"; do
    tm new-session -d -s "$node" -n "$node" -c "$demo"
    tm send-keys -t "$node" "${cmds[$node]}" Enter
done
tm set-option -g status-left " #S "

if ! command -v wt.exe >/dev/null || [[ -z "${WSL_DISTRO_NAME:-}" ]]; then
    echo "Windows Terminal not found - attaching here instead, switch nodes with Ctrl-b s." >&2
    exec tmux -L "$sock" attach -t master
fi

# Tile the windows over the primary screen's working area (falls back to wt's default spot)
read -r sx sy sw sh < <(powershell.exe -NoProfile -Command \
    'Add-Type -AssemblyName System.Windows.Forms; $a = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea; "$($a.X) $($a.Y) $($a.Width) $($a.Height)"' \
    2>/dev/null | tr -d '\r') || true

for i in "${!nodes[@]}"; do
    node="${nodes[$i]}"
    pos=()
    if [[ -n "${sh:-}" ]]; then
        pos=(--pos "$((sx + i % 3 * sw / 3)),$((sy + i / 3 * sh / 2))")
    fi
    # -w new: a separate window per node; "--" stops wt parsing the wsl/tmux flags as its own
    wt.exe -w new "${pos[@]}" new-tab --title "$node" --suppressApplicationTitle \
        -- wsl.exe -d "$WSL_DISTRO_NAME" -- tmux -L "$sock" attach -t "$node"
    sleep 0.3  # keep the windows opening in order
done
