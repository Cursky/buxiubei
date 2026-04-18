"""harness/paths.py — Cross-platform path helpers for MoYing.

Single source of truth for the global MoYing home directory.

NOTE: ``moying-install.py`` keeps a *separate* copy of this function on purpose.
The installer must locate ``~/.moying/`` *before* it can ``import harness.*``,
because it injects ``~/.moying`` into ``sys.path`` only after copying the
``harness/`` tree there. Do not "deduplicate" the installer's copy.
"""

import os
from pathlib import Path

MOYING_HOME_ENV = "MOYING_HOME"


def get_moying_home() -> Path:
    """Cross-platform global path: ~/.moying/ or %USERPROFILE%\\.moying\\."""
    if env := os.environ.get(MOYING_HOME_ENV):
        return Path(env)
    if os.name == "nt":
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".moying"
    return Path.home() / ".moying"
