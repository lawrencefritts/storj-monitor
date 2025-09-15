# Documentation Update Required

The WARP.md and docs/README.md files previously contained references to Windows PowerShell scripts that have been removed during the Linux migration cleanup.

The following PowerShell script references have been removed and should be replaced with their Python equivalents:

## Removed Scripts:
- `.\scripts\setup.ps1` → Use: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- `.\scripts\run_tests.ps1` → Use: `python -m pytest`
- `.\scripts\run_tests.ps1 -Coverage` → Use: `python -m pytest --cov`
- `.\scripts\run_web.ps1` → Use: `python -m uvicorn webapp.server:app`
- `.\scripts\install_collector.ps1` → Manual setup required for systemd service
- `.\scripts\start_collector.ps1` → Use: `python collector/service.py`
- `.\scripts\stop_collector.ps1` → Use standard process termination
- `.\scripts\collect_now.ps1` → Use: `python scripts/collect_now.py`

## Next Steps:
1. Update documentation with Linux-appropriate commands
2. Create Linux shell scripts if needed for complex operations
3. Set up systemd service files for daemon management
