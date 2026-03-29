param(
    [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Branch = "main",
    [string]$Remote = "origin"
)

$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Args)
    & git @Args
    if ($LASTEXITCODE -ne 0) {
        throw "git command failed with exit code ${LASTEXITCODE}: git $($Args -join ' ')"
    }
}

try {
    Set-Location $RepoPath

    # Clear stale lock from an interrupted previous run.
    $indexLock = Join-Path $RepoPath ".git\index.lock"
    if (Test-Path $indexLock) {
        Remove-Item $indexLock -Force
    }

    # Verify git repository.
    $inside = (git rev-parse --is-inside-work-tree 2>$null)
    if ($inside -ne "true") {
        Write-Output "Not a git repository: $RepoPath"
        exit 1
    }

    # Ensure remote exists.
    $remoteExists = git remote 2>$null | Select-String -SimpleMatch $Remote
    if (-not $remoteExists) {
        Write-Output "Remote '$Remote' not found."
        exit 1
    }

    # Work on target branch if available.
    $currentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($currentBranch -ne $Branch) {
        $branchExists = git branch --list $Branch
        if ($branchExists) {
            Invoke-Git @("checkout", $Branch)
        }
    }

    # Stage and commit only when there are changes.
    Invoke-Git @("add", "-A")
    $hasStaged = git diff --cached --name-only
    if (-not $hasStaged) {
        Write-Output "No changes to commit."
        exit 0
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $msg = "chore(auto): hourly update $timestamp"

    Invoke-Git @("commit", "-m", $msg)

    # Sync then push the new commit.
    Invoke-Git @("fetch", $Remote, "--prune")
    Invoke-Git @("pull", "--rebase", "--autostash", $Remote, $Branch)
    Invoke-Git @("push", $Remote, $Branch)

    Write-Output "Hourly update pushed at $timestamp"
    exit 0
}
catch {
    Write-Output "Hourly update failed: $($_.Exception.Message)"
    exit 1
}
