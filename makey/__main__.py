from plumbum import local, cmd, ProcessExecutionError
import plumbum
import argparse
import re
import getpass
from urllib.parse import urlparse, urlunparse
from contextlib import contextmanager

CMAKE_PROJECT_NAME_PATTERN = re.compile(r"project\((.*)\)", re.IGNORECASE)
PACKAGE_NAME_PATTERN = re.compile(r"package: (.*?) generated")
VERSION_STRING_PATTERN = re.compile(r"v(\d+[\.-]\d+[\.-]\d+)")
HTTP_SCHEMES = {"http", "https"}


@contextmanager
def track_new_files(path):
    files = set(path)
    changed = set()
    yield changed
    changed.update(set(path) - files)


def load_source(url_or_path: str) -> plumbum.Path:
    parsed_url = urlparse(url_or_path)

    with track_new_files(local.cwd) as new_files:
        # Load data
        if parsed_url.scheme.startswith("git+"):
            original_scheme = parsed_url.scheme[len("git+") :]
            repo_url = urlunparse(
                (
                    original_scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    parsed_url.params,
                    parsed_url.query,
                    "",
                )
            )
            args = ["clone", repo_url, "--depth=1"]
            if parsed_url.fragment:
                args.append(f"--branch={parsed_url.fragment}")
            cmd.git(*args)

        elif parsed_url.scheme in HTTP_SCHEMES:
            (cmd.wget["-qO-", url_or_path] | cmd.tar["xvz"])()
        else:
            cmd.tar("-xvf", url_or_path)

    project_path, = new_files
    return project_path


def find_version_from_git() -> str:
    version_string = cmd.git("describe", "--tags", "--abbrev=0")
    major, minor, patch = VERSION_STRING_PATTERN.search(version_string).groups()
    return f"{major}.{minor}.{patch}"


def load_cmake_project_name(cmakelists_contents: str) -> str:
    library_name_match = CMAKE_PROJECT_NAME_PATTERN.search(cmakelists_contents)
    if library_name_match is None:
        raise ValueError("Unable to find package name from CMakeLists.txt")
    return library_name_match.group(1).strip()


def install_with_cpack(verbose: bool = False):
    author = getpass.getuser()
    result = run_command(
        cmd.sudo[cmd.cpack["-G", "DEB", "-D", f'CPACK_PACKAGE_CONTACT="{author}"']],
        verbose,
    )
    package_name = PACKAGE_NAME_PATTERN.search(result).group(1).strip()
    run_command(cmd.sudo[cmd.apt["install", package_name]], verbose)


def install_with_checkinstall(name: str, version: str, verbose: bool = False):
    run_command(
        cmd.sudo[cmd.checkinstall[f"--pkgname={name}", f"--pkgversion={version}"]],
        verbose,
    )


def run_command(command, verbose: bool):
    if verbose:
        retcode, stdout, stderr = command & plumbum.TEE
        return stdout
    else:
        return command()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "url_or_path",
        type=str,
        help="URL/local path of tar file, or url of git repositry prefixed with git+.",
    )
    parser.add_argument(
        "-j", "--jobs", type=str, help="Number of jobs for make command", default=1
    )
    parser.add_argument("--version", type=str, help="Project version")
    parser.add_argument("-v", "--verbose", action="store_true")
    args, unknown_args = parser.parse_known_args()

    # Parse file from URL or local tarball
    project_path = load_source(args.url_or_path)

    # Place source inside the project directory
    source_path = project_path.move(local.cwd / f"{project_path.name}_source")
    source_path = source_path.move(project_path / "source")
    build_path = project_path / "build"
    build_path.mkdir()

    # Make package with CMAKE
    with local.cwd(build_path):
        print("Running CMake")
        run_command(cmd.cmake[(source_path, *unknown_args)], args.verbose)

        print("Running Make")
        run_command(cmd.make[f"-j{args.jobs}"], args.verbose)

        # Try CPack, otherwise use checkinstall
        if (local.cwd / "CPackConfig.cmake").exists():
            print("Installing with CPack")
            install_with_cpack(verbose=args.verbose)
        else:
            print("Installing with checkinstall")
            # Find library name
            library_name = load_cmake_project_name(
                (source_path / "CMakeLists.txt").read("utf8")
            )
            if args.version is None:
                with local.cwd(source_path):
                    try:
                        version = find_version_from_git()
                        print(f"Using version {version} from Git")
                    except ProcessExecutionError:
                        raise ValueError(
                            "Could not load version from Git, need to pass version flag."
                        )
            else:
                version = args.version

            install_with_checkinstall(library_name, version, verbose=args.verbose)
    print("Done!")


if __name__ == "__main__":
    main()
