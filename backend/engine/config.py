"""Discovery Engine - Configuration loading, validation, hashing, and overrides (P2.2)."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from engine.errors import ConfigError
from engine.schema import ContentTypeSpec

# Default configs directory relative to this file: backend/engine/configs
DEFAULT_CONFIGS_DIR = Path(__file__).resolve().parent / "configs"


def compute_config_hash(data: dict[str, Any] | ContentTypeSpec) -> str:
    """Compute a deterministic SHA-256 hash for a configuration dictionary or ContentTypeSpec."""
    raw_dict = data.model_dump() if isinstance(data, ContentTypeSpec) else copy.deepcopy(data)
    raw_dict.pop("test_only", None)
    raw_dict.pop("chat", None)
    if isinstance(raw_dict.get("evaluation"), dict):
        raw_dict["evaluation"].pop("post_train", None)

    # Serialize canonical JSON with sorted keys
    canonical_json = json.dumps(raw_dict, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def get_config_path(path_or_type: str | Path, configs_dir: Path | None = None) -> Path:
    """Resolve a config path from an explicit file path or content type slug."""
    p = Path(path_or_type)
    if p.exists() and p.is_file():
        return p.resolve()

    base_dir = configs_dir or DEFAULT_CONFIGS_DIR
    slug_path = base_dir / f"{path_or_type}.yaml"
    if slug_path.exists() and slug_path.is_file():
        return slug_path.resolve()

    slug_yml_path = base_dir / f"{path_or_type}.yml"
    if slug_yml_path.exists() and slug_yml_path.is_file():
        return slug_yml_path.resolve()

    raise ConfigError(
        f"Configuration file not found for '{path_or_type}'. Searched: {p} and {slug_path}"
    )


def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge overrides dict into base dict."""
    result = copy.deepcopy(base)
    for key, val in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = deep_merge(result[key], val)
        else:
            result[key] = copy.deepcopy(val)
    return result


def apply_fast_overrides(raw_dict: dict[str, Any]) -> dict[str, Any]:
    """Apply generic --fast overrides from the config's 'fast' section if present."""
    config = copy.deepcopy(raw_dict)
    if "fast" not in config or config["fast"] is None:
        return config

    fast_section = config["fast"]
    if not isinstance(fast_section, dict):
        raise ConfigError(
            f"The 'fast' configuration section must be a mapping/dict, got {type(fast_section).__name__}"
        )

    for k, v in fast_section.items():
        if k in config and isinstance(config[k], dict) and isinstance(v, dict):
            config[k] = deep_merge(config[k], v)
        else:
            config[k] = copy.deepcopy(v)

    return config


def load_config(
    path_or_type: str | Path,
    fast: bool = False,
    configs_dir: Path | None = None,
) -> ContentTypeSpec:
    """Load, validate, optionally override, and return a ContentTypeSpec.

    Args:
        path_or_type: File path or content type identifier (e.g. 'media').
        fast: If True, applies faster settings (smaller dataset variants).
        configs_dir: Optional custom directory to look for config YAMLs.

    Returns:
        Validated ContentTypeSpec instance.

    Raises:
        ConfigError: If file is missing, YAML is invalid, or schema validation fails.
    """
    config_file = get_config_path(path_or_type, configs_dir)

    try:
        content = config_file.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(f"Failed to read config file '{config_file}': {e}") from e

    try:
        raw_data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in config file '{config_file}': {e}") from e

    if not isinstance(raw_data, dict):
        raise ConfigError(
            f"Config file '{config_file}' must define a mapping/dictionary, got {type(raw_data).__name__}"
        )

    if fast:
        raw_data = apply_fast_overrides(raw_data)

    try:
        spec = ContentTypeSpec.model_validate(raw_data)
    except ValidationError as e:
        errors_summary = []
        for err in e.errors():
            loc = " -> ".join(str(x) for x in err.get("loc", []))
            msg = err.get("msg", "Validation error")
            errors_summary.append(f"Field '{loc}': {msg}")
        readable_errors = "\n  - " + "\n  - ".join(errors_summary)
        raise ConfigError(
            f"Configuration validation failed for '{config_file}':{readable_errors}"
        ) from e

    return spec


def resolve_serving_config(
    content_type: str,
    type_dir: Path,
    configs_dir: Path | None = None,
) -> ContentTypeSpec:
    """Reconstruct and verify the exact serving configuration from artifact manifest (FIX-37).

    Matches dataset variant, applies tuned serving parameters, and asserts config_hash agreement.
    """
    manifest_path = type_dir / "manifest.json"
    if not manifest_path.exists():
        raise ConfigError(
            f"Cannot resolve serving config: manifest.json not found at {manifest_path}"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_hash = manifest.get("config_hash")

    # Reconstruct serving config checking both standard and fast configurations
    candidate_specs: list[ContentTypeSpec] = []
    for is_fast in (False, True):
        candidate = load_config(content_type, fast=is_fast, configs_dir=configs_dir)
        tuning_file = type_dir / "tuning.json"
        if tuning_file.exists():
            try:
                tdata = json.loads(tuning_file.read_text(encoding="utf-8"))
            except Exception as e:
                raise ConfigError(f"Failed to parse tuning.json at {tuning_file}: {e}") from e

            if not isinstance(tdata, dict) or "best_params" not in tdata:
                raise ConfigError(
                    f"Failed to parse tuning.json at {tuning_file}: missing 'best_params' dictionary"
                )

            best_p = tdata.get("best_params", {})
            if "similarity_type" in best_p:
                candidate.model.params["similarity_type"] = best_p["similarity_type"]
            if "timedecay_formula" in best_p:
                candidate.model.params["timedecay_formula"] = best_p["timedecay_formula"]
            if "top_neighbors_per_item" in best_p:
                candidate.serving.top_neighbors_per_item = int(best_p["top_neighbors_per_item"])
            if best_p.get("time_decay_coefficient") is not None:
                candidate.model.params["time_decay_coefficient"] = best_p["time_decay_coefficient"]
            if "positive_threshold" in best_p:
                candidate.signal.positive_threshold = float(best_p["positive_threshold"])
        candidate_specs.append(candidate)
        if expected_hash and compute_config_hash(candidate) == expected_hash:
            return candidate

    # If neither candidate produced expected_hash, report the mismatch
    last_computed = compute_config_hash(candidate_specs[0])
    raise ConfigError(
        f"Serving config hash mismatch for '{content_type}': "
        f"computed {last_computed} but artifact manifest requires {expected_hash}"
    )
