# Release - Quick Release Automation

Skill for automating the full release flow of workflows-manager.

## Usage

```
/release <version>
```

Example: `/release 0.3.1`

## What it does

Executes the full release flow in one shot:

1. **Validate** - Ensure clean working tree and on master
2. **Bump** - Update version in `pyproject.toml`
3. **Branch** - Create `release/v<version>` from master
4. **Commit + Push** - Commit version bump and push branch
5. **PR** - Create PR to master
6. **Wait** - Wait for GitHub Actions checks to pass
7. **Merge** - Merge PR (merge commit, delete branch)
8. **Cleanup** - Return to master and pull

## Instructions

When invoked, parse the version from the arguments. Then execute ALL steps sequentially without asking for confirmation at each step. Only stop if an error occurs.

### Step 1: Validate
```bash
git status --porcelain
git branch --show-current
```
- Working tree must be clean
- Must be on `master` branch
- If not, STOP and tell the user

### Step 2: Bump version
- Edit `pyproject.toml`: update `version = "X.Y.Z"` to the new version
- Edit `wfm/__init__.py`: update the fallback `__version__ = "X.Y.Z"` to the new version
- Validate the version format matches semver (X.Y.Z)

### Step 3: Create branch and commit
```bash
git checkout -b release/v<version>
git add pyproject.toml wfm/__init__.py
git commit -m "chore: release v<version>"
```

### Step 4: Push
```bash
git push -u origin release/v<version>
```

### Step 5: Create PR
```bash
gh pr create --title "Release v<version>" --body "Release v<version>"
```

### Step 6: Wait for checks
```bash
gh pr checks <pr-number> --watch
```
- Timeout: 5 minutes max
- If checks fail, STOP and report the failure

### Step 7: Merge
```bash
gh pr merge <pr-number> --merge --delete-branch
```

### Step 8: Cleanup
```bash
git checkout master
git pull
```

### Output
Print a summary table at the end with each step's status.

Then remind: on the target machine, run `wfm self-update` to get the new version.
