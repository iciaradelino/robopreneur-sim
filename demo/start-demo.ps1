# Opens every node of the demo in its own window, roughly tiled 3x2 on the main screen:
#
#   | chain   | master  | robot_1 |
#   | robot_2 | human_1 | human_2 |
#
# Move and resize them as you like. Closing the chain window wipes the chain.
#
# Usage:  powershell -ExecutionPolicy Bypass -File .\start-demo.ps1   (from demo/)

$demo = $PSScriptRoot
$py = Join-Path $demo ".venv\Scripts\python.exe"

if (-not (Test-Path $py)) {
    Write-Error "Python venv not found at $py - run the setup steps in demo\README.md first."
    exit 1
}
if (Get-NetTCPConnection -LocalPort 8545 -State Listen -ErrorAction SilentlyContinue) {
    Write-Error "Port 8545 is already in use - stop the running Ganache first, the demo needs a fresh chain."
    exit 1
}

$nodes = @(
    @{ title = "chain";   cmd = @("cmd", "/k", "npm run ganache") },
    @{ title = "master";  cmd = @($py, "master.py") },
    @{ title = "robot_1"; cmd = @($py, "agent.py", "robot_1") },
    @{ title = "robot_2"; cmd = @($py, "agent.py", "robot_2") },
    @{ title = "human_1"; cmd = @($py, "agent.py", "human_1") },
    @{ title = "human_2"; cmd = @($py, "agent.py", "human_2") }
)

Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.WorkingArea
$cellW = [int]($screen.Width / 3)
$cellH = [int]($screen.Height / 2)

for ($i = 0; $i -lt $nodes.Count; $i++) {
    $node = $nodes[$i]
    $x = $screen.X + ($i % 3) * $cellW
    $y = $screen.Y + [Math]::Floor($i / 3) * $cellH
    if (Get-Command wt.exe -ErrorAction SilentlyContinue) {
        # -w new: a separate window per node; agents take a positional name (no dashes)
        # so wt doesn't mistake their arguments for its own options
        $wtArgs = @("-w", "new", "--pos", "$x,$y", "new-tab", "--title", $node.title,
                    "--suppressApplicationTitle", "-d", $demo) + $node.cmd
        Start-Process wt.exe -ArgumentList $wtArgs
    }
    else {
        $command = "cd '$demo'; & " + (($node.cmd | ForEach-Object { "'$_'" }) -join " ")
        Start-Process powershell -ArgumentList "-NoExit", "-Command", $command
    }
    Start-Sleep -Milliseconds 300  # keep the windows opening in order
}
