#!/usr/bin/env python3
"""Create an AI-assisted testing workspace using only the standard library."""

import argparse
import re
import shutil
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parent / "template"
EMPTY_DIRS = (
    "AI-Workspace/SecretScrub",
    "AI-Workspace/Images-Redacted",
    "Images-Raw",
    "Output-Raw",
)


def project_name(value):
    """Require a single directory name portable across supported systems."""
    if (
        not value or value in (".", "..")
        or value != value.strip() or value.endswith(".")
        or re.search(r'[<>:"/\\|?*\x00-\x1f\x7f]', value)
        or re.fullmatch(r"CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[1-9¹²³]|LPT[1-9¹²³]",
                        value.split(".")[0].rstrip(), re.IGNORECASE)
    ):
        raise argparse.ArgumentTypeError(
            "use a single directory name without path separators, reserved Windows "
            "names, leading/trailing spaces, trailing dots, or invalid characters"
        )
    return value


def create_workspace(name, parent):
    name = project_name(name)
    parent = Path(parent).expanduser().resolve()
    destination = parent / name
    if not TEMPLATE_DIR.is_dir():
        raise FileNotFoundError("Missing template folder beside create_workspace.py")
    parent.mkdir(parents=True, exist_ok=True)
    # Reserve the destination exclusively; never merge into an existing project.
    destination.mkdir()
    try:
        shutil.copytree(TEMPLATE_DIR, destination, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns(".DS_Store", "__pycache__", ".obsidian"))
        for directory in EMPTY_DIRS:
            (destination / directory).mkdir(parents=True, exist_ok=True)
        (destination / "workspace.code-workspace").rename(
            destination / (name + ".code-workspace")
        )
    except BaseException:
        # Only remove the new directory this invocation successfully reserved.
        shutil.rmtree(destination)
        raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--ProjectName", required=True, type=project_name,
                        help="Name of the new project directory (not a path)")
    parser.add_argument("--ParentDir", required=True, type=Path,
                        help="Parent directory; created if missing. Supports ~ and spaces.")
    args = parser.parse_args()
    try:
        destination = create_workspace(args.ProjectName, args.ParentDir)
    except FileExistsError:
        parser.exit(1, "Error: destination already exists, or a parent is a file; nothing overwritten.\n")
    except OSError as error:
        parser.exit(1, "Error: {}\n".format(error))
    print("Created: {}".format(destination))
    print("Open in VS Code: {}".format(destination / (args.ProjectName + ".code-workspace")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
