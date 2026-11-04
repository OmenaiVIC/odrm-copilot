import json
from pathlib import Path
from typing import Any

import joblib  # type: ignore


class ModelNotFoundError(Exception):
    pass


class ModelContractError(Exception):
    pass


def save_model(model: Any, metadata: dict[str, Any], root: Path) -> None:
    """Saves the model and metadata atomically."""
    target = metadata["target"]
    version = metadata["model_version"]

    target_dir = Path(root) / target
    version_dir = target_dir / version
    version_dir.mkdir(parents=True, exist_ok=True)

    model_path = version_dir / "model.joblib"
    joblib.dump(model, model_path)

    meta_path = version_dir / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    latest_path = target_dir / "latest.json"
    latest_path.write_text(
        json.dumps({"version": version, "target": target}, indent=2), encoding="utf-8"
    )


def load_model(target: str, root: Path, version: str | None = None) -> tuple[Any, dict[str, Any]]:
    """Loads a model by target and optional specific version. Defaults to latest."""
    target_dir = Path(root) / target
    latest_path = target_dir / "latest.json"

    if not latest_path.exists():
        raise ModelNotFoundError(f"No latest.json found for target '{target}' at {target_dir}")

    latest_data = json.loads(latest_path.read_text(encoding="utf-8"))
    resolved_version = version or latest_data["version"]

    version_dir = target_dir / resolved_version
    model_path = version_dir / "model.joblib"
    meta_path = version_dir / "metadata.json"

    if not model_path.exists() or not meta_path.exists():
        raise ModelNotFoundError(f"Artifact files missing for {target} v{resolved_version}")

    model = joblib.load(model_path)
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    model_features = getattr(model, "feature_names_in_", [])
    meta_features = metadata.get("features", [])

    if list(model_features) != list(meta_features):
        raise ModelContractError(
            f"Model feature mismatch: model expects {model_features}, metadata says {meta_features}"
        )

    return model, metadata
