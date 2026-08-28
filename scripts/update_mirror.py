from __future__ import annotations

import json
import re
import subprocess
import urllib.request
from pathlib import Path


PYPI_URL = "https://pypi.org/pypi/typos/json"

VERSION_FILE = Path(".version")
PYPROJECT_FILE = Path("pyproject.toml")

VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")

DEPENDENCY_RE = re.compile(
    r'(?m)^(?P<indent>\s*)"typos==(?P<version>\d+\.\d+\.\d+)"'
    r"(?P<comma>,?)$"
)


def version_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))


def git(*args: str) -> None:
    subprocess.run(
        ["git", *args],
        check=True,
    )


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        text=True,
    ).strip()


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        [
            "git",
            "rev-parse",
            "--verify",
            "--quiet",
            f"refs/tags/{tag}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def check_working_tree() -> None:
    if git_output("status", "--porcelain"):
        raise RuntimeError("Working tree is not clean")


def read_current_version() -> str:
    version = VERSION_FILE.read_text(encoding="utf-8").strip()

    if not VERSION_RE.fullmatch(version):
        raise RuntimeError(
            f"Invalid version in {VERSION_FILE}: {version!r}"
        )

    return version


def read_pinned_version() -> str:
    pyproject = PYPROJECT_FILE.read_text(encoding="utf-8")
    matches = list(DEPENDENCY_RE.finditer(pyproject))

    if len(matches) != 1:
        raise RuntimeError(
            "Expected exactly one pinned typos dependency in "
            f"{PYPROJECT_FILE}"
        )

    return matches[0].group("version")


def validate_current_state(current: str) -> None:
    pinned = read_pinned_version()

    if pinned != current:
        raise RuntimeError(
            "Version mismatch: "
            f"{VERSION_FILE} contains {current}, "
            f"but {PYPROJECT_FILE} contains typos=={pinned}"
        )

    tag = f"v{current}"

    if not tag_exists(tag):
        raise RuntimeError(
            f"Current mirror tag {tag} does not exist"
        )

    tagged_version = git_output(
        "show",
        f"{tag}:.version",
    )

    if tagged_version != current:
        raise RuntimeError(
            f"{tag} contains .version={tagged_version}, "
            f"expected {current}"
        )


def fetch_available_versions() -> list[str]:
    request = urllib.request.Request(
        PYPI_URL,
        headers={
            "User-Agent": "rdmorganiser/mirrors-typos",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=30,
    ) as response:
        metadata = json.load(response)

    return sorted(
        (
            version
            for version in metadata["releases"]
            if VERSION_RE.fullmatch(version)
        ),
        key=version_key,
    )


def get_new_versions(
    current: str,
    available_versions: list[str],
) -> list[str]:
    if current not in available_versions:
        raise RuntimeError(
            f"Current version {current} is not available on PyPI"
        )

    current_index = available_versions.index(current)

    return available_versions[current_index + 1 :]


def update_pyproject(version: str) -> None:
    pyproject = PYPROJECT_FILE.read_text(encoding="utf-8")

    def replace_dependency(match: re.Match[str]) -> str:
        return (
            f'{match.group("indent")}'
            f'"typos=={version}"'
            f'{match.group("comma")}'
        )

    pyproject, count = DEPENDENCY_RE.subn(
        replace_dependency,
        pyproject,
    )

    if count != 1:
        raise RuntimeError(
            "Expected to replace exactly one typos dependency, "
            f"replaced {count}"
        )

    PYPROJECT_FILE.write_text(
        pyproject,
        encoding="utf-8",
    )


def create_mirror_release(version: str) -> None:
    tag = f"v{version}"

    if tag_exists(tag):
        raise RuntimeError(
            f"Tag {tag} already exists"
        )

    print(f"Creating mirror release {version}")

    update_pyproject(version)

    VERSION_FILE.write_text(
        f"{version}\n",
        encoding="utf-8",
    )

    git(
        "add",
        str(VERSION_FILE),
        str(PYPROJECT_FILE),
    )

    git(
        "diff",
        "--cached",
        "--check",
    )

    git(
        "commit",
        "-m",
        f"Mirror: {version}",
    )

    git(
        "tag",
        "-a",
        tag,
        "-m",
        f"Mirror: {version}",
    )


def main() -> None:
    check_working_tree()

    current = read_current_version()

    validate_current_state(current)

    available_versions = fetch_available_versions()
    new_versions = get_new_versions(
        current,
        available_versions,
    )

    if not new_versions:
        print(f"Mirror is up to date at {current}")
        return

    print(
        "New releases:",
        ", ".join(new_versions),
    )

    for version in new_versions:
        create_mirror_release(version)

    check_working_tree()


if __name__ == "__main__":
    main()
