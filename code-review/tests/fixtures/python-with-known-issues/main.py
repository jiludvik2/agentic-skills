import subprocess


def run_command(cmd: str) -> None:
    subprocess.run(cmd, shell=True)  # noqa: S603,S604
