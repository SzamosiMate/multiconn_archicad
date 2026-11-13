# Maintainer-triggered Tapir schema validation and merge

Prepared a tooling proposal for the schema coordination work tracked in
[#2379](https://github.com/ENZYME-APD/tapir-archicad-automation/issues/2379#issuecomment-6724468082).
The user requested a synced fork and an implementation on an appropriate branch.
This run changes merge tooling rather than Tapir schemas or MultiConn models.

## Source and publication

- MultiConn target at preparation time was Tapir 2.0.0. Upstream main's working version was 2.0.1.
- Synced `SzamosiMate/tapir-archicad-automation` main from `ENZYME-APD/tapir-archicad-automation` without force.
- Upstream and fork main both resolved to `2c5491d885e1b944a8aa15bcd58f654bf39f13ef`.
- Published branch [codex/validate-schema-merge](https://github.com/SzamosiMate/tapir-archicad-automation/tree/codex/validate-schema-merge).
- Proposal tip `6beac17786c7492fe5238368f9dcc679404a89b2` was pushed and verified.
- The isolated Tapir checkout is under `tmp/tapir-part5-names`. Its old schema proposal branch was preserved.
- The user submitted the workflow proposal as [PR #2814](https://github.com/ENZYME-APD/tapir-archicad-automation/pull/2814).

## Behavior and placement

The PR description must contain `<!-- tapir-schema-refinement -->`. The PR author
can post exactly `/check-schema` on their own PR without repository write access.
People with live repository write permission can check any marked PR and are the
only users allowed to request `/merge-schema`. A fork contributor can add the
marker without repository label permissions. The marker alone does not authorize
a merge.

Progress and results appear as PR conversation comments. Success comments link
directly to the Actions run, whose `schema-report` artifact holds the full JSON
comparison. Validation, publication, and preparation failures post a stopped
message with a run link. Runs signal success/failure in Actions rather than adding
a required check to the PR commit. Misspelled commands are ignored by the trigger.

Tapir already keeps repository-wide Python tooling in `tools/` and Actions in
`.github/workflows/`, so the proposal uses those directories.

| Location | Purpose |
| --- | --- |
| `.github/workflows/schema_refinement.yml` | Command authorization, isolated validation, and publication |
| `tools/check_schema_refinement.py` | Trusted docs interpreter over source snapshots, reference checks, structural comparison, separate annotation report |
| `tools/merge_schema_refinement.py` | Live authorization and build/review gates, pinned candidate selection, GitHub PR merge |
| `.github/workflows/claude_auto_merge.yml` | Excludes marked PRs from the ordinary scheduled merge path |
| `.github/workflows/claude_pr_review.yml` | Prevents these command comments from starting a model re-review |
| `CLAUDE.md` | Usage, shared command flow, the two Python files' responsibilities, and scope |

On review, the user asked to keep tests local and simplify the explanations.
The `CLAUDE.md` entry is now ten lines, and module docstrings are five/six lines.
Long explanations were removed. An AST comparison confirmed only docstrings changed
in the last Python edit. The added Python test file and pull-request
test job were removed from the proposal. The tests are preserved outside the
Tapir checkout at `tmp/schema-refinement-local-tests/test_schema_refinement.py`.
They still pass against the two proposed helpers via `PYTHONPATH` pointing to the
Tapir checkout's `tools/` directory. Follow-up tests cover contributor check access,
maintainer-only merging, and linked result comments. The documentation cleanup
did not change comparison logic; contributor authorization and result reporting
were then updated at the user's request.

The workflow interprets candidate C++ schema data with the documentation generator
from the trusted default-branch checkout. It does not execute candidate Python.
Validation runs separately without write permission or persisted Git credentials.
The publication job rechecks authorization, refs, current-head builds, statuses,
requested changes, and unresolved human review threads. Merge holds are respected.

The workflow checks main immediately before requesting a GitHub PR merge and pins
the PR head in that request. GitHub's API does not atomically pin main: a change
between the final check and the merge can result in an unvalidated merge. A moved
head or detected base movement needs a fresh command. Replaying an old Actions
attempt is rejected. Main builds and API coverage are explicitly dispatched after
publication because the Actions token's merge does not start push workflows.

## Compatibility and limits

- Only source `.cpp`/`.hpp` files and `CommonSchemaDefinitions.json` are accepted by this path. This is a file-scope gate, not proof that every C++ edit is schema-only. Human review and native builds remain necessary.
- Existing command contracts and shared definition names must remain available. Added shared definitions are reported for naming review. No downstream naming manifest was imposed.
- Reference siblings, requiredness, constraints, enum and union order, and recursive definitions are preserved in comparison. Duplicate JSON keys and unresolved supported Tapir references fail validation. Descriptions and other annotations are reported separately, including unused shared definitions.
- The documentation generator selects the highest version in `archicad-addon/devkits.json`, currently Archicad 30. Older-version conditional schema branches are not compared. A scan found no version guards surrounding or inside schema methods, but did not trace every helper or constant.
- Native checks required for publication are the existing PR-head checks. They are not a new native build of the synthetic merge. The fresh merge comparison specifically checks schema preservation.
- No branch protection, merge queue, additional secret, or scheduled wait was introduced. GitHub manual merging can bypass this path. The workflow must first land on the upstream default branch before comment-triggered use.
- The ordinary bot's split-issue followup and branch cleanup are not replicated. This path is intended for maintainer-reviewed schema proposals.

## Validation

- All 21 standard-library offline tests passed outside the proposal. They cover author-only contributor check access, maintainer-only merging, schema comparison, moved heads, a detected main change before the API request, and the head-pinned merge request. The old local Git lease test exercises the superseded direct-push design and does not prove atomicity of the API merge.
- A full-source comparison smoke test at baseline `2c5491d8` completed for 803 commands and 1,068 existing definitions with no structural or annotation differences. The tooling proposal leaves the source schemas unchanged, confirmed by comparing the source trees after commit.
- Ruff formatting and lint checks passed for the two proposed Python files. `actionlint` passed the new workflow and both modified workflows, and passed again after removing the test job. Optional ShellCheck and Pyflakes integrations were unavailable and disabled for that invocation. YAML parsing and `git diff --check` also passed.
- Current Tapir PR API records were inspected to confirm workflow IDs, head-SHA filtering, and build-check names.
- No native build, live Archicad test, comment-triggered upstream run, or live upstream merge was performed. A maintainer trial after the infrastructure lands remains necessary.

The only MultiConn change in this run is this staged report. Unrelated work was
preserved, and no client models, release pins, or schema patch implementations were
changed.

## Focused guard test branches

At the user's request, prepared two branches from upstream main
`2c5491d885e1b944a8aa15bcd58f654bf39f13ef`, after syncing the fork without force.
The test branches are intended for use once the schema-command workflow is on
upstream's default branch. Neither pull request was opened by this run.

- `schema/refinements-2.0.0-autotext` extracts `AutoTextExpression` from
  `InterpretAutoTexts` input items and `InterpretedAutoText` from its successful
  response. Both names and their schemas match MultiConn's released 2.0.0 patches.
  The command already uses `CommonSchema::Used`; the response value description
  is retained on the extracted field. Existing accepted values are unchanged.
  Commit `5b046b18bc04a3977f225582da121f993dd9e77c` was pushed and its remote
  tip verified. The skill's full merge check compared 803 commands and 1,068
  existing definitions with zero structural differences.
- `schema/test-rejected-autotext` includes that extraction and deliberately changes
  `AutoTextExpression.minLength` from 1 to 2 and removes the optional `elementId`
  input property. It is a test-only breaking change, intended to be rejected and
  never merged. Commit `51a351c7afe04f83086a0d24839244ee2c44476a` was pushed and
  its remote tip verified. The full guard compared 803 commands and 1,068 shared
  definitions and rejected the branch, listing both the missing `elementId` and
  the `minLength: 1 -> 2` change.

Searches found no open upstream PR naming either new definition. The bad branch
is explicitly marked test-only in its commit; any test PR should also have a
prominent do-not-merge title. Neither native builds nor live Archicad tests were
run for this pair.

PR #2814's bot review identified a conflict between directly pushing to main and
Tapir's documented intent to require PR merges. Public read-only rules queries
returned no visible active rules, but the account has only pull access, so this
does not establish the intended or complete protection state. The suggested PR
merge API pins the PR head, not the base, so it does not provide the same atomic
base guarantee. A GitHub Actions `GITHUB_TOKEN` API merge also does not restore
normal push-triggered workflows. At the user's request, the PR now uses the merge
API with a final main check and openly retains the narrow base race. A maintainer
can decide whether to accept it or use a merge queue or dedicated app instead.
