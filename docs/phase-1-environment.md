# Phase 1 Windows environment inspection

Status: Windows virtual environment and contract regression checks passed on
2026-10-23 with Python 3.12.3 and jsonschema 4.26.0 (46/46). Docker CLI is
unresolved and neither default Desktop path was found. WSL 3.0.3 installed and
VirtualMachinePlatform enabling succeeded, explicitly requiring a reboot.
Post-reboot output now reports WSL 3.0.3.0 and default version 2 without the
previous WSL2 virtualization-start error. No distributions are installed.
A running WSL2 VM/Docker engine and firmware state remain unverified.
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

## Follow-up evidence 2026-10-23

- Interpreter: repository-local .venv/Scripts/python.exe, Python 3.12.3.
- jsonschema 4.26.0 installed; all 46 contract checks passed on Windows.
- git status --short returned no output after validation: clean worktree.
- Both default Docker Desktop executable-path checks returned False; a custom
  install is not excluded. The docker command remains unresolved.
- Running wsl --version triggered an interactive WSL installation. Output reports
  WSL 3.0.3.0 and kernel 6.18.54.1-1 installed.
- VirtualMachinePlatform enabling completed successfully and explicitly reported:
  changes will not be effective until the system is rebooted.
- wsl --status, run before that required reboot, reported default version 2 and
  inability to start WSL2 due to virtualization. This cannot by itself establish
  that firmware virtualization is disabled.
- WSL1 optional-component advice is not a requirement to use the planned WSL2 path.
- A stray [O command produced an unrelated parser error.

See [Windows contract output](testing/mqtt-contract-windows-validation.txt).
The saved text is owner-supplied execution evidence, not an assistant execution
on the owner's machine. Dependency installation output is not a complete lockfile.

## Next action: reboot before changing more settings

Save open work and use Windows Start -> Power -> Restart. Do not repeatedly run
installation commands or change firmware settings before observing post-reboot
state. Microsoft troubleshooting explicitly requires restarting after enabling
Virtual Machine Platform.

After restart:

```powershell
wsl --version
wsl --status
wsl --list --verbose
```

Also inspect Task Manager -> Performance -> CPU -> Virtualization and report
Enabled or Disabled. Do not infer this value from the pre-reboot error alone.

If the error persists, collect the exact output and firmware/OS virtualization
evidence, then select a targeted fix. If a WSL distribution is not installed,
that alone is not an error for Docker Desktop: its Windows WSL2 backend does not
require a separately installed Ubuntu distribution.

Docker Desktop installation/readiness is still pending; do not count this step
as MQTT or broker runtime success.

References:
- https://learn.microsoft.com/en-us/windows/wsl/troubleshooting
- https://docs.docker.com/desktop/features/wsl/
Consulted 2026-10-23.

## Post-reboot evidence and Docker installation 2026-10-23

Owner output after reboot:
- wsl --version: WSL 3.0.3.0; kernel 6.18.54.1-1.
- wsl --status: default version 2; only the WSL1 optional-feature warning remains.
- wsl --list --verbose: no installed distributions.
- The earlier WSL2 virtualization-start error is no longer present.

This supports proceeding with Docker Desktop installation. It does not by itself
prove that a Linux VM or Docker engine can run. No separate Ubuntu installation
is required for Docker Desktop's Windows WSL2 workflow. Do not enable WSL1 merely
to suppress its warning.

1. Open https://docs.docker.com/desktop/setup/install/windows-install/ .
2. Choose the x86_64 Windows installer for this x64 environment, as evidenced by
   the Windows Python AMD64 wheel in the supplied installation log.
3. Use the default per-user installation mode where offered and the WSL2 backend.
   Keep Linux containers for this project. Restart if the installer requires it.
4. Start Docker Desktop and wait for the engine to finish starting. If settings
   expose Use WSL 2 based engine, keep it enabled; it may already be the default.
5. Open a new PowerShell terminal and run:

```powershell
docker --version
docker compose version
docker info --format '{{.OSType}}'
```

After info reports linux, run:

```powershell
docker run --rm hello-world
```

Acceptance requires CLI and Compose version output, a reachable Linux engine,
and the hello-world success message. The last command may need network access
to pull its image and removes its test container on exit. Record the exact error
if startup or pulling fails instead of reinstalling blindly.

The above are instructions, not completed installation or container results.
No simulator/MQTT implementation has started yet.
