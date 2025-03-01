from dataclasses import dataclass, asdict
from typing import Self, Protocol, Type, Any, TypeVar, Union, ClassVar
import re
from urllib.parse import unquote
from abc import ABC, abstractmethod

from multi_conn_ac.utilities.platform_utils import is_using_mac, double_quote, single_quote

JsonType = Union[str, int, float, bool, None, list["JsonType"], dict[str, "JsonType"]]


class Port(int):
    def __new__(cls, value):
        if not (19723 <= value <= 19744):
            raise ValueError(f"Port value must be between 19723 and 19744, got {value}.")
        return int.__new__(cls, value)


class FromAPIResponse(Protocol):
    @classmethod
    def from_api_response(cls, response: dict) -> Self: ...


@dataclass
class BaseModel:
    """Base class providing common functionality for data models"""

    def to_dict(self) -> dict[str, JsonType]:
        """Convert the instance to a dictionary suitable for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create an instance from a dictionary."""
        return cls(**data)


@dataclass
class ProductInfo(BaseModel):
    version: int
    build: int
    lang: str

    @classmethod
    def from_api_response(cls, response: dict) -> Self:
        return cls(
            response["result"]["version"],
            response["result"]["buildNumber"],
            response["result"]["languageCode"],
        )


@dataclass
class ArchicadLocation(BaseModel):
    archicadLocation: str

    @classmethod
    def from_api_response(cls, response: dict) -> Self:
        location = response["result"]["addOnCommandResponse"]["archicadLocation"]
        return cls(f"{location}/Contents/MacOS/ARCHICAD" if is_using_mac() else location)


@dataclass
class APIResponseError(BaseModel):
    code: int
    message: str

    @classmethod
    def from_api_response(cls, response: dict) -> Self:
        return cls(
            code=response["error"]["code"],
            message=response["error"]["message"],
        )


@dataclass
class TeamworkCredentials(BaseModel):
    username: str
    password: str | None

    def __repr__(self) -> str:
        attrs = vars(self).copy()
        attrs["password"] = "*" * len(self.password) if self.password else None
        str_repr = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
        return f"{self.__class__.__name__}({str_repr})"

    def __str__(self) -> str:
        return self.__repr__()

    def to_dict(self) -> dict[str, JsonType]:
        return self.__dict__.copy() | {"password": None}


class ArchiCadID(ABC):
    _ID_type_registry: dict[str, Type[Self]] = {}
    projectName: str = "Untitled"

    @classmethod
    def register_subclass(cls, subclass: Type[Self]) -> Type[Self]:
        cls._ID_type_registry[subclass.__name__] = subclass
        return subclass

    @classmethod
    def from_api_response(cls, response: dict) -> Self:
        addon_command_response = response["result"]["addOnCommandResponse"]
        if addon_command_response["isUntitled"]:
            return cls._ID_type_registry["UntitledProjectID"]()
        elif not addon_command_response["isTeamwork"]:
            return cls._ID_type_registry["SoloProjectID"](
                projectPath=addon_command_response["projectPath"],
                projectName=addon_command_response["projectName"],
            )
        else:
            return cls._ID_type_registry["TeamworkProjectID"].from_project_location(
                project_location=addon_command_response["projectLocation"],
                project_name=addon_command_response["projectName"],
            )

    @abstractmethod
    def to_dict(self) -> dict[str, JsonType]: ...

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        for id_type in cls._ID_type_registry.values():
            try:
                return id_type.from_dict(data)
            except (KeyError, AttributeError, TypeError):
                pass
        raise AttributeError(f"can not instantiate ArchiCadID from {data}")

    @abstractmethod
    def get_project_location(self, _: TeamworkCredentials | None = None) -> str | None: ...


@ArchiCadID.register_subclass
@dataclass
class UntitledProjectID(BaseModel, ArchiCadID):
    projectName: str = "Untitled"

    def get_project_location(self, _: TeamworkCredentials | None = None) -> None:
        return None


@ArchiCadID.register_subclass
@dataclass
class SoloProjectID(BaseModel, ArchiCadID):
    projectPath: str
    projectName: str

    def get_project_location(self, _: TeamworkCredentials | None = None) -> str:
        return self.projectPath


@ArchiCadID.register_subclass
@dataclass
class TeamworkProjectID(BaseModel, ArchiCadID):
    projectPath: str
    serverAddress: str
    teamworkCredentials: TeamworkCredentials
    projectName: str

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TeamworkProjectID):
            if (
                self.projectPath == other.projectPath
                and self.serverAddress == other.serverAddress
                and self.projectName == other.projectName
            ):
                return True
        return False

    def get_project_location(self, teamwork_credentials: TeamworkCredentials | None = None) -> str:
        teamwork_credentials = teamwork_credentials if teamwork_credentials else self.teamworkCredentials
        if not teamwork_credentials.password:
            raise ValueError("Missing password in teamwork credentials.")
        else:
            return (
                f"teamwork://{single_quote(teamwork_credentials.username)}:{single_quote(teamwork_credentials.password)}@"
                f"{double_quote(self.serverAddress)}/{double_quote(self.projectPath)}"
            )

    @classmethod
    def from_project_location(cls, project_location: str, project_name: str) -> Self:
        match = cls.match_project_location(project_location)
        return cls(
            serverAddress=match.group("serverAddress"),
            projectPath=match.group("projectPath"),
            teamworkCredentials=TeamworkCredentials(
                username=match.group("username"),
                password=match.group("password"),
            ),
            projectName=project_name,
        )

    @staticmethod
    def match_project_location(project_location: str) -> re.Match:
        project_location = unquote(unquote(project_location))
        pattern = re.compile(
            r"teamwork://(?P<username>[^:]+):(?P<password>[^@]+)@(?P<serverAddress>https?://[^/]+)/(?P<projectPath>.*)?"
        )
        match = pattern.match(project_location)
        if not match:
            raise ValueError(
                f"Could not recognize projectLocation format:/n({project_location})/n Please, contact developer"
            )
        return match

    def to_dict(self) -> dict[str, JsonType]:
        return asdict(self) | {"teamworkCredentials": self.teamworkCredentials.to_dict()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(**data | {"teamworkCredentials": TeamworkCredentials.from_dict(data["teamworkCredentials"])})


T = TypeVar("T", bound=FromAPIResponse)


async def create_object_or_error_from_response(result: dict, class_to_create: Type[T]) -> T | APIResponseError:
    if result["succeeded"]:
        return class_to_create.from_api_response(result)
    else:
        return APIResponseError.from_api_response(result)
