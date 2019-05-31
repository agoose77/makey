from plumbum import local, cmd
import plumbum
import argparse
import re
from urllib.parse import urlparse, urlunparse

CMAKE_PROJECT_NAME_PATTERN = re.compile(r"project\((.*)\)", re.IGNORECASE)
HTTP_SCHEMES = {"http", "https"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url_or_path", type=str, help="URL/local path of tar file, or url of git repositry prefixed with git+.")
    parser.add_argument("-j", "--jobs", type=str, help="Number of jobs for make command")
    args, unknown_args = parser.parse_known_args()

    # Parse file from URL or local tarball
    old_files = set(local.cwd)
    parsed_url = urlparse(args.url_or_path)

    if parsed_url.scheme.startswith("git+"):
        original_scheme = parsed_url.scheme[len("git+"):]
        repo_url = urlunparse((original_scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, parsed_url.query,
                               parsed_url.fragment))
        (cmd.git("clone", repo_url))
    elif parsed_url.scheme in HTTP_SCHEMES:
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
        cmd.make("install", f"-j{args.jobs}")
        cmd.sudo[cmd.checkinstall, "--pkgname", library_name] & plumbum.FG


if __name__ == "__main__":
    main()
