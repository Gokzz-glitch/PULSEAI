Write-Host "Starting auto-backup script. Will commit every 30 seconds if changes exist."
while ($true) {
    Start-Sleep -Seconds 30
    $status = git status --porcelain
    if ($status) {
        git add .
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git commit -m "Auto-backup timestamp: $timestamp"
        
        Write-Host "Committed at $timestamp"
        # If there's a remote origin configured, push it
        $remote = git remote
        if ($remote) {
            git push origin HEAD
        }
    }
}
