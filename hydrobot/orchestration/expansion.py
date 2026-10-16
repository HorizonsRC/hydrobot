from typing import Any
from copy import deepcopy

# TODO: Stays a plain dict for now. Tighten into a model once the shape settles.
RunConfig = dict[str, Any]

# Keys that only exist to drive expansion; they don't belong in a run config.
_EXPANSION_KEYS = ("layers", "layer_expansion_template")


def expand_layers(entry: RunConfig) -> list[RunConfig]:
    """Turn one batch entry into one run config per layer (depth/height).

    Layers come from ``entry["layers"]`` (e.g. a list of depths in mm). A lone
    ``entry["depth"]`` is treated as a single layer, so existing single-depth
    configs go through the same path. With neither, the entry is returned
    as a single unchanged run config.

    ``entry["layer_expansion_template"] maps config keys to format strings.
    Each is formatted with that run's own fields (``depth`` included), e.g.
    ``"pH (-{depth} mm)"``.

    Parameters
    ----------
    entry: dict
        The batch entry. Not modified.

    Returns
    -------
    list of dict
        One new run config per layer.
    """
    if "layers" in entry and "layer" in entry:
        raise ValueError(
            "Entry has both 'layers' and 'layer'; use 'layers' for a list "
            "or 'layer' for a single value, not both."
        )
    layers = entry.get("layers")
    if layers is None and "layer" in entry:
        layers = [entry["layer"]]

    if layers is None:
        return[_strip_expansion_keys(entry)]

    template = entry.get("layer_expansion_template", {})
    runs = []
    for layer in layers:
        run = _strip_expansion_keys(entry)
        run["layer"] = layer
        for key, fmt in template.items():
            try:
                run[key] = fmt.format(**run)
            except KeyError as missing:
                raise KeyError(
                    f"layer_expansion_template[{key!r}] = {fmt!r} refers to "
                    f"{missing}, which is not a field of this run config. "
                    f"Available fields: {sorted(run)}"
                ) from None
        runs.append(run)
    return runs


def _strip_expansion_keys(entry: RunConfig) -> RunConfig:
    run = deepcopy(entry)
    for key in _EXPANSION_KEYS:
        run.pop(key, None)
    return run
