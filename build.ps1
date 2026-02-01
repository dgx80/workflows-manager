# cicd-workflow build script
# Forces a clean rebuild and global installation with uv tool

Write-Host "Cleaning build artifacts..." -ForegroundColor Cyan
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue dist, build, *.egg-info

Write-Host "Installing cicd globally with uv tool..." -ForegroundColor Cyan
uv tool install . --force --reinstall

if ($LASTEXITCODE -eq 0) {
    Write-Host "Done! cicd CLI installed successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  cicd init       Initialize workflows in a project"
    Write-Host "  cicd update     Update workflows from GitHub"
    Write-Host "  cicd list       List workflows and agents"
    Write-Host "  cicd version    Show version info"
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
