# Repository workflow and Windows synchronization

Updated 2026-10-23. Project files are maintained directly through GitHub branches
and commits, as requested by the owner. Pull requests are not part of this
workflow. The initial draft PR #1 was closed without merging; its branch and
commit history are preserved.

## Responsibilities

The assistant reads the latest branch, prepares focused changes, verifies them
and commits directly to the work branch. The Windows checkout receives those
commits using Git. Remote edits do not execute commands on the owner's C drive
and do not establish Windows runtime results.

The owner has verified that docs/phase-0-baseline tracks its remote at f8bfed5
and has a clean working tree. Keep any earlier backup stash until comparison;
do not automatically pop overlapping old files over the tracked baseline.

## Branches

- main: initial commit; no implicit merges.
- docs/phase-0-baseline: architecture and contract baseline.
- phase-1/virtual-sensors: Phase 1 preparation and incremental implementation.

Create the Phase 1 branch from the updated Phase 0 baseline. New work follows
the latest phase branch; there is no requirement to merge to main first.
Integrating completed phases into main is a separate step.

## First checkout of a new remote phase branch

With a clean working tree:

```powershell
git fetch origin
git switch --track origin/phase-1/virtual-sensors
git status
git log -1 --oneline
```

If that local branch already exists, switch to it normally and inspect tracking
rather than creating it again.

## Later updates

```powershell
git status --short
git pull --ff-only
```

Proceed only after checking local changes. Preserve intentional edits before
updating. If fast-forward is rejected, inspect history rather than force-resetting.

## 中文说明

后续直接创建分支、提交修改，不创建 PR。现有草稿 PR 已关闭，未合并；
分支和提交历史仍保留。Phase 0 本地同步已通过，开始 Phase 1 环境检查。
Windows 使用 Git 获取文件；助手不直接操作本机 C 盘。
已有备份 stash 先保留，不自动 pop。main 暂时维持初始提交，阶段整合另行执行。
