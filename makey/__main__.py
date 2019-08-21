from argparse import ArgumentParser
from . import makey


def make_arguments(opts, flags):
    return [f"-{o}" for o in opts] + [f"--{f}" for f in flags]


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        "url_or_path",
        type=str,
        help="URL/local path of tar file, or url of git repository prefixed with git+.",
    )
    parser.add_argument(
        "-j", "--jobs", type=str, help="Number of jobs for make command.", default=1
    )
    parser.add_argument("-v", "--version", type=str, help="Project version.")
    parser.add_argument(
        "-c", "--force_checkinstall", action="store_true", help="Force checkinstall."
    )
    parser.add_argument("-p", "--patch", help="Apply patch to source.")
    parser.add_argument("-V", "--verbose", action="store_true", help="Turn on verbose mode.")
    parser.add_argument("-b", "--build_only", action="store_true", help="Only build package.")
    parser.add_argument("--cflag", action="append", nargs="+", help="CMake flags pass-through.", default=[])
    parser.add_argument("-D", "--copt", action="append", nargs="+", help="CMake options pass-through.", default=[])
    parser.add_argument("--dflag", action="append", nargs="+", help="dpkg flags pass-through.", default=[])
    parser.add_argument("--dopt", action="append", nargs="+", help="dpkg options pass-through.", default=[])
    args = parser.parse_args(args)

    makey(
        args.url_or_path,
        args.jobs,
        args.version,
        args.verbose,
        patch=args.patch,
        cmake_args=make_arguments(sum(args.copt, []), sum(args.cflag, [])),
        dpkg_args=make_arguments(sum(args.dopt, []), sum(args.dflag, [])),
        force_checkinstall=args.force_checkinstall,
        install_package=not args.build_only,
    )


if __name__ == "__main__":
    main()
