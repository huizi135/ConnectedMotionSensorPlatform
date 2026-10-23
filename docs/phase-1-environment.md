# Phase 1 Windows environment inspection

Status: inspection instructions prepared; owner-machine results pending.
No simulator or broker implementation is included in this step.

## Objective

Establish which Python interpreter and Docker components are already available
before choosing versions, installing software or creating a virtual environment.
Do not require .NET or PostgreSQL yet.

## Current architecture slice

Python virtual devices -> Mosquitto -> verification subscriber.

The initial simulator publishes MQTT directly; BLE/GATT remains deferred.

## Inspect in PowerShell

From the repository root:

```powershell
$PSVersionTable.PSVersion
py --version
python --version
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

If a command is not found, retain the error and continue with the next independent
check. Do not infer that Python is absent merely because the py launcher is absent,
or that Docker is ready merely because its CLI prints a version.

## Interpretation

| Check | What it establishes |
| --- | --- |
| PowerShell version | Shell behavior, including default text decoding |
| py --version | Availability and selected interpreter of the Python launcher |
| python --version | Interpreter resolved by this command/PATH; may differ from py |
| docker --version | Docker CLI availability only |
| docker compose version | Compose plugin availability only |
| docker info reporting linux | Engine is reachable and uses Linux containers |

If Docker info fails, distinguish a stopped engine, missing installation,
permissions or other setup errors before proposing a fix. Keep actual errors
as evidence; a generic reconnect/reinstall instruction is not a diagnosis.

## Next gate

After inspecting the results, select compatible versions and configure a
repository-local .venv without changing unrelated project environments. Then
reproduce tools/validate_contracts.py on Windows. Only after the Python/Docker
checks pass, implement the smallest single-device MQTT slice.

The existing validator's author-environment Python version is evidence about
that test run, not a requirement to upgrade an already compatible Windows Python.

## Planned Phase 1 acceptance

- One device publishes structurally valid samples at a configurable rate.
- Three devices run for five minutes with independent identities and sequences.
- Fixed seeds reproduce signal values.
- Retained status, Last Will and reconnects are exercised.
- Record observed gaps and recovery time; do not promise full outage replay.
- Detector labels remain reference metadata, not detection inputs.

## 中文说明

本阶段先确认电脑现有 Python、Docker CLI、Compose 与引擎状态。
某条命令不存在时保留错误并继续其他独立检查；暂不安装、不初始化模拟器。
Docker 版本输出只能证明 CLI 存在，info 返回 linux 才表明引擎可达且
处于 Linux 容器模式。结果确认后再配置虚拟环境和运行契约校验。
