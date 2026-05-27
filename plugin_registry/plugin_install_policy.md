# Plugin Install Policy

## Public PC Rule

No plugins are installed, downloaded, scanned, activated, or tested on a public/shared computer. This layer is documentation and dry-run harness only.

## Main Computer Rule

Real installation is allowed only on the trusted main production computer after:

- Official source URLs are reviewed.
- Dry-run scripts are run first.
- The user explicitly enables execution with `EXECUTE_INSTALL=1` or `--execute`.
- Plugin account/login requirements are understood.
- No cracked software, mirrors, torrent links, or unofficial download sites are used.

## Vocal Repair Chain Policy

The target chain order is:

1. Conservative denoise
2. Dynamic EQ
3. De-ess
4. Body restoration
5. Gentle compression
6. Parallel original vocal blend
7. Metering/QC
8. Safe preview limiting

Pitch correction tools are disabled by default because they can change vocal identity. Saturation and reverb are not denoise tools; they may restore body or space after cleanup. LoudMax is a preview/final safety limiter only, not a fix for bad mix balance. Youlean and SPAN are QC tools, not tone tools.

