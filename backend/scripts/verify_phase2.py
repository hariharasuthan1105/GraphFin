"""Run pytest in a fresh disposable repository copy, never production state.

python backend/scripts/verify_phase2.py SCRATCH_DIRECTORY -- [pytest arguments]
Use the same Python interpreter that has the project's dependencies installed.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    root = Path(__file__).resolve().parents[2]
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    scratch = Path(sys.argv[1]).resolve()
    if scratch.is_relative_to(root):
        raise SystemExit("Scratch directory must be outside the source repository.")
    scratch.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix="phase2-", dir=scratch))
    checkout = directory / "repo"
    shutil.copytree(root, checkout, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "node_modules", ".venv"))
    (checkout / ".graphfin-test-sandbox").write_text(str(checkout.resolve()))
    for name in ("temp", "mpl"):
        (directory / name).mkdir()
    env = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD="1", TEMP=str(directory/"temp"),
               TMP=str(directory/"temp"), MPLCONFIGDIR=str(directory/"mpl"))
    args = sys.argv[2:]
    if args[:1] == ["--"]:
        args = args[1:]
    command = [sys.executable, "-u", "-m", "pytest", "-ra", "--basetemp="+str(directory/"pytest-temp"),
               "--junitxml="+str(directory/"results.xml"), *args]
    print("DISPOSABLE_ROOT="+str(directory), flush=True)
    with (directory/"command.txt").open("w", encoding="utf-8") as f:
        f.write(repr(command))
    # Preserve transcript while streaming progress. No application patches or event-loop substitutions.
    with (directory/"pytest.log").open("w", encoding="utf-8") as log:
        proc = subprocess.Popen(command, cwd=checkout, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            log.write(line); log.flush()
            print(line, end="", flush=True)
        result = proc.wait()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
