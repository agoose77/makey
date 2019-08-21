import getpass
import re
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse

import plumbum
import os
import logging
from plumbum import local, cmd, ProcessExecutionError

logging.basicConfig(level=os.environ.get("MAKEY_LOGLEVEL", "WARNING"))

CMAKE_PROJECT_NAME_PATTERN = re.compile(r"project\((.*)\)", re.IGNORECASE)
PACKAGE_NAME_PATTERN = re.compile(r"package: (.*?) generated")
VERSION_STRING_PATTERN = re.compile(r"v(\d+)[\.-](\d+)[\.-](\d+)")
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
            url_path = local.cwd / url_or_path
            if url_path.is_dir():
                cmd.cp("-r", url_path, local.cwd)
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


def build_with_cpack(verbose: bool = False) -> plumbum.LocalPath:
    author = getpass.getuser()
    result = run_command(
        cmd.cpack["-G", "DEB", "-D", f'CPACK_PACKAGE_CONTACT="{author}"'], verbose
    )
    return local.cwd / PACKAGE_NAME_PATTERN.search(result).group(1).strip()


def build_with_checkinstall(
    name: str, version: str, verbose: bool = False
) -> plumbum.LocalPath:
    # Checkinstall returns filename on stderr, let's just use this approach
    with track_new_files(local.cwd) as new_files:
        run_command(
            cmd.checkinstall[
                f"--pkgname={name}",
                f"--pkgversion={version}",
                "--install=no",
                "--fstrans=yes",
            ],
            verbose,
        )
    return next(p for p in new_files if p.suffix == ".deb")


def run_command(command, verbose: bool):
    if verbose:
        retcode, stdout, stderr = command & plumbum.TEE
        return stdout
    else:
        return command()


def makey(
    url_or_path: str,
    jobs: int = 1,
    version: str = None,
    verbose: bool = False,
    cmake_args: list = None,
    dpkg_args: list = None,
    force_checkinstall: bool = False,
    install_package: bool = True,
):
    # Parse file from URL or local tarball
    print(f"Loading source from {url_or_path}")
    project_path = load_source(url_or_path)

    # Place source inside the project directory
    source_path = project_path.move(local.cwd / f"{project_path.name}_source").move(project_path / "source")
    build_path = project_path / "build"
    build_path.mkdir()

    # Make package with CMAKE
    with local.cwd(build_path):
        print("Running CMake")
        run_command(cmd.cmake[(source_path, *cmake_args)], verbose)

        print("Running Make")
        run_command(cmd.make[f"-j{jobs}"], verbose)

        # Try CPack, otherwise use checkinstall
        if (local.cwd / "CPackConfig.cmake").exists() and not force_checkinstall:
            print("Installing with CPack")
            deb_path = build_with_cpack(verbose=verbose)
        else:
            print("Installing with checkinstall")
            # Find library name
            library_name = load_cmake_project_name(
                (source_path / "CMakeLists.txt").read("utf8")
            )
            if version is None:
                with local.cwd(source_path):
                    try:
                        version = find_version_from_git()
                        print(f"Using version {version} from Git")
                    except ProcessExecutionError:
                        version = input(
                            "Could not load version from Git, please enter version string (major.minor.patch):"
                        )

            deb_path = build_with_checkinstall(library_name, version, verbose=verbose)

        print(f"Created deb file: {deb_path}")

        if install_package:
            print("Installing deb file ...")
            run_command(cmd.sudo[cmd.dpkg[("-i", deb_path, *dpkg_args)]], verbose)

    return deb_path
