"""One-command setup, on any operating system.

    python setup.py

Builds the virtual environment, installs the three dependencies, creates a
.env from the example, and tells you how to start. Uses nothing but the
standard library, so it runs before anything is installed.

    python setup.py --start     set up and then start the portal immediately
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
MIN_PYTHON = (3, 10)


def venv_python() -> Path:
    """The interpreter inside .venv - Scripts on Windows, bin everywhere else."""
    if platform.system() == "Windows":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def run(command: list[str], what: str) -> None:
    print(f"  {what} ...", flush=True)
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"\n{what} failed (exit {result.returncode}).\n"
                 f"Command was: {' '.join(str(c) for c in command)}")


def main() -> None:
    print(f"\nSetting up InternRadar in {ROOT}\n")

    if sys.version_info < MIN_PYTHON:
        sys.exit(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or newer is needed - "
                 f"this is {platform.python_version()}.\n"
                 f"Get it from https://www.python.org/downloads/ and run this again.")
    print(f"  Python {platform.python_version()} on {platform.system()} - fine")

    if not venv_python().exists():
        print("  creating the virtual environment ...", flush=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(VENV)
    else:
        print("  virtual environment already there")

    python = str(venv_python())
    run([python, "-m", "pip", "install", "--upgrade", "pip", "--quiet"], "upgrading pip")
    run([python, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"],
        "installing Flask, waitress and python-jobspy")

    env_file = ROOT / ".env"
    if not env_file.exists():
        shutil.copyfile(ROOT / ".env.example", env_file)
        print("  created .env from the example")
    else:
        print("  .env already there, left alone")

    # Prove the install works before claiming it does.
    check = subprocess.run([python, "-c", "import flask, jobspy, waitress; print('imports ok')"],
                           cwd=ROOT, capture_output=True, text=True)
    if check.returncode != 0:
        sys.exit("\nThe packages installed but will not import:\n" + check.stderr[-800:])
    print("  " + check.stdout.strip())

    start = "start_portal.cmd" if platform.system() == "Windows" else "./start.sh"
    print(f"""
Done.

  Start the portal:   {start}
            or:       {python} app.py

  Then open:          http://127.0.0.1:8700

The first account you create is the operator and gets the /admin page.
Email stays off until you put an app password in .env - until then every
digest is written to data/outbox as an .html file you can open.
""")

    if "--start" in sys.argv:
        os.execv(python, [python, str(ROOT / "app.py")])


if __name__ == "__main__":
    main()
