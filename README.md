# NightRecon candidate validation

Manual validation infrastructure for an immutable, uncommitted NightRecon controller candidate. This repository does not contain the candidate implementation and does not commit, push, merge or release NightRecon source.

## Owner bootstrap

Review and merge the bootstrap PR before running the workflow. In Actions, select **NightRecon immutable candidate Windows validation**, then **Run workflow**. Only the `kostekdolata` actor and manual dispatch are accepted. No schedules or PR-triggered candidate execution are enabled.

The owner must first upload the frozen candidate ZIP as an unreferenced Git blob in `kostekdolata/NightRecon` using the prepared `candidate-upload.json`:

```sh
gh api --method POST repos/kostekdolata/NightRecon/git/blobs --input candidate-upload.json --jq .sha
```

Use the returned blob SHA and these exact dispatch values:

- `archive_sha256`: `db95a1dc17fc562fd2d14405bfbd19c596338c17f0589d122052dbefbeb03c91`
- `manifest_sha256`: `1dc8c83fa0c3b23222e8a6611d18c76903287bfb8955aa13ae09f4bb9050f5ce`
- `candidate_digest`: `bf9104128f5f52431a564a49e4e19e1bef463df7268bb6ee0a8255d294e2a4e0`

Do not substitute the outer handoff ZIP: the blob must contain the inner `candidate.zip`. The public blob download sends no credentials. The SHA-256 pins are checked before extraction or execution. Use a reviewed infrastructure revision; do not accept new checksums from candidate output.

## Validation

Nine Windows jobs and eight Linux jobs cover Python 3.11/3.14 full suites, Red distribution and lifecycle, White distribution, and the Python 3.11 installer lifecycle. Main jobs require 1,580 total tests, including 112 controller tests; exact platform skips are recorded separately. Every role checks source integrity before and after execution, syntax and dependencies. Reports are uploaded as validation evidence. Installer artifacts are not published.

The workflow has read-only repository permissions, disables persisted checkout credentials, and uses GitHub-hosted disposable Windows and Ubuntu runners. Do not add publishing secrets or run against external security targets. Repository administrators must enable Actions if disabled by account policy. Standard action versions follow existing NightRecon CI; review dependency trust before dispatch.

## Completion gate

A workflow installation or green bootstrap review is not candidate validation. Only actual successful reports from all nine jobs, with matching candidate digests, satisfy the Windows checkpoint. Missing reports, unexpected skips, source changes and failed jobs block the checkpoint. Any source repair requires a new frozen candidate and complete Linux/Windows revalidation.

Linux distribution and lifecycle checks require the sudo-capable Ubuntu runner used by project CI. The local Codex environment has no sudo; do not bypass privilege checks. Both OS families use the same unchanged frozen candidate, hash checks and manual dispatch inputs.
