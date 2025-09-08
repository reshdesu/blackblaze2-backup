# Development Notes

## Important Reminders

### File Cleanup Guidelines
When performing project cleanup, be extremely careful not to delete important files:

**DO NOT DELETE:**
- `performance_results.json` - Contains historical performance test results
- `comprehensive_5k_performance_results.txt` - Performance benchmark summaries
- `PERFORMANCE_RESULTS.md` - Human-readable performance documentation
- Any `.json` files with test results or benchmarks
- Any files with "performance", "results", or "benchmark" in the name

**Why this matters:**
- These files contain valuable historical data and test results
- Recreating them requires running expensive tests (e.g., 20-minute comprehensive 5k test)
- They provide context for performance improvements and regressions
- They contain statistical analysis that took significant time to generate

**Safe cleanup approach:**
1. Use `git status` to see what's tracked vs untracked
2. When in doubt, keep files rather than delete them
3. Focus cleanup on temporary files, build artifacts, and cache directories
4. Preserve any files that contain data, results, or historical information

### Context Setup for AI Assistant

**When starting a new session, provide:**
1. **Project Overview**: Brief description of what you're working on and the main issue
2. **Key Files**: List the main files you're working with (main.py, core modules, etc.)
3. **Recent Changes**: What modifications were made and why
4. **Current State**: What's working vs what's broken
5. **Constraints**: What NOT to modify/delete (especially important files)
6. **Environment**: OS, package manager, current app state

**Example good context:**
```
"I'm working on BlackBlaze B2 Backup Tool - a cross-platform backup application.
The main issue is that preview results disappear from the log during backup operations.

Key files: main.py, src/blackblaze_backup/gui.py, src/blackblaze_backup/core.py
Recent changes: Modified preview display logic in gui.py to show results at top of log
Current state: App runs but preview results get cleared when backup starts

Please don't modify: performance_results.json, any benchmark files, or test data
Environment: Ubuntu, using uv, app is currently running locally

I need help fixing the preview results persistence issue."
```

**This avoids:**
- Accidental deletions of important files
- Misunderstanding the current state
- Breaking working functionality
- Wasting time on wrong assumptions
- Recreating expensive test data

### AI Assistant "Don't Do This" List

**NEVER DELETE OR MODIFY:**

**Performance & Test Data Files:**
- `performance_results.json` - Historical performance data
- `comprehensive_5k_performance_results.txt` - Performance benchmarks
- `PERFORMANCE_RESULTS.md` - Performance documentation
- `DEVELOPMENT_NOTES.md` - This file with important reminders
- Any files with "performance", "benchmark", "results" in the name
- Test data directories like `test_photos/`
- Any `.json` files containing test results or data

**Project Configuration Files:**
- `pyproject.toml` - Project configuration and dependencies
- `requirements-ci.txt` - CI/CD dependencies
- `blackblaze_backup.spec` - PyInstaller build specification
- `sample.env` - Environment template
- `uv.lock` - Package lock file
- `.pre-commit-config.yaml` - Pre-commit hooks configuration

**Source Code & Documentation:**
- `src/blackblaze_backup/` directory and all contents
- `main.py` - Application entry point
- `README.md` - Project documentation
- `LICENSE` - Project license
- `CONTRIBUTORS.md` - Contributor information
- `SECURITY.md` - Security policy

**Build & CI Files:**
- `.github/workflows/` directory and all workflow files
- `scripts/` directory and all utility scripts
- `tests/` directory and all test files
- `build_ubuntu.sh` - Ubuntu build script

**Temporary Files (Safe to Delete):**
- `__pycache__/` directories
- `.pytest_cache/` directory
- `htmlcov/` directory
- `coverage.xml` file
- `.ruff_cache/` directory
- `dist/` and `build/` directories (if they exist)

**NEVER DO WITHOUT ASKING:**
- Run expensive tests (like 5k photo generation) without explicit permission
- Commit code changes without user confirmation
- Modify core functionality without understanding the full impact
- Delete any files during "cleanup" without checking what they contain
- Change version numbers without user request
- Modify CI/CD pipeline files without understanding the impact

**NEVER ASSUME:**
- That files are "safe to delete" just because they're not in git
- That performance test results can be easily recreated
- That the user wants automatic commits
- That cleanup means deleting everything that looks temporary
- That test failures mean the code is broken (could be test issues)

**ALWAYS CHECK FIRST:**
- What files contain before deleting them
- Git status to see what's tracked vs untracked
- If expensive operations are really necessary
- With user before making destructive changes
- If there are existing solutions before creating new ones

**COMMON MISTAKES TO AVOID:**
- Deleting performance data files during cleanup
- Running long tests without user permission
- Committing code that hasn't been properly tested
- Modifying working functionality unnecessarily
- Not preserving important historical data
- Breaking existing functionality while fixing other issues

### Recent Issues Fixed
- **Preview Results Display**: Fixed issue where preview results were cleared by `self.log_text.clear()` in `start_backup_immediately` for manual backups
- **Performance Results Restoration**: Recreated `performance_results.json` after accidental deletion during cleanup

### Performance Benchmarks (Current)
- Cache Population: ≤20s (target: avg + 6σ)
- Processing per File: ≤12ms (target: avg + 6σ)
- Total Time (500 files): ≤25s (target: avg + 6σ)
- Cache Lookup: ≤10ms (target: avg + 6σ)

Last Updated: 2025-09-07
