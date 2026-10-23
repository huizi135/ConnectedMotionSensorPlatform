# Phase 0 acceptance record

Date: 2026-10-23. Evidence: owner-provided Windows PowerShell output and
previously recorded author-side checks.

| Area | Evidence | Result |
| --- | --- | --- |
| Git installation | 2.41.0.windows.3 and executable path | Passed |
| Repository identity | Name/email originate from .git/config | Passed |
| Configuration | Files exist; ignore rules and LF attributes checked | Passed |
| README | Formatting repaired, diff whitespace check clean, UTF-8 read correct | Passed |
| Architecture and ADRs | Tracked in the shared baseline | Prepared |
| Contracts | Two schemas, three examples and regression vectors tracked | Prepared |
| Author-side contract validation | Python 3.12.14, jsonschema 4.26.0, 46/46 | Passed in author environment |
| Windows synchronization | docs/phase-0-baseline, f8bfed5, origin tracking, clean worktree | Passed |
| Workflow | Owner requests direct branches and commits; no PRs | Recorded |
| Windows contract execution | Not run | Phase 1 task |
| MQTT, simulator, backend and database | Not implemented or runtime-tested | Later phases |

The Phase 0 design/repository baseline is accepted for incremental Phase 1 work.
This is not evidence of runtime readiness, durable message delivery or hardware
accuracy. Environment inspection is the next gate before installation and coding.

## 中文记录

用户输出确认本地处于 docs/phase-0-baseline，提交 f8bfed5，跟踪远程且
工作区干净。Phase 0 设计与仓库基线通过；下一步检查 Python 和 Docker。
未运行的 Windows 契约校验、MQTT 和后端测试仍明确保留为待执行。
不把生成设计文件、读取报告或同步提交当成运行验证。
