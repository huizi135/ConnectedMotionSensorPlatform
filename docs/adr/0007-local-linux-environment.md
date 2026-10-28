# ADR 0007: Windows development with WSL2-backed Linux containers

Status: accepted for local MVP environment, 2026-10-28.

## Context
The owner develops on Windows. WSL and Linux Docker execution have real owner
evidence; no standalone Ubuntu distribution was installed in the latest recorded
machine inventory. Additional Linux skills are a career objective, but no physical
hardware or paid cloud is available.

## Decision
Keep the existing Windows checkout and Python/.NET host development initially.
Run infrastructure, and later backend deployments, in Linux containers under
Docker Desktop's WSL2 engine. Use Compose/runbooks to teach shell, process,
permission, environment, network, volume and diagnostic skills incrementally.
An Ubuntu LTS WSL2 distribution is optional for native Linux shell practice.
Do not install an independent VM or require a dedicated Linux host now.

## Alternatives
WSL2 Ubuntu-first development; independent Linux VM; dedicated Linux machine;
cloud-only development; Windows-native installation of every infrastructure tool.

## Costs
Docker Desktop/WSL dependencies and Windows/Linux path/permission differences.
Container execution does not establish systemd, host patching, firewall, SSH,
backup or production Linux administration proficiency. Ubuntu installation is
a separate machine change, not claimed as completed. A later clean Linux target
is needed to support reproducible deployment claims.

## Reconsider when
A deployment target requires an independent host, native Linux file performance
becomes material, Linux system-service administration is in scope, or optional
OPC UA/ROS 2 tooling benefits from a Linux development workspace. Those adapters
must not block the backend/database MVP.

Reference: https://docs.docker.com/desktop/features/wsl/
