from __future__ import annotations

import logging
import os
import re

from pathlib import Path

logger = logging.getLogger(__name__)


def find_readme_files() -> dict[str, Path]:
    """Find all README files"""
    project_root = Path("..")  # TODO: make this location agnostic
    readme_files = project_root.rglob("README.md")

    files: dict[str, Path] = {}

    for file in readme_files:
        abspath = Path(os.path.abspath(file.absolute()))

        if abspath.parent.name in ['.pytest_cache', 'data']:
            # Ignore these files
            continue

        files[abspath.parent.name] = abspath

    return files


def replace_section(readme_text: str, section_name: str, section_text: str) -> str:
    """Replaces a section in the main README text with the section README text"""
    start = f"<!-- {section_name} section -->"
    end = f"<!-- end {section_name} section -->"

    if start not in readme_text or end not in readme_text:
        logger.warning(
            f"Could not combine section {section_name}, no placeholders found"
        )
        return readme_text

    section_text = f"{start}\n{section_text}\n{end}"
    readme_text = re.sub(f"{start}.*?{end}", section_text, readme_text, flags=re.DOTALL)

    return readme_text


def add_extra_heading_level(lines: list[str]) -> str:
    """Adds an extra heading level '#' to each line that starts with '#'"""
    new_lines: list[str] = []
    inside_code_block = False

    for line in lines:
        if line.startswith("```"):
            inside_code_block = not inside_code_block

        if line.startswith('#') and not inside_code_block:
            new_lines.append('#' + line)
            continue

        new_lines.append(line)

    return ''.join(new_lines)


def read_file_text(path: Path) -> str:
    """Reads file to str"""
    with open(path, "r") as file:
        text = file.read()
    return text


def read_file_lines(path: Path) -> list[str]:
    """Reads file to list of str"""
    with open(path, "r") as file:
        lines = file.readlines()
    return lines


def write_to_file(path: Path, text: str) -> None:
    """Write text to file"""
    with open(path, "w") as file:
        file.write(text)


def read_section(path: Path) -> str:
    """Reads file and adds extra heading level"""
    lines = read_file_lines(path)
    return add_extra_heading_level(lines)


def compile_readme() -> None:
    """Combines all readme files into one"""
    readme_files = find_readme_files()

    main_readme = readme_files['fittie']
    main_readme_text = read_file_text(main_readme)

    for section_name, path in readme_files.items():
        if section_name == 'fittie':
            continue

        section_text = read_section(path)
        main_readme_text = replace_section(main_readme_text, section_name, section_text)

    write_to_file(main_readme, main_readme_text)


if __name__ == "__main__":
    compile_readme()
