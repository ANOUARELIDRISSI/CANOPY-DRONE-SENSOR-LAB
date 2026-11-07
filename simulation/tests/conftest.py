"""Keep test scratch files in a new project-local directory on Windows and Linux."""

import tempfile
from pathlib import Path


def pytest_configure(config):
    if config.option.basetemp is None:
        parent = Path(config.rootpath) / "artifacts" / "tests"
        parent.mkdir(parents=True, exist_ok=True)
        # New empty directory only; never point pytest's cleanup at existing experiments.
        config.option.basetemp = tempfile.mkdtemp(prefix="run-", dir=parent)
