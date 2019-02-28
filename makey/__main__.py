from plumbum import local, cmd
import plumbum
import argparse
import re
from urllib.parse import urlparse

CMAKE_PROJECT_NAME_PATTERN = re.compile(r"project\((.*)\)")
HTTP_SCHEMES = {"http", "https"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url_or_path", type=str)
    args, unknown_args = parser.parse_known_args()

    # Parse file from URL or local tarball
    old_files = set(local.cwd)
    scheme = urlparse(args.url_or_path).scheme

    if scheme in HTTP_SCHEMES:
        (cmd.wget["-qO-", args.url_or_path] | cmd.tar["xvz"])()
    else:
        cmd.tar("-xvf", args.url_or_path)
    project_path, = set(local.cwd) - old_files

    # Place source inside the project directory
    source_path = project_path.move(local.cwd / f"{project_path.name}_source")
    source_path = source_path.move(project_path / "source")

    build_path = project_path / "build"
    build_path.mkdir()

    # Find library name
    cmake_path = source_path / "CMakeLists.txt"
    library_name_match = CMAKE_PROJECT_NAME_PATTERN.search(cmake_path.read("utf8"))
    if library_name_match is None:
        raise ValueError("Unable to find package name from CMakeLists.txt")
    library_name = library_name_match.group(1)

    # Make package with CMAKE
    with local.cwd(build_path):
        cmd.cmake(source_path, *unknown_args)
        cmd.sudo[cmd.checkinstall, "--pkgname", library_name] & plumbum.FG


if __name__ == "__main__":
    main()
