Handling additionalProperties: Investigate schemas that use additionalProperties: true.

For the Official API's ExecuteAddOnCommand, this is a required feature to support dynamic parameters. The models need to be configured to allow this explicitly.

For the Tapir API, this appears to be a schema error. The plan is to fix the schema upstream and submit a pull request to the Tapir repository.

Implement a Global StrictBaseModel: To enforce strict validation (extra='forbid') consistently across all models and remove verbose ConfigDict blocks, a shared StrictBaseModel will be implemented. This is linked to the additionalProperties investigation.