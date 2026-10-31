import tomllib
from pathlib import Path

import minny


def test_package_metadata_version_matches_runtime_version():
    project_dir = Path(__file__).parent.parent
    with (project_dir / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    assert pyproject["project"]["version"] == minny.__version__
