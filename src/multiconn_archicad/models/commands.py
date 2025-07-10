from __future__ import annotations
from typing import Any, List, Literal, Union, TypeAlias
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, RootModel
from .types import *


class AddCommentToIssueParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issueId: IssueId
    author: str | None = Field(None, description="The author of the new comment.")
    status: IssueCommentStatus | None = None
    text: str = Field(..., description="Comment text to add.")


class ApplyFavoritesToElementDefaultsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    favorites: List[str] = Field(..., description="The favorites to apply.")


class ApplyFavoritesToElementDefaultsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class AttachElementsToIssueParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issueId: IssueId
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    type: IssueElementType


class ChangeSelectionOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    addElementsToSelection: List[ElementIdArrayItem] | None = Field(
        None, description="A list of elements."
    )
    removeElementsFromSelection: List[ElementIdArrayItem] | None = Field(
        None, description="A list of elements."
    )


class ChangeSelectionOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResultsOfAddToSelection: List[
        SuccessfulExecutionResult | FailedExecutionResult
    ] = Field(..., description="A list of execution results.")
    executionResultsOfRemoveFromSelection: List[
        SuccessfulExecutionResult | FailedExecutionResult
    ] = Field(..., description="A list of execution results.")


class CreateBuildingMaterialsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    buildingMaterialDataArray: List[BuildingMaterialDataArrayItem] = Field(
        ..., description="Array of data to create new Building Materials."
    )
    overwriteExisting: bool | None = Field(
        None,
        description="Overwrite the Building Material if exists with the same name. The default is false.",
    )


class CreateBuildingMaterialsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributeIds: List[AttributeIdArrayItem] = Field(
        ..., description="A list of attributes."
    )


class CreateColumnsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    columnsData: List[ColumnsDatum] = Field(
        ..., description="Array of data to create Columns."
    )


class CreateColumnsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class CreateCompositesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    compositeDataArray: List[CompositeDataArrayItem] = Field(
        ..., description="Array of data to create Composites."
    )
    overwriteExisting: bool | None = Field(
        None,
        description="Overwrite the Composite if exists with the same name. The default is false.",
    )


class CreateCompositesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributeIds: List[AttributeIdArrayItem] = Field(
        ..., description="A list of attributes."
    )


class CreateFavoritesFromElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    favoritesFromElements: List[FavoritesFromElement]


class CreateFavoritesFromElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class CreateIssueParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    name: str = Field(..., description="The name of the issue.")
    parentIssueId: IssueId | None = None
    tagText: str | None = Field(None, description="Tag text of the issue, optional.")


class CreateIssueResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issueId: IssueId


class CreateLayersParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    layerDataArray: List[LayerDataArrayItem] = Field(
        ..., description="Array of data to create new Layers."
    )
    overwriteExisting: bool | None = Field(
        None,
        description="Overwrite the Layer if exists with the same name. The default is false.",
    )


class CreateLayersResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributeIds: List[AttributeIdArrayItem] = Field(
        ..., description="A list of attributes."
    )


class CreateMeshesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    meshesData: List[MeshesDatum] = Field(
        ..., description="Array of data to create Meshes."
    )


class CreateMeshesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class CreateObjectsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    objectsData: List[ObjectsDatum] = Field(
        ..., description="Array of data to create Objects."
    )


class CreateObjectsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class CreatePolylinesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    polylinesData: List[PolylinesDatum] = Field(
        ..., description="Array of data to create Polylines."
    )


class CreatePolylinesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class CreatePropertyDefinitionsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyDefinitions: List[PropertyDefinition] = Field(
        ..., description="The parameters of the new properties."
    )


class CreatePropertyDefinitionsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyIds: List[PropertyIdOrError | ErrorItem] = Field(
        ..., description="A list of property identifiers."
    )


class CreatePropertyGroupsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyGroups: List[PropertyGroup] = Field(
        ..., description="The parameters of the new property groups."
    )


class CreatePropertyGroupsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyGroupIds: List[PropertyGroupId] = Field(
        ..., description="The identifiers of the created property groups."
    )


class CreateSlabsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    slabsData: List[SlabsDatum] = Field(
        ..., description="Array of data to create Slabs."
    )


class CreateSlabsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class CreateZonesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    zonesData: List[ZonesDatum] = Field(
        ..., description="Array of data to create Zones."
    )


class CreateZonesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class DeleteIssueParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issueId: IssueId
    acceptAllElements: bool | None = Field(
        None,
        description="Accept all creation/deletion/modification of the deleted issue. By default false.",
    )


class DeletePropertyDefinitionsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyIds: List[PropertyId] = Field(
        ..., description="The identifiers of properties to delete."
    )


class DeletePropertyDefinitionsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class DeletePropertyGroupsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyGroupIds: List[PropertyGroupId] = Field(
        ..., description="The identifiers of property groups to delete."
    )


class DeletePropertyGroupsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class DetachElementsFromIssueParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issueId: IssueId
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class ExportIssuesToBCFParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issues: List[IssueIdArrayItem] | None = Field(
        None, description="Leave it empty to export all issues."
    )
    exportPath: str = Field(
        ..., description="The os path to the bcf file, including it's name."
    )
    useExternalId: bool = Field(
        ...,
        description="Use external IFC ID or Archicad IFC ID as referenced in BCF topics.",
    )
    alignBySurveyPoint: bool = Field(
        ...,
        description="Align BCF views by Archicad Survey Point or Archicad Project Origin.",
    )


class FilterElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    filters: List[ElementFilter] | None = Field(None, min_length=1)


class FilterElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class GenerateDocumentationParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    destinationFolder: constr(min_length=1) = Field(
        ..., description="Destination folder for the generated documentation files."
    )


class Get3DBoundingBoxesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class Get3DBoundingBoxesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    boundingBoxes3D: List[BoundingBox3DOrError | ErrorItem] = Field(
        ..., description="A list of 3D bounding boxes."
    )


class GetAddOnVersionResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    version: constr(min_length=1) = Field(
        ..., description='Version number in the form of "1.1.1".'
    )


class GetAllElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    filters: List[ElementFilter] | None = Field(None, min_length=1)
    databases: List[DatabaseIdArrayItem] | None = Field(
        None, description="A list of Archicad databases."
    )


class GetAllElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    executionResultForDatabases: (
        List[SuccessfulExecutionResult | FailedExecutionResult] | None
    ) = Field(None, description="A list of execution results.")


class GetAllPropertiesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    properties: List[PropertyDetails] = Field(
        ..., description="A list of property identifiers."
    )


class GetArchicadLocationResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    archicadLocation: constr(min_length=1) = Field(
        ..., description="The location of the Archicad executable in the filesystem."
    )


class GetAttributesByTypeParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributeType: AttributeType


class GetAttributesByTypeResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributes: List[Attribute] = Field(..., description="Details of attributes.")


class GetBuildingMaterialPhysicalPropertiesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributeIds: List[AttributeIdArrayItem] = Field(
        ..., description="A list of attributes."
    )


class GetBuildingMaterialPhysicalPropertiesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    properties: List[Property] = Field(..., description="Physical properties list.")


class GetClassificationsOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    classificationSystemIds: List[ClassificationSystemIdArrayItem] = Field(
        ..., description="A list of classification system identifiers."
    )


class GetClassificationsOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elementClassifications: List[ElementClassificationOrError | ErrorItem] = Field(
        ...,
        description="The list of element classification item identifiers. Order of the ids are the same as in the input. Non-existing elements or non-existing classification systems are represented by error objects.",
    )


class GetCommentsFromIssueParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issueId: IssueId


class GetCommentsFromIssueResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    comments: List[Comment] = Field(..., description="A list of existing comments.")


class GetConnectedElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    connectedElementType: ElementType


class GetConnectedElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    connectedElements: List[ConnectedElement]


class GetCurrentRevisionChangesOfLayoutsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    layoutDatabaseIds: List[DatabaseIdArrayItem] = Field(
        ..., description="A list of Archicad databases."
    )


class GetCurrentRevisionChangesOfLayoutsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    currentRevisionChangesOfLayouts: RevisionChangesOfEntities | ErrorItem


class GetCurrentWindowTypeResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    currentWindowType: WindowType


class GetDatabaseIdFromNavigatorItemIdParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    navigatorItemIds: List[NavigatorItemIdArrayItem] = Field(
        ..., description="A list of navigator item identifiers."
    )


class GetDatabaseIdFromNavigatorItemIdResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    databases: List[DatabaseIdArrayItem] = Field(
        ..., description="A list of Archicad databases."
    )


class GetDetailsOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class GetDetailsOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    detailsOfElements: List[DetailsOfElement]


class GetDocumentRevisionsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    documentRevisions: List[DocumentRevision]


class GetElementsAttachedToIssueParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issueId: IssueId
    type: IssueElementType


class GetElementsAttachedToIssueResult(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class GetElementsByTypeParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elementType: ElementType
    filters: List[ElementFilter] | None = Field(None, min_length=1)
    databases: List[DatabaseIdArrayItem] | None = Field(
        None, description="A list of Archicad databases."
    )


class GetElementsByTypeResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    executionResultForDatabases: (
        List[SuccessfulExecutionResult | FailedExecutionResult] | None
    ) = Field(None, description="A list of execution results.")


class GetGDLParametersOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class GetGDLParametersOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    gdlParametersOfElements: List[GDLParameterList] = Field(
        ..., description="The GDL parameters of elements."
    )


class GetGeoLocationResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    projectLocation: ProjectLocation
    surveyPoint: SurveyPoint


class GetHotlinksResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    hotlinks: List[Hotlink] = Field(..., description="A list of hotlink nodes.")


class GetIssuesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    issues: List[Issue] = Field(..., description="A list of existing issues.")


class GetLibrariesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    libraries: List[Library] = Field(..., description="A list of project libraries.")


class GetModelViewOptionsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    modelViewOptions: List[ModelViewOption]


class GetProjectInfoFieldsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    fields: List[FieldModel] = Field(..., description="A list of project info fields.")


class GetProjectInfoResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    isUntitled: bool = Field(..., description="True, if the project is not saved yet.")
    isTeamwork: bool = Field(
        ..., description="True, if the project is a Teamwork (BIMcloud) project."
    )
    projectLocation: constr(min_length=1) | None = Field(
        None,
        description="The location of the project in the filesystem or a BIMcloud project reference.",
    )
    projectPath: constr(min_length=1) | None = Field(
        None,
        description="The path of the project. A filesystem path or a BIMcloud server relative path.",
    )
    projectName: constr(min_length=1) | None = Field(
        None, description="The name of the project."
    )


class GetPropertyValuesOfAttributesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributeIds: List[AttributeIdArrayItem] = Field(
        ..., description="A list of attributes."
    )
    properties: List[PropertyIdArrayItem] = Field(
        ..., description="A list of property identifiers."
    )


class GetPropertyValuesOfAttributesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyValuesForAttributes: List[PropertyValuesOrError | ErrorItem] = Field(
        ...,
        description="List of property value lists. The order of the outer list is that of the given attributes. The order of the inner lists are that of the given properties.",
    )


class GetPropertyValuesOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    properties: List[PropertyIdArrayItem] = Field(
        ..., description="A list of property identifiers."
    )


class GetPropertyValuesOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    propertyValuesForElements: List[PropertyValuesOrError | ErrorItem] = Field(
        ...,
        description="List of property value lists. The order of the outer list is that of the given elements. The order of the inner lists are that of the given properties.",
    )


class GetRevisionChangesOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class GetRevisionChangesOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    revisionChangesOfElements: RevisionChangesOfEntities | ErrorItem


class GetRevisionChangesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    revisionChanges: List[RevisionChange]


class GetRevisionIssuesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    revisionIssues: List[RevisionIssue]


class GetSelectedElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class GetStoriesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    firstStory: int = Field(..., description="First story index.")
    lastStory: int = Field(..., description="Last story index.")
    actStory: int = Field(
        ..., description="Actual (currently visible in 2D) story index."
    )
    skipNullFloor: bool = Field(
        ...,
        description="Floor indices above ground-floor level may start with 1 instead of 0.",
    )
    stories: List[Story] = Field(..., description="A list of project stories.")


class GetSubelementsOfHierarchicalElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class GetSubelementsOfHierarchicalElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    subelements: List[Subelement]


class GetView2DTransformationsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    databases: List[DatabaseIdArrayItem] | None = Field(
        None, description="A list of Archicad databases."
    )


class GetView2DTransformationsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    transformations: List[ViewTransformations | ErrorItem]


class GetViewSettingsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    navigatorItemIds: List[NavigatorItemIdArrayItem] = Field(
        ..., description="A list of navigator item identifiers."
    )


class GetViewSettingsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    viewSettings: List[ViewSettings | ErrorItem]


class HighlightElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")
    highlightedColors: List[List[int]] = Field(
        ..., description="A list of colors to highlight elements."
    )
    wireframe3D: bool | None = Field(
        None,
        description="Optional parameter. Switch non highlighted elements in the 3D window to wireframe.",
    )
    nonHighlightedColor: List[int] | None = Field(
        None,
        description="Optional parameter. Color of the non highlighted elements as an [r, g, b, a] array. Each component must be in the 0-255 range.",
        max_length=4,
        min_length=4,
    )


class ImportIssuesFromBCFParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    importPath: str = Field(
        ..., description="The os path to the bcf file, including it's name."
    )
    alignBySurveyPoint: bool = Field(
        ...,
        description="Align BCF views by Archicad Survey Point or Archicad Project Origin.",
    )


class MoveElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elementsWithMoveVectors: List[ElementsWithMoveVector] = Field(
        ..., description="The elements with move vector pairs."
    )


class MoveElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class OpenProjectParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    projectFilePath: str = Field(..., description="The target project file to open.")


class PublishPublisherSetParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    publisherSetName: constr(min_length=1) = Field(
        ..., description="The name of the publisher set."
    )
    outputPath: constr(min_length=1) | None = Field(
        None,
        description="Full local or LAN path for publishing. Optional, by default the path set in the settings of the publiser set will be used.",
    )


class ReleaseElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class ReserveElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")


class ReserveElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResult: SuccessfulExecutionResult | FailedExecutionResult = Field(
        ..., description="The result of the execution."
    )
    conflicts: List[Conflict] | None = None


class SetClassificationsOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elementClassifications: List[ElementClassification] = Field(
        ..., description="A list of element classification identifiers."
    )


class SetClassificationsOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class SetDetailsOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elementsWithDetails: List[ElementsWithDetail] = Field(
        ..., description="The elements with parameters."
    )


class SetDetailsOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class SetGDLParametersOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elementsWithGDLParameters: List[ElementsWithGDLParameter] = Field(
        ..., description="The elements with GDL parameters dictionary pairs."
    )


class SetGDLParametersOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class SetProjectInfoFieldParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    projectInfoId: constr(min_length=1) = Field(
        ..., description="The id of the project info field."
    )
    projectInfoValue: constr(min_length=1) = Field(
        ..., description="The new value of the project info field."
    )


class SetPropertyValuesOfAttributesParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    attributePropertyValues: Any


class SetPropertyValuesOfAttributesResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class SetPropertyValuesOfElementsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elementPropertyValues: List[ElementPropertyValue] = Field(
        ..., description="A list of element property values."
    )


class SetPropertyValuesOfElementsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class SetStoriesParameters(BaseModel):
    model_config = ConfigDict(
        extra="allow",
    )
    stories: List[Story] = Field(..., description="A list of project stories.")


class SetViewSettingsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    navigatorItemIdsWithViewSettings: List[NavigatorItemIdsWithViewSetting]


class SetViewSettingsResult(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    executionResults: List[SuccessfulExecutionResult | FailedExecutionResult] = Field(
        ..., description="A list of execution results."
    )


class UpdateDrawingsParameters(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
    )
    elements: List[ElementIdArrayItem] = Field(..., description="A list of elements.")