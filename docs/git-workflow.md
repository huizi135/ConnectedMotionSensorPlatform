# Repository workflow and Windows synchronization

This repository is the source of truth for project files. The assistant can read
and modify the connected GitHub repository. The assistant cannot directly modify
the owner's Windows C drive or execute PowerShell there.

## Change workflow

1. Inspect the current remote branch before making changes.
2. Prepare a focused change on a work branch.
3. Run appropriate checks and record their actual environment and limits.
4. Commit the files and open a pull request for review.
5. Synchronize the Windows checkout using Git.
6. Merge after review and applicable phase acceptance; do not force-push main.

Phase 0 work is on `docs/phase-0-baseline`. Phase 1 implementation has not begun.
Remote source changes do not imply that Windows tests were executed.

## First synchronization with existing local changes

User-provided output shows a modified README and untracked project files. Preserve
them before switching to a branch that tracks files at the same paths.

Run in Windows PowerShell, from the project repository:

```powershell
git status --short
git stash push -u -m "backup local Phase 0 work before remote sync"
git status --short
```

The second status should be empty. `-u` preserves untracked, non-ignored files as
well as tracked changes. Ignored files and local Git identity are unaffected.
If the stash command fails or the status is not clean, inspect that result before
switching branches.

Then fetch and check out the shared work branch:

```powershell
git fetch origin
git switch --track origin/docs/phase-0-baseline
git status
git log -1 --oneline
git stash list
```

Use this initial switch command only if the local work branch does not yet exist.
If it exists, switch to it normally and inspect its relationship to origin.
Keep the backup stash until the checked-out files have been compared. Do not
immediately apply it over the same files, because it contains overlapping local
copies of the baseline. There is no need to delete the backup to use the branch.

## Later synchronization

Once the working tree is clean and the local branch tracks its remote branch:

```powershell
git pull --ff-only
```

If there are local edits, inspect and preserve them before updating. A rejected
fast-forward requires history inspection, not a force reset.

## 当前操作说明

后续由助手通过 GitHub 工作分支生成和修改文件，通过 PR 展示改动。
Windows 使用 Git 获取更新，不再反复下载 ZIP。当前本地 README 和未跟踪文档
先用 stash -u 备份，确认工作区干净后再获取工作分支。stash 保留，不立即 pop，
避免与远程相同路径文件产生冲突。Git 提交身份保存在本地 .git/config，不受切换影响。
