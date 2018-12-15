from plumbum import local, cmd
import plumbum
import argparse


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", type=str)
    args, unknown_args= parser.parse_known_args()

    old_files = set(local.cwd)
    (cmd.wget["-qO-", args.url] | cmd.tar["xvz"])()

    project_path, = set(local.cwd) - old_files

    # Place source inside the project directory
    source_path = project_path.move(local.cwd / f"{project_path.name}_source")
    source_path = source_path.move(project_path / "source")

    build_path = project_path / "build"
    build_path.mkdir()

    with local.cwd(build_path):
        cmd.cmake(source_path, *unknown_args)
        cmd.sudo[cmd.checkinstall] & plumbum.FG
