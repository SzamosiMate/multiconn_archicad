from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar, Literal, Self, Union
import re
from urllib.parse import unquote
from dataclasses import dataclass

from pydantic import (
    BaseModel,
    ConfigDict,
    SecretStr,
    field_validator,
    field_serializer,
    model_validator,
    GetCoreSchemaHandler,
)
from pydantic_core import core_schema
from packaging.version import Version, InvalidVersion

from multiconn_archicad.errors import APIErrorBase
from multiconn_archicad.utilities.platform_utils import is_using_mac, double_quote, single_quote
from multiconn_archicad.constants import SUPPORTED_TAPIR_VERSION

JsonType = Union[str, int, float, bool, None, list["JsonType"], dict[str, "JsonType"]]


class Port(int):
    """Port constraint for Archicad JSON API (19723 <= port < 19744)."""

    MIN_PORT: ClassVar[int] = 19723
    MAX_PORT: ClassVar[int] = 19744

    def __new__(cls, value: int | str) -> Self:
        int_val = int(value)
        if not (cls.MIN_PORT <= int_val < cls.MAX_PORT):
            raise ValueError(f"Port value must be between {cls.MIN_PORT} and {cls.MAX_PORT}, got {int_val}.")
        return super().__new__(cls, int_val)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        return core_schema.chain_schema([
            core_schema.int_schema(ge=cls.MIN_PORT, lt=cls.MAX_PORT),
            core_schema.no_info_plain_validator_function(cls),
        ])

class HeaderInfoBase(BaseModel):
    """Base class providing common configuration and backward-compatible helper methods."""

class HeaderInfoBase(BaseModel):
    """Base class providing common configuration and backward-compatible helper methods."""

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls.model_validate(data)

    @classmethod
    def from_api_response(cls, response: dict[str, Any]) -> Self:
        return cls.model_validate(response)


class ProductInfo(HeaderInfoBase):
    version: int
    buildNumber: int
    languageCode: str


class ArchicadLocation(HeaderInfoBase):
    archicadLocation: str

    @field_validator("archicadLocation", mode="after")
    @classmethod
    def _normalize_mac_path(cls, v: str) -> str:
        if is_using_mac() and not v.endswith("/Contents/MacOS/ARCHICAD"):
            return f"{v}/Contents/MacOS/ARCHICAD"
        return v


class APIResponseError(HeaderInfoBase):
    code: int | None = None
    message: str

    @classmethod
    def from_exception(cls, exc: APIErrorBase | Exception) -> Self:
        return cls(
            code=getattr(exc, "code", None),
            message=getattr(exc, "message", str(exc)),
        )


class PendingResponse(APIResponseError):
    code: int | None = None
    message: str = "Identifying..."


class TeamworkCredentials(HeaderInfoBase):
    username: str
    password: SecretStr | None = None

    @field_serializer("password", when_used="always")
    def _serialize_password(self, password: SecretStr | None) -> None:
        return None


def get_project_type(v: Any) -> str | None:
    """Extracts discriminator tag from serialized dict or raw Tapir API response."""
    if isinstance(v, dict):
        if "project_type" in v:
            return v["project_type"]
        if "isUntitled" in v and "isTeamwork" in v:
            if v["isUntitled"]:
                return "untitled"
            if v["isTeamwork"]:
                return "teamwork"
            return "solo"
        return None
    return getattr(v, "project_type", None)


class ArchiCadID(HeaderInfoBase, ABC):
    projectName: str = "Untitled"

    @abstractmethod
    def get_project_location(self, teamwork_credentials: TeamworkCredentials | None = None) -> str | None: ...

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        if source_type.__name__ == "ArchiCadID" and "UntitledProjectID" in globals():
            return core_schema.tagged_union_schema(
                choices={
                    "untitled": handler.generate_schema(globals()["UntitledProjectID"]),
                    "solo": handler.generate_schema(globals()["SoloProjectID"]),
                    "teamwork": handler.generate_schema(globals()["TeamworkProjectID"]),
                },
                discriminator=get_project_type,
            )
        return handler(source_type)


class UntitledProjectID(ArchiCadID):
    project_type: Literal["untitled"] = "untitled"
    projectName: str = "Untitled"

    def get_project_location(self, _: TeamworkCredentials | None = None) -> None:
        return None


class SoloProjectID(ArchiCadID):
    project_type: Literal["solo"] = "solo"
    projectPath: str
    projectName: str

    def get_project_location(self, _: TeamworkCredentials | None = None) -> str:
        return self.projectPath

    def __fspath__(self) -> str:
        return self.projectPath


class TeamworkProjectID(ArchiCadID):
    project_type: Literal["teamwork"] = "teamwork"
    projectPath: str
    serverAddress: str
    teamworkCredentials: TeamworkCredentials
    projectName: str

    @model_validator(mode="before")
    @classmethod
    def _parse_project_location(cls, data: Any) -> Any:
        """Parses raw projectLocation URL into address, path, and credentials."""
        if isinstance(data, dict) and "projectLocation" in data:
            data = dict(data)
            match = cls.match_project_location(data.pop("projectLocation"))
            data.setdefault("serverAddress", match.group("serverAddress"))
            data.setdefault("projectPath", match.group("projectPath"))
            data.setdefault(
                "teamworkCredentials",
                TeamworkCredentials(
                    username=match.group("username"),
                    password=match.group("password"),
                ),
            )
        return data

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TeamworkProjectID):
            return (
                self.projectPath == other.projectPath
                and self.serverAddress == other.serverAddress
                and self.projectName == other.projectName
            )
        return False

    def get_project_location(self, teamwork_credentials: TeamworkCredentials | None = None) -> str:
        creds = teamwork_credentials or self.teamworkCredentials
        if not creds.password:
            raise ValueError("Missing password in teamwork credentials.")
        raw_password = (
            creds.password.get_secret_value()
            if isinstance(creds.password, SecretStr)
            else creds.password
        )
        return (
            f"teamwork://{single_quote(creds.username)}:{single_quote(raw_password)}@"
            f"{double_quote(self.serverAddress)}/{double_quote(self.projectPath)}"
        )

    @classmethod
    def from_project_location(cls, project_location: str, project_name: str) -> Self:
        return cls.model_validate({"projectLocation": project_location, "projectName": project_name})

    @staticmethod
    def match_project_location(project_location: str) -> re.Match[str]:
        project_location = unquote(unquote(project_location))
        pattern = re.compile(
            r"teamwork://(?P<username>[^:]+):(?P<password>[^@]+)@(?P<serverAddress>https?://[^/]+)/(?P<projectPath>.*)?"
        )
        match = pattern.match(project_location)
        if not match:
            raise ValueError(
                f"Could not recognize projectLocation format:\n({project_location})\nPlease, contact developer"
            )
        return match


ArchiCadID.model_rebuild(force=True)


@dataclass
class VersionPair:
    self: Version
    other: Version


class TapirInfo(HeaderInfoBase):
    """ Represents the Tapir Add-On state on an Archicad instance. """
    version: str | None
    is_installed: bool = False
    requiredVersion: str  = SUPPORTED_TAPIR_VERSION

    @model_validator(mode="after")
    def _infer_installed_state(self) -> Self:
        """If a version string is present, mark as installed automatically."""
        if self.version is not None:
            self.is_installed = True
        return self

    @classmethod
    def not_installed(cls) -> Self:
        """Factory method representing an Archicad instance without the Tapir add-on."""
        return cls(version=None, is_installed=False)

    @property
    def is_supported(self) -> bool:
        """Checks if Tapir is installed and meets the library's required baseline."""
        if versions:= self._ensure_version():
            return versions.self >= versions.other
        else:
            return False

    @property
    def is_newer(self) -> bool:
        """Checks if Tapir is newer than the library's required baseline."""
        if versions:= self._ensure_version():
            return versions.self > versions.other
        else:
            return False

    @property
    def is_older(self) -> bool:
        """Checks if Tapir is older than the library's required baseline."""
        if versions:= self._ensure_version():
            return versions.self < versions.other
        else:
            return False

    @property
    def is_exact_match(self) -> bool:
        """Checks if Tapir exactly matches the library's required version."""
        if versions := self._ensure_version():
            return versions.self == versions.other
        return False

    def is_at_least(self, min_version: str) -> bool:
        """Checks if Tapir is installed and at least a specific target version."""
        if versions:= self._ensure_version(min_version):
            return versions.self >= versions.other
        else:
            return False

    def __repr__(self) -> str:
        if not self.is_installed:
            return "TapirInfo(not_installed)"
        return f"TapirInfo(version={self.version!r}, supported={self.is_supported})"

    def _ensure_version(self, other: str | None = None) -> VersionPair | None:
        if not self.is_installed or self.version is None:
            return None
        other = other if other else self.requiredVersion
        if not other:
            return None
        try:
            return VersionPair(
                self=Version(self.version),
                other=Version(other)
            )
        except InvalidVersion:
            return None



