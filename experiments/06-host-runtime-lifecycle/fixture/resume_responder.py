"""Serve lifecycle resume frames through the merged loopback responder."""

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

FRAMES = Path(__file__).parent / "resume_frames"
SOURCE = Path(__file__).parents[2] / "02-host-socket-attribution" / "model_responder.py"


def load_responder() -> ModuleType:
    """Load the reviewed responder and select only the committed resume frames."""
    spec = importlib.util.spec_from_file_location("bv01_model_responder", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("merged responder source is absent")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.FIXTURES = FRAMES  # pyrefly: ignore[missing-attribute]
    return module


if __name__ == "__main__":
    load_responder().main()
