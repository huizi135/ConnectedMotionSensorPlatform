README portfolio review — 2026-11-12

Reference structure: huizi135/Twiggle README, blob 05864536a147b21cd4ee3f330761d79fee28f765.
ConnectedMotionSensorPlatform implementation baseline:
e347969f5e8dbf31fc66f271129da14fcc7e298c (phase-1/status-acceptance).

GitHub inspection:
- main 9c73dfb was an ancestor of the implementation branch, 18 commits behind.
- Existing source includes Python simulator/MQTT/status tooling, schemas, broker
  Compose, tests and eight ADRs. No .NET, PostgreSQL, frontend or monitoring UI.
- GitHub Actions API reports zero runs and no workflow exists in the tree.
- No LICENSE file; no license selected by this documentation change.
- No tracked secrets/ directory in the inspected tree.

Documentation change:
- Replaced project README with motivation, current features, current/target
  architecture, stack, Windows setup/demo, engineering challenges, verification,
  local security/reliability boundaries, roadmap and repository/document guide.
- Added real-time monitoring as planned work after backend/API/persistence:
  device state, live curves, diagnostics, latency interpretation and history.
- No application code, dependency versions or runtime guarantees changed.
- Existing Chinese/English HTML learning material retained.

Verification during review:
python -m unittest discover -s tests -v: 25 tests passed.
python tools/validate_contracts.py: 46/46 passed.
Environment: Python 3.12.14, paho-mqtt 2.1.0, jsonschema 4.26.0.
31 Markdown links checked against repository paths and heading anchors.
Markdown fences balanced; pending status acceptance explicitly retained.

Docker, dotnet and psql are unavailable in this review environment. No new
real-broker run, Windows run, status acceptance, backend/database build or CI run
was performed or claimed. Windows broker/message evidence remains historical.
The status lifecycle runner's real-broker acceptance is still pending.

Publication: a documentation commit is based on the implementation head.
A docs/portfolio-readme branch preserves that commit; main can advance by
non-forced fast-forward from its initial commit with no loss of history.
Existing development branches are preserved.
