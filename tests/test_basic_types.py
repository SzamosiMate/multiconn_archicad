import pytest
from unittest.mock import patch, MagicMock
from dataclasses import dataclass, asdict

from multiconn_archicad import ArchiCadID, UntitledProjectID, TeamworkCredentials, SoloProjectID, ProductInfo, Port, TeamworkProjectID, APIResponseError, ArchicadLocation


# Setup for common fixtures

@pytest.fixture
def reset_archicad_id_registry():
    """Reset the ArchiCadID registry before and after each test."""
    original_registry = ArchiCadID._ID_type_registry.copy()
    ArchiCadID._ID_type_registry = {
        "UntitledProjectID": UntitledProjectID,
        "SoloProjectID": SoloProjectID,
        "TeamworkProjectID": TeamworkProjectID
    }
    yield
    ArchiCadID._ID_type_registry = original_registry


@pytest.fixture
def teamwork_credentials():
    """Create sample TeamworkCredentials."""
    return TeamworkCredentials(username="user", password="secret")


@pytest.fixture
def teamwork_project_id(teamwork_credentials):
    """Create sample TeamworkProjectID."""
    return TeamworkProjectID(
        projectPath="projects/myproject",
        serverAddress="https://teamwork.example.com",
        teamworkCredentials=teamwork_credentials,
        projectName="MyTeamworkProject"
    )


# Tests for Port class

def test_valid_port():
    valid_port = 19730
    port = Port(valid_port)
    assert port == valid_port
    assert isinstance(port, Port)
    assert isinstance(port, int)


def test_invalid_port_too_low():
    invalid_port = 19722
    with pytest.raises(ValueError, match="Port value must be between 19723 and 19744"):
        Port(invalid_port)


def test_invalid_port_too_high():
    invalid_port = 19745
    with pytest.raises(ValueError, match="Port value must be between 19723 and 19744"):
        Port(invalid_port)


# Tests for ProductInfo class

def test_product_info_from_api_response():
    api_response = {
            "version": 26,
            "buildNumber": 3001,
            "languageCode": "en"
    }
    product_info = ProductInfo.from_api_response(api_response)
    assert product_info.version == 26
    assert product_info.build == 3001
    assert product_info.lang == "en"


def test_product_info_to_dict():
    product_info = ProductInfo(version=26, build=3001, lang="en")
    expected_dict = {"version": 26, "build": 3001, "lang": "en"}
    assert product_info.to_dict() == expected_dict


def test_product_info_from_dict():
    data_dict = {"version": 26, "build": 3001, "lang": "en"}
    product_info = ProductInfo.from_dict(data_dict)
    assert product_info.version == 26
    assert product_info.build == 3001
    assert product_info.lang == "en"


# Tests for TeamworkCredentials class

def test_teamwork_credentials_repr_with_password():
    credentials = TeamworkCredentials(username="user", password="secret")
    repr_str = repr(credentials)
    assert "username='user'" in repr_str
    assert "password='******'" in repr_str
    assert "password='secret'" not in repr_str


def test_teamwork_credentials_repr_without_password():
    credentials = TeamworkCredentials(username="user", password=None)
    repr_str = repr(credentials)
    assert "username='user'" in repr_str
    assert "password=None" in repr_str


def test_teamwork_credentials_to_dict():
    credentials = TeamworkCredentials(username="user", password="secret")
    expected_dict = {"username": "user", "password": None}
    assert credentials.to_dict() == expected_dict


def test_teamwork_credentials_from_dict():
    data_dict = {"username": "user", "password": "secret"}
    credentials = TeamworkCredentials.from_dict(data_dict)
    assert credentials.username == "user"
    assert credentials.password == "secret"


# Tests for UntitledProjectID class

def test_untitled_project_id_default_project_name():
    project_id = UntitledProjectID()
    assert project_id.projectName == "Untitled"


def test_untitled_project_id_get_project_location():
    project_id = UntitledProjectID()
    assert project_id.get_project_location() is None


def test_untitled_project_id_to_dict():
    project_id = UntitledProjectID()
    expected_dict = {"projectName": "Untitled"}
    assert project_id.to_dict() == expected_dict


def test_untitled_project_id_from_dict():
    data_dict = {"projectName": "Untitled"}
    project_id = UntitledProjectID.from_dict(data_dict)
    assert project_id.projectName == "Untitled"


# Tests for SoloProjectID class

def test_solo_project_id_constructor():
    project_id = SoloProjectID(projectPath="C:\\python\\tests\\TestProject03.pla", projectName="MyProject")
    assert project_id.projectPath == "C:\\python\\tests\\TestProject03.pla"
    assert project_id.projectName == "MyProject"


def test_solo_project_id_get_project_location():
    project_id = SoloProjectID(projectPath="C:\\python\\tests\\TestProject03.pla", projectName="MyProject")
    assert project_id.get_project_location() == "C:\\python\\tests\\TestProject03.pla"


def test_solo_project_id_to_dict():
    project_id = SoloProjectID(projectPath="C:\\python\\tests\\TestProject03.pla", projectName="MyProject")
    expected_dict = {"projectPath": "C:\\python\\tests\\TestProject03.pla", "projectName": "MyProject"}
    assert project_id.to_dict() == expected_dict


def test_solo_project_id_from_dict():
    data_dict = {"projectPath": "C:\\python\\tests\\TestProject03.pla", "projectName": "MyProject"}
    project_id = SoloProjectID.from_dict(data_dict)
    assert project_id.projectPath == "C:\\python\\tests\\TestProject03.pla"
    assert project_id.projectName == "MyProject"


# Tests for TeamworkProjectID class

def test_teamwork_project_id_constructor(teamwork_credentials):
    project_id = TeamworkProjectID(
        projectPath="projects/myproject",
        serverAddress="https://teamwork.example.com",
        teamworkCredentials=teamwork_credentials,
        projectName="MyTeamworkProject"
    )
    assert project_id.projectPath == "projects/myproject"
    assert project_id.serverAddress == "https://teamwork.example.com"
    assert project_id.teamworkCredentials == teamwork_credentials
    assert project_id.projectName == "MyTeamworkProject"


def test_teamwork_project_id_eq_same_project(teamwork_credentials):
    project_id1 = TeamworkProjectID(
        projectPath="projects/myproject",
        serverAddress="https://teamwork.example.com",
        teamworkCredentials=teamwork_credentials,
        projectName="MyTeamworkProject"
    )
    project_id2 = TeamworkProjectID(
        projectPath="projects/myproject",
        serverAddress="https://teamwork.example.com",
        teamworkCredentials=TeamworkCredentials(username="different", password="different"),
        projectName="MyTeamworkProject"
    )
    assert project_id1 == project_id2


@pytest.mark.parametrize("different_attr, different_value", [
    ("projectPath", "projects/different"),
    ("serverAddress", "https://different.example.com"),
    ("projectName", "DifferentName")
])
def test_teamwork_project_id_eq_different_project(teamwork_credentials, different_attr, different_value):
    project_id1 = TeamworkProjectID(
        projectPath="projects/myproject",
        serverAddress="https://teamwork.example.com",
        teamworkCredentials=teamwork_credentials,
        projectName="MyTeamworkProject"
    )

    # Create a dictionary with the base values
    project_id2_args = {
        "projectPath": "projects/myproject",
        "serverAddress": "https://teamwork.example.com",
        "teamworkCredentials": teamwork_credentials,
        "projectName": "MyTeamworkProject"
    }
    # Update the attribute that should be different
    project_id2_args[different_attr] = different_value

    project_id2 = TeamworkProjectID(**project_id2_args)

    assert project_id1 != project_id2


def test_teamwork_project_id_eq_different_type(teamwork_project_id):
    other_object = "not a TeamworkProjectID"
    assert teamwork_project_id != other_object


def test_teamwork_project_id_get_project_location(teamwork_project_id):
    with patch('multiconn_archicad.basic_types.single_quote') as mock_single_quote, \
            patch('multiconn_archicad.basic_types.double_quote') as mock_double_quote:
        mock_single_quote.side_effect = lambda s: f"single_quoted_{s}"
        mock_double_quote.side_effect = lambda s: f"double_quoted_{s}"

        expected_location = (
            "teamwork://single_quoted_user:single_quoted_secret@"
            "double_quoted_https://teamwork.example.com/double_quoted_projects/myproject"
        )
        assert teamwork_project_id.get_project_location() == expected_location


def test_teamwork_project_id_get_project_location_with_provided_credentials(teamwork_project_id):
    new_credentials = TeamworkCredentials(username="new_user", password="new_secret")

    with patch('multiconn_archicad.basic_types.single_quote') as mock_single_quote, \
            patch('multiconn_archicad.basic_types.double_quote') as mock_double_quote:
        mock_single_quote.side_effect = lambda s: f"single_quoted_{s}"
        mock_double_quote.side_effect = lambda s: f"double_quoted_{s}"

        expected_location = (
            "teamwork://single_quoted_new_user:single_quoted_new_secret@"
            "double_quoted_https://teamwork.example.com/double_quoted_projects/myproject"
        )
        assert teamwork_project_id.get_project_location(new_credentials) == expected_location


def test_teamwork_project_id_get_project_location_without_password():
    credentials_without_password = TeamworkCredentials(username="user", password=None)
    project_id = TeamworkProjectID(
        projectPath="projects/myproject",
        serverAddress="https://teamwork.example.com",
        teamworkCredentials=credentials_without_password,
        projectName="MyTeamworkProject"
    )

    with pytest.raises(ValueError, match="Missing password in teamwork credentials"):
        project_id.get_project_location()


def test_teamwork_project_id_from_project_location():
    with patch('multiconn_archicad.basic_types.TeamworkProjectID.match_project_location') as mock_match_project_location:
        mock_match = MagicMock()
        mock_match.group.side_effect = lambda key: {
            "serverAddress": "https://teamwork.example.com",
            "projectPath": "projects/myproject",
            "username": "user",
            "password": "secret"
        }[key]
        mock_match_project_location.return_value = mock_match

        project_id = TeamworkProjectID.from_project_location(
            project_location="teamwork://user:secret@https://teamwork.example.com/projects/myproject",
            project_name="MyTeamworkProject"
        )

        assert project_id.serverAddress == "https://teamwork.example.com"
        assert project_id.projectPath == "projects/myproject"
        assert project_id.projectName == "MyTeamworkProject"
        assert project_id.teamworkCredentials.username == "user"
        assert project_id.teamworkCredentials.password == "secret"


def test_teamwork_project_id_match_project_location_valid():
    location = "teamwork://user:secret@https://teamwork.example.com/projects/myproject"
    match = TeamworkProjectID.match_project_location(location)

    assert match.group("serverAddress") == "https://teamwork.example.com"
    assert match.group("projectPath") == "projects/myproject"
    assert match.group("username") == "user"
    assert match.group("password") == "secret"


def test_teamwork_project_id_match_project_location_invalid():
    invalid_location = "invalid://format"

    with pytest.raises(ValueError, match="Could not recognize projectLocation format"):
        TeamworkProjectID.match_project_location(invalid_location)


def test_teamwork_project_id_to_dict(teamwork_project_id):
    expected_dict = {
        "projectPath": "projects/myproject",
        "serverAddress": "https://teamwork.example.com",
        "teamworkCredentials": {"username": "user", "password": None},
        "projectName": "MyTeamworkProject"
    }
    assert teamwork_project_id.to_dict() == expected_dict


def test_teamwork_project_id_from_dict():
    data_dict = {
        "projectPath": "projects/myproject",
        "serverAddress": "https://teamwork.example.com",
        "teamworkCredentials": {"username": "user", "password": "secret"},
        "projectName": "MyTeamworkProject"
    }
    project_id = TeamworkProjectID.from_dict(data_dict)

    assert project_id.projectPath == "projects/myproject"
    assert project_id.serverAddress == "https://teamwork.example.com"
    assert project_id.projectName == "MyTeamworkProject"
    assert project_id.teamworkCredentials.username == "user"
    assert project_id.teamworkCredentials.password == "secret"


# Tests for ArchicadLocation class

@pytest.mark.parametrize("is_mac,expected_suffix", [
    (True, "/Contents/MacOS/ARCHICAD"),
    (False, "")
])
def test_archicad_location_from_api_response(is_mac, expected_suffix):
    with patch('multiconn_archicad.basic_types.is_using_mac', return_value=is_mac):
        api_response = {
                "archicadLocation": "/Applications/ARCHICAD"
        }
        location = ArchicadLocation.from_api_response(api_response)

        assert location.archicadLocation == f"/Applications/ARCHICAD{expected_suffix}"


def test_archicad_location_to_dict():
    location = ArchicadLocation(archicadLocation="/path/to/archicad")
    expected_dict = {"archicadLocation": "/path/to/archicad"}
    assert location.to_dict() == expected_dict


def test_archicad_location_from_dict():
    data_dict = {"archicadLocation": "/path/to/archicad"}
    location = ArchicadLocation.from_dict(data_dict)
    assert location.archicadLocation == "/path/to/archicad"


# Tests for APIResponseError class

def test_api_response_error_from_api_response():
    api_response = {
            "code": 404,
            "message": "Resource not found"
    }
    error = APIResponseError.from_api_response(api_response)
    assert error.code == 404
    assert error.message == "Resource not found"


def test_api_response_error_to_dict():
    error = APIResponseError(code=404, message="Resource not found")
    expected_dict = {"code": 404, "message": "Resource not found"}
    assert error.to_dict() == expected_dict


def test_api_response_error_from_dict():
    data_dict = {"code": 404, "message": "Resource not found"}
    error = APIResponseError.from_dict(data_dict)
    assert error.code == 404
    assert error.message == "Resource not found"


# Tests for ArchiCadID class

def test_archicad_id_register_subclass(reset_archicad_id_registry):
    # Define a new subclass
    @dataclass
    class TestSubclass(ArchiCadID):
        test_attr: str

        def get_project_location(self, _=None):
            return self.test_attr

        def to_dict(self):
            return asdict(self)

        @classmethod
        def from_dict(cls, data):
            return cls(**data)

    # Register it
    ArchiCadID.register_subclass(TestSubclass)

    # Verify it's in the registry
    assert "TestSubclass" in ArchiCadID._ID_type_registry
    assert ArchiCadID._ID_type_registry["TestSubclass"] == TestSubclass


def test_archicad_id_from_api_response_untitled(reset_archicad_id_registry):
    api_response = {
            "isUntitled": True,
            "isTeamwork": False
    }
    project_id = ArchiCadID.from_api_response(api_response)
    assert isinstance(project_id, UntitledProjectID)


def test_archicad_id_from_api_response_solo(reset_archicad_id_registry):
    api_response = {
            "isUntitled": False,
            "isTeamwork": False,
            "projectPath": "/path/to/project",
            "projectName": "MySoloProject"
    }
    project_id = ArchiCadID.from_api_response(api_response)
    assert isinstance(project_id, SoloProjectID)
    assert project_id.projectPath == "/path/to/project"
    assert project_id.projectName == "MySoloProject"


def test_archicad_id_from_api_response_teamwork(reset_archicad_id_registry):
    with patch('multiconn_archicad.basic_types.TeamworkProjectID.from_project_location') as mock_from_project_location:
        mock_project_id = MagicMock(spec=TeamworkProjectID)
        mock_from_project_location.return_value = mock_project_id

        api_response = {
                "isUntitled": False,
                "isTeamwork": True,
                "projectLocation": "teamwork://user:pass@server/project",
                "projectName": "MyTeamworkProject"
        }
        project_id = ArchiCadID.from_api_response(api_response)

        mock_from_project_location.assert_called_once_with(
            project_location="teamwork://user:pass@server/project",
            project_name="MyTeamworkProject"
        )
        assert project_id == mock_project_id


def test_archicad_id_from_dict_untitled(reset_archicad_id_registry):
    data_dict = {"projectName": "Untitled"}
    project_id = ArchiCadID.from_dict(data_dict)
    assert isinstance(project_id, UntitledProjectID)
    assert project_id.projectName == "Untitled"


def test_archicad_id_from_dict_solo(reset_archicad_id_registry):
    data_dict = {"projectPath": "/path/to/project", "projectName": "MySoloProject"}
    project_id = ArchiCadID.from_dict(data_dict)
    assert isinstance(project_id, SoloProjectID)
    assert project_id.projectPath == "/path/to/project"
    assert project_id.projectName == "MySoloProject"


def test_archicad_id_from_dict_teamwork(reset_archicad_id_registry):
    data_dict = {
        "projectPath": "projects/myproject",
        "serverAddress": "https://teamwork.example.com",
        "teamworkCredentials": {"username": "user", "password": "secret"},
        "projectName": "MyTeamworkProject"
    }
    project_id = ArchiCadID.from_dict(data_dict)
    assert isinstance(project_id, TeamworkProjectID)
    assert project_id.projectPath == "projects/myproject"
    assert project_id.serverAddress == "https://teamwork.example.com"
    assert project_id.projectName == "MyTeamworkProject"
    assert project_id.teamworkCredentials.username == "user"
    assert project_id.teamworkCredentials.password == "secret"


def test_archicad_id_from_dict_invalid(reset_archicad_id_registry):
    data_dict = {"invalid": "data"}
    with pytest.raises(AttributeError, match="can not instantiate ArchiCadID from"):
        ArchiCadID.from_dict(data_dict)