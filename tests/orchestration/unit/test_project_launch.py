from unittest.mock import MagicMock

import pytest

from multiconn_archicad import ConnHeader
from multiconn_archicad.orchestration.actions.project_handler import OpenProject, ProjectParams
from multiconn_archicad.orchestration.basic_types import TeamworkCredentials

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "system, executable, project_path",
    [
        ("Windows", r"C:\Program Files\Graphisoft\ARCHICAD.exe", r"C:\Projects\O'Brien & Sons\House $1.pln"),
        (
            "Darwin",
            "/Applications/Graphisoft/Archicad 29/Archicad.app/Contents/MacOS/ARCHICAD",
            "/Users/example/Projects/O'Brien & Sons/House $1.pln",
        ),
    ],
)
@pytest.mark.parametrize("project_kind", ["solo", "teamwork", "teamwork_override"])
@pytest.mark.parametrize("demo", [False, True])
def test_launch_preserves_arguments(monkeypatch, system, executable, project_path, project_kind, demo):
    monkeypatch.setattr("platform.system", lambda: system)
    popen = MagicMock()
    monkeypatch.setattr("multiconn_archicad.orchestration.actions.project_handler.subprocess", MagicMock(Popen=popen))
    credentials = None
    if project_kind == "solo":
        project_id = {"project_type": "solo", "projectPath": project_path, "projectName": "House"}
        expected_location = project_path
    else:
        project_id = {
            "project_type": "teamwork",
            "projectPath": "Projects/House A.pln",
            "projectName": "House",
            "serverAddress": "https://bim.example.com",
            "teamworkCredentials": {"username": "stored user", "password": "stored&password"},
        }
        expected_credentials = "stored%20user:stored%26password"
        if project_kind == "teamwork_override":
            credentials = TeamworkCredentials(username="other user", password="other&password")
            expected_credentials = "other%20user:other%26password"
        expected_location = (
            f"teamwork://{expected_credentials}@https%253A%252F%252Fbim%2Eexample%2Ecom/Projects%252FHouse%2520A%2Epln"
        )

    header = ConnHeader.from_dict(
        {
            "productInfo": {"version": 29, "buildNumber": 3000, "languageCode": "INT"},
            "archicadId": project_id,
            "archicadLocation": {"archicadLocation": executable},
        }
    )
    multi_conn = MagicMock()
    multi_conn.find_archicad.from_header.return_value = None
    action = OpenProject(multi_conn)
    params = action._check_input(ProjectParams(header, credentials, demo))

    action._open_project(params)

    expected_args = [executable, expected_location]
    if demo:
        expected_args.append("-demo")
    popen.assert_called_once_with(expected_args, start_new_session=True, shell=False, text=True)
    multi_conn.dialog_handler.start.assert_called_once_with(popen.return_value)
