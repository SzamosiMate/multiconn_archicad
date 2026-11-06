"""Edit, save and compile query rows without connecting to Archicad."""

from multiconn_archicad.utilities.queries.editing import QueryRow, QueryRows, build_query


def main() -> None:
    height = QueryRow(
        predicate={
            "kind": "property",
            "field_id": "22222222-2222-4222-8222-222222222222",
            "test": {"kind": "number", "operator": "is greater than"},
        }
    )
    rows = QueryRows(
        rows=[
            QueryRow(open_parentheses=1, predicate={"kind": "element_type", "types": ["Wall"]}, join_next="or"),
            QueryRow(close_parentheses=1, predicate={"kind": "element_type", "types": ["Column"]}),
            height,
        ],
    )

    for issue in build_query(rows).issues:
        print(issue.location, issue.message)

    height.predicate["test"] = {"kind": "number", "operator": "is greater than", "value": 3}
    saved = rows.model_dump_json(indent=2)
    print(saved)
    restored = QueryRows.model_validate_json(saved, context={"require_schema_version": True})

    result = build_query(restored)
    assert result.query is not None, result.issues
    print(result.query.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
