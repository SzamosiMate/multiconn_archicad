# Semantic schema review

## Sharing and naming

Sharing is semantic, not just shape matching. `Zoom` and drawing bounds can have identical coordinates but represent different concepts. A beam-hole modification payload without `holeId` differs from the identified read model; preserve its positive width/height constraints and conditional height meaning.

Use singular scalar enum names and domain-specific names for narrow concepts: `MEPDomain`, `RoofLevel`, `RoofPivotLine`. Search existing definitions. Report client compatibility alias needs for release adoption; do not edit generated models during upstream work.

Inspect SDK contracts precisely. A direct `Domain` return differs from `Result<Domain>`, which can carry an error. An `Unknown` switch default is not proof of a fourth SDK enum value or a reachable normal result. An explicit error-to-string fallback is part of Tapir's output handling. An Equipment element can lack a domain while its individual ports have domains; do not tighten an empty-string element response based on a port getter.

## Descriptions

- Put general object meaning on the shared definition, and general field behavior on that field. A creation-time flag's meaning belongs on the shared flag, not repeated on all enclosing object references.
- Keep only unique caller defaults, restrictions, effects, field-name mappings or readback expectations at referencing properties. If there is nothing distinct to add, use a plain reference.
- Split generic and contextual facts rather than copying whole descriptions. Preserve real limitations and supported-version facts; remove redundant explanations and investigation narratives. Never shorten away a default or restriction.

Inspect the actual target-branch renderer. A sibling description can be swallowed when the renderer replaces the whole reference node. Where both descriptions are supported, verify that resolving a caller does not mutate the definition or leak context to another caller. Otherwise keep necessary facts in a rendered location or identify the renderer dependency. Record full strings/locations for retained double-description cases in the single run report.

## Compatibility and evidence

Distinguish command wire behavior, schema acceptance, generated public API and published documentation. Extraction can rename a client type; enum tightening can reject input before execution; fixing `#ref` restores a previously ineffective constraint. Do not describe all of these as “no behavior change.”

Use released unpatched schemas as evidence for current client input, and interpreted current source for proposed upstream contracts. Normalize Tapir `#/Name` references to MultiConn `#/$defs/Name` for comparison, preserving siblings and annotations. A generic expander does not necessarily reproduce Archicad or renderer behavior.

Preserve `oneOf` versus `anyOf`, GUID-only versus error-union identifiers, and required versus optional variants. Similar generated Python is insufficient proof of equivalent schemas.

## Merge check

From the MultiConn checkout, pass the Tapir checkout and the already-fetched base ref. Use Python 3.12 or newer and Git with `merge-tree --write-tree` support.

```text
python .agents/skills/multiconn-upstream-patches/scripts/check_schema_merge.py --repo "<Tapir checkout>" --base upstream/main --head HEAD
```

Pass the actual fetched upstream ref or SHA if it has a different name. `--head` selects a committed proposal. Use `--scratch "<existing writable directory>"` when the system temporary directory is unavailable. The script prints the two commit IDs and synthetic merge tree. It generates both outputs with Tapir's generator and keeps the snapshots and merge objects in temporary storage. This avoids comparing stale files under `docs/archicad-addon` and leaves the checkouts and remote branches untouched.

- Exit `0` means the input and response contracts and existing shared definitions compare equal. New named definitions are allowed and their references are checked.
- Exit `1` reports structural differences by path. Review every difference, including any intended breaking correction. Match each intended change to its source evidence and report it explicitly. Do not waive a whole command when only one path was intended to change.
- Exit `2` means the check could not finish, for example because the merge conflicts, the generator fails, a JSON key is duplicated, or a reference cannot resolve. Resolve the underlying problem and rerun the check.

The comparison ignores prose annotations and handles the required-only object selectors used by Tapir. It follows references while comparing constraint siblings and recursive schemas. It checks the documentation generator's target Archicad version. Continue to review annotations, common-schema access and execution separately, and build or run live checks when the change warrants them.

### Local check and Tapir's manual workflow

Tapir's `schema_refinement.yml` calls `tools/check_schema_refinement.py`. Its structural rules currently match this skill's check: compare current base with the proposed merge, resolve references, preserve constraints and union semantics, and reject removed commands, fields, or existing definition names. Added definitions are allowed. Both use the docs generator's newest supported Archicad version.

The local script runs each revision's own documentation generator and prints structural differences. The workflow uses a trusted default-branch generator, rejects links in snapshots, runs without write credentials, and saves a JSON report that also includes annotation differences and new names. Its controller separately checks permissions, file scope, builds, reviews, draft status, and ref freshness. Those are not part of the local script's structural check.

Use the local script for reviewed source proposals. Where the upstream workflow is available, its result is the final check for that workflow; a local pass does not authorize merging or remove the API's remaining base race. Do not execute an unreviewed PR's Python through the local script.

### Parallel-batch checks

Independent branches must compose as well as pass individually. Multiple additions at the same closing brace of the common JSON file are a predictable textual conflict, even when their definition names and contracts are disjoint. Use separate existing domain anchors and preserve unrelated formatting.

Before publishing or updating a set of independent proposals:

1. Pin fetched main and each proposed committed head. Include other relevant open schema proposals when they overlap the same source locations.
2. Use temporary Git objects or an isolated checkout to trial-merge each pair in both orders and the complete set in the intended merge order. Do not alter the user's branches to conduct the test. If the result depends on order, declare and test that dependency rather than claiming independence.
3. Reject conflicts, duplicate JSON keys, unresolved references, lost definitions/references, and incompatible edits to an existing definition. Compare the combined result with the union of the reviewed changes; a textual merge alone can silently lose intended content.
4. Run the full structural comparison between pinned main and the combined candidate, in addition to the required individual proposal checks. Verify each proposal's new named contracts survive unchanged. Cache snapshots by exact source/merge tree so equivalent orderings need no additional generation. If a real dependency changes acceptance, isolate and explain its exact paths as usual.
5. Record base, heads, tested order(s) and results in the logical run's existing report. Repeat affected checks when a head or main changes. An individual pass against a common ancestor is not joint integration evidence.

In publish mode, a failing joint check blocks submission of the conflicting set until its layout or dependency is resolved. In prepare mode, resolve it locally before declaring the proposals ready. Review-only mode can report the conflict without changing source.

Parallel preparation/review does not imply parallel integration. When authorized to merge, run the final validation-and-merge actions sequentially and capture main when each proposal's turn starts. Serializing only the merge API call leaves earlier validation stale. The current workflow uses per-PR concurrency, which permits different PRs to run against the same old main; do not dispatch those merge runs together. If another merge advances main during validation, retain the freshness failure, refresh/test the remaining candidate and start a new authorized run. Do not assume that an Actions concurrency group is a durable queue for every submitted proposal.

### Claude review

After opening a draft, request review without marking it ready:

```text
gh workflow run claude_pr_review.yml -R ENZYME-APD/tapir-archicad-automation --ref main -f pr_number=1234
```

Confirm the deployed workflow permits explicit reviews of drafts. If it still skips them, report the blocked review; do not mark the PR ready as a workaround. Record the PR head and run URL, wait for that run, then read the bot's summary and findings. A successful job alone is not an approval. If the head changed during review, do not present it as reviewed. Review can run alongside ordinary build CI. If the run fails or is refused, return it as an incomplete review instead of automatically retrying.

### Manual action

After the user authorizes merging, keep the PR draft and run:

```text
gh workflow run schema_refinement.yml -R ENZYME-APD/tapir-archicad-automation --ref main -f pr=1234 -f merge=true
```

Replace `1234` with the reviewed PR number. Write access is required. The action keeps the PR draft during validation, then marks it ready and requests a merge. Failed validation leaves it draft; a later merge failure attempts to restore draft status. Results appear in PR comments and the run's `schema-report` artifact.

For a negative test or check-only run, use `merge=false`; this leaves readiness unchanged. That is optional testing, not another required preflight. The API pins the PR head but leaves a small race with a concurrent main update after the final check.

### Ordered merge queue

The queue implementation belongs in Tapir at `tools/queue_schema_refinements.py` ([helper PR #3116](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/3116)). When that helper is available in the chosen checkout, preview an explicit list from the Tapir root:

```text
python tools/queue_schema_refinements.py 3104 3105
```

After the maintainer has authorized merging those PRs, run the same list with `--merge`:

```text
python tools/queue_schema_refinements.py 3104 3105 --merge
```

The helper uses the authenticated `gh` CLI, captures each listed PR head, waits for its existing CI checks, dispatches `schema_refinement.yml` from main, and watches the exact returned run URL at a default 20-second interval. Each action must finish before the next dispatch. A changed head before dispatch moves that PR to the back of the queue with its new head; CI and the fresh schema action run again on its next turn. Main advancing between queued actions needs no retry: each new action captures fresh main. If main advances during validation, a confirmed controller freshness rejection moves that PR to the back for a new comparison. Head and stale-base changes share a default limit of three reschedules per PR. The server workflow still captures fresh main and enforces its existing validation/build/review gates. Queueing removes manual waiting; it does not shorten the schema comparison.

Use one queue at a time. Definite per-PR failures (failed CI, invalid/closed PR, exhausted reschedules, a completed failed action, or a completed action without a merged PR) remove that item, record its failure, and let the remaining items proceed. The exception is an identified stale-base rejection: require the exact freshness error from the trusted prepare/finish controller job, an unchanged PR head, and for finish failures a matching `schema-request` artifact and proof current main differs from its pinned base. Log/artifact/metadata failures or generic validation/build/conflict errors do not authorize automatic redispatch. No rebase or force-push is performed. The final summary lists failed items and the command exits nonzero if any failed.

A failed run watcher is not proof the server action finished. The helper polls that same action's status within the remaining wait budget, including retrying status-read failures. It dispatches nothing else until the action is confirmed completed. An expired wait with an active/unknown action, or an unidentified dispatch, blocks the remaining queue for inspection. Stopping the helper does not cancel a dispatched action. If an older `gh` does not return a run URL, the dispatch may still have succeeded: inspect it rather than guessing the latest run or sending a duplicate. Already-merged entries are skipped when the explicit list is resumed.

This is a one-shot local command, not a standing watcher or scheduled automation. Its existence does not authorize merges. Defaults are a read-only preview, 20-second polling, a 90-minute timeout for each CI/action wait, and three head/stale-base reschedules per PR. `--interval`, `--timeout-minutes` and `--max-reschedules` adjust these; zero reschedules removes a PR on its first candidate change. Keep the strict moved-base validation failure if another actor merges concurrently: rescheduling must run a fresh comparison, never waive the server check or reuse a stale pass.
