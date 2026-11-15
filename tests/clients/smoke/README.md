# Request compatibility smoke tests

These are representative tests of the generated client's default-serialization
contract. The SI flag is one real example, rather than the suite's subject.
All transport is mocked; the tests do not contact Archicad or modify a project.

Run the suite with the project environment:

```console
python -m pytest tests/clients/smoke -m smoke -q -p no:cacheprovider
```

The [implementation plan](../../../code_generation/documentation/optional-default-serialization-plan.md)
is pending on branch `codex/optional-default-compatibility`, created from
`extensible-elmement-query` at `9e4de6f`. The initial smoke baseline is **5 passed,
10 failed** across 15 cases. The failing assertions deliberately expose the
current default-forwarding behavior; they are not skipped or marked xfail.

| Representative shape | Why it differs |
| --- | --- |
| New top-level flag defaulted to false | Reproduces old-server incompatibility; omitted, None, default and nondefault calls are distinguished |
| Existing utility calling the generated client | Covers the utility boundary and version-dependent availability forwarding |
| True Boolean and string defaults | Prevents a fix limited to false values; preserves a nondefault false |
| Nested defaulted field from a dictionary/model | Ensures the policy applies recursively after Pydantic validation |
| Required Literal tags inside an Official request list | Prevents an indiscriminate default-exclusion fix from producing an invalid request; also covers the other provider |

The older-schema fixture is a self-contained extraction of Tapir 1.7.3's property
read input and reachable common definitions. Its reference paths are normalized;
it requires neither Git tags nor a running server during tests. It independently
checks the contract demonstrated by the [live experiment](../../../code_generation/documentation/reports/codegen/archicad-extra-fields-2026-11-15.md).

Detailed serializer edge cases (aliases, include/exclude, Boolean Literal tags,
JSON/TypeAdapter routes and mixins) belong to the focused implementation tests
specified in the plan, rather than expanding this representative smoke suite.
