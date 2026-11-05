"""Validate and evaluate classification queries offline using one shared context."""

from uuid import UUID

from multiconn_archicad.models.official import types as official
from multiconn_archicad.utilities import BatchGrid
from multiconn_archicad.utilities.queries import (
    CLASSIFICATION_FIELDS,
    CLASSIFICATION_VALUES,
    ClassificationCatalogue,
    ClassificationInfo,
    ClassificationOperator,
    ClassificationPredicate,
    ClassificationTest,
    ColumnData,
    EvaluationContext,
    Query,
    validate_query,
)


def main() -> None:
    system_id, root_id, child_id = (UUID(int=i) for i in range(1, 4))
    system = official.ClassificationSystem.model_validate(
        {
            "classificationSystemId": {"guid": system_id},
            "name": "Example",
            "description": "",
            "source": "Example",
            "version": "1",
            "date": "2026-11-01",
        }
    )
    tree = [
        official.ClassificationItemArrayItem.model_validate(
            {
                "classificationItem": {
                    "classificationItemId": {"guid": root_id},
                    "id": "Construction",
                    "name": "",
                    "description": "",
                    "children": [
                        {
                            "classificationItem": {
                                "classificationItemId": {"guid": child_id},
                                "id": "Wall",
                                "name": "",
                                "description": "",
                            }
                        }
                    ],
                }
            }
        )
    ]
    field = ClassificationInfo(system, tree)
    catalogue = ClassificationCatalogue([field])
    elements = [UUID(int=i) for i in range(10, 13)]
    assignments = BatchGrid[UUID | None].from_rows([[root_id], [child_id], [None]], width=1)
    context = EvaluationContext(
        {
            CLASSIFICATION_FIELDS: {system_id: field},
            CLASSIFICATION_VALUES: {
                system_id: ColumnData(assignments, {guid: i for i, guid in enumerate(elements)}, 0)
            },
        }
    )
    for test in (
        ClassificationTest(operator=ClassificationOperator.IS_IN_BRANCH_OF, value=root_id),
        ClassificationTest(operator=ClassificationOperator.HAS_NO_VALUE),
        ClassificationTest(operator=ClassificationOperator.IS_NOT_DIRECT_CHILD_OF, value=root_id),
    ):
        query = Query(where=ClassificationPredicate(field_id=system_id, test=test))
        validate_query(query, [catalogue]).raise_for_errors()
        serialized = query.model_dump_json()
        assert Query.model_validate_json(serialized, context={"require_schema_version": True}) == query
        print(serialized)
        print([query.where.evaluate(context, guid).value for guid in elements])


if __name__ == "__main__":
    main()
