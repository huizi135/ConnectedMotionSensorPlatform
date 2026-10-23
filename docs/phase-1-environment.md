# Phase 1 Windows environment inspection

Status: partial Windows inspection recorded on 2026-10-23. Both py and python
report Python 3.12.3. Docker commands are not recognized in this PowerShell
session. Installation status, WSL and Docker engine readiness remain unknown.
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

## Observed Windows results 2026-10-23

| Command | Observed result | Interpretation |
| --- | --- | --- |
| py --version | Python 3.12.3 | Launcher resolves an existing Python |
| python --version | Python 3.12.3 | Command reports the same version, not proof of identical paths |
| docker --version | CommandNotFoundException | Docker CLI not resolved in this session |
| docker compose version | CommandNotFoundException for docker | Compose readiness unknown |
| docker info | CommandNotFoundException for docker | Engine state unknown |

PowerShell version, WSL status and checkout of the Phase 1 branch have not yet
been supplied by the owner. Do not mark missing observations as passed.

## Next Python step

Synchronize the Phase 1 branch, then create a project-local virtual environment.
If .venv already exists, inspect it rather than recreating it.

```powershell
git fetch origin
git switch phase-1/virtual-sensors
git pull --ff-only
Test-Path .venv
```

If Test-Path returns False:

```powershell
py -3.12 -m venv .venv
```

Use the virtual environment interpreter directly. Activation is optional; this
avoids changing PowerShell execution policy or unrelated system configuration.

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -c "import sys; print(sys.executable)"
.\.venv\Scripts\python.exe -m pip install -r tools/requirements-contracts.txt
.\.venv\Scripts\python.exe tools/validate_contracts.py
git status --short
```

Expected: Python 3.12.3, an interpreter under this repository's .venv, 46/46
checks passed, and no tracked-file changes. If any step fails, retain its output
and resolve it before dependent steps. Local execution is currently pending.

## Docker diagnosis before installation

Inspect both documented default installation locations and WSL:

```powershell
Test-Path "C:\Program Files\Docker\Docker\Docker Desktop.exe"
Test-Path "$env:LOCALAPPDATA\Programs\DockerDesktop\Docker Desktop.exe"
wsl --version
wsl --status
Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, BuildNumber, OSArchitecture
```

These locations do not exclude a custom installation. Also check Windows
Installed apps for Docker Desktop if needed. If installed, launch Desktop,
open a new terminal and inspect PATH before reinstalling.

If not installed, choose the appropriate official Windows installer after
confirming OS/WSL prerequisites. The intended local setup uses Linux containers;
WSL 2 is the normal starting backend. Installation and possible reboots are
separate Windows actions, not something a Git commit performs.

Sources consulted 2026-10-23:
- https://docs.docker.com/desktop/setup/install/windows-install/
- https://docs.docker.com/desktop/features/wsl/

See [the bilingual environment record](Phase1_Environment_Record_ZH_EN.html).
