from argparse import ArgumentParser
from . import makey


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
    parser.add_argument("-V", "--verbose", action="store_true", help="Turn on verbose mode.")
    parser.add_argument("-b", "--build_only", action="store_true", help="Only build package.")
    args, unknown_args = parser.parse_known_args(args)

    makey(
        args.url_or_path,
        args.jobs,
        args.version,
        args.verbose,
        unknown_args,
        force_checkinstall=args.force_checkinstall,
        install_package=not args.build_only,
    )


if __name__ == "__main__":
    main()
