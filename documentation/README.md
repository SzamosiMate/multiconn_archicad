# Documentation

Start with the [repository README](../README.md) for installation, connection
management, and the `unified`, `core`, and `standard` API namespaces. These pages
describe the code in this checkout; check that your installed package contains
the features you intend to use.

## Using the library

| I want to… | Read |
| --- | --- |
| Find elements or filter an existing population | [Element queries](utilities/element_queries.md) |
| Look up query operators, validation, scope, or error behavior | [Query reference](utilities/element_query_reference.md) |
| Discover classification systems or read assignments | [Classification utilities](utilities/classifications.md) |
| Combine property reads/writes, matching, and result reporting | [Utility usage patterns](utilities/usage_patterns.md) |

The query guide starts with a complete search and links to executable offline
examples. Element-query discovery and execution require Tapir **2.0.0 or newer**;
other utilities can have different requirements.

## Integrating and maintaining the library

| I want to… | Read |
| --- | --- |
| Build a query editor or integrate field descriptors and editable rows | [Query editing and field integration](utilities/element_query_editing.md) |
| Understand utility design conventions, result containers, and contribution boundaries | [Utility architecture](utilities/architecture.md) |
| Continue engine work or review deferred decisions and live findings | [Query development plan](development/element_queries_plan.md) |

User guides and references describe current behavior. The development plan
records future work and investigation; an entry there is not a supported feature.

## Other material

The [Windows dialog-handler workbook](dialog_handlers/win_int_handler_factory.xlsx)
supports the dialog-handling feature described in the repository README.
