"""Explicit synthetic profile for mocked transport tests, never an app default."""
import json
from pathlib import Path
from app.domain.shopping import ShoppingProfile


def configured_profile(**changes):
    data = json.loads((Path(__file__).parent / "fixtures/shopping-profile.json").read_text())
    data.update(changes)
    return ShoppingProfile.model_validate(data)
