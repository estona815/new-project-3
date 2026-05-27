# Main Computer Execution Flow

Use only on the trusted production machine.

1. Clone repo.
2. Run safety check.
3. Confirm local production machine environment.
4. Back up REAPER resource folder.
5. Dry-run install scripts.
6. Install approved tools only.
7. Scan plugins in REAPER.
8. Run dummy fixture.
9. Prepare real `local_only/` audio folder.
10. Process real Suno vocal candidates.
11. Generate QC report.
12. Export final only after candidate decision approval.

Required environment for real installation or fixture execution:

```bash
LOCAL_PRODUCTION_MACHINE=1
EXECUTE_INSTALL=1
```

Real execution also requires an explicit `--execute` flag.

