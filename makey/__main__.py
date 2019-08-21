from argparse import ArgumentParser
from . import makey


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        "url_or_path",
        type=str,
        help="URL/local path of tar file, or url of git repositry prefixed with git+.",
    )
    parser.add_argument(
        "-j", "--jobs", type=str, help="Number of jobs for make command", default=1
    )
    parser.add_argument("--version", type=str, help="Project version")
    parser.add_argument(
        "--checkinstall", action="store_true", help="Force checkinstall"
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args, unknown_args = parser.parse_known_args(args)

    makey(args.url_or_path, args.jobs, args.version, args.verbose, unknown_args, force_checkinstall=args.checkinstall)


if __name__ == "__main__":
    main()
