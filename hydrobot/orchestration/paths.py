"""Where a run's files live on disk, and what they are called.

Pure functions: they build paths and names from a run config and never touch
the file system. Keeping this in ONE place means the folder layout can change
(or differ per council) without anything else knowing about it.

Layout (see the Gen 500 project scope):

    <root>/<measurement_folder>/<batch>/<site>/                 unlayered site
    <root>/<measurement_folder>/<batch>/<site>/<layer_label>/   layered site

File names are ``<batch>_<data_source_code>_<site_code>[_<layer_label>]_<purpose>.<ext>``
(e.g. ``500_DO_TCO_config.yaml`` or ``500_DO_TCO_-500mm_config.yaml``). Every
file repeats its batch, source and site so it can still be identified if the
folder structure is ever scrambled by.

Run config keys used here (``layer_label`` is optional):

    batch               the batch number, e.g. 501
    measurement_folder  the folder name for the measurement, e.g. "Dissolved Oxygen"
    data_source_code    short code for the data source, e.g. "DO"
    site                the site name, e.g. "Manawatu at Teachers College"
    site_code           the site's short code, e.g. "TCO"
    layer_label         how this layer reads in paths, e.g. "-500mm"
"""

from pathlib import Path

from hydrobot.orchestration.expansion import RunConfig

# Characters Windows (NTFS) doesn't allow in a file or folder name, plus the
# path separators. Refusing them up front beats a confusing failure later.

_ILLEGAL_CHARACTERS = set('\\/:*?"<>|') | {chr(c) for c in range (32)}

_DIR_KEYS = ("batch", "measurement_folder", "site")
_FILE_KEYS = ("batch", "data_source_code", "site_code")


def run_dir(root: Path | str, run: RunConfig) -> Path:
    """The folder that holds all of one run's files.

    A layered run (one with a ``layer_label``) gets an extra folder level
    below its site; an unlayered run doesn't.
    """
    _require(run, _DIR_KEYS)
    parts = [
        _segment("measurement_folder", run["measurement_folder"]),
        _segment("batch", run["batch"]),
        _segment("site", run["site"]),
    ]
    if run.get("layer_label") is not None:
        parts.append(_segment("layer_label", run["layer_label"]))
    return Path(root).joinpath(*parts)


def run_filename(run: RunConfig, purpose: str, extension: str) -> str:
    """The name of one of a run's files, e.g. ``500_DO_TCO_config.yaml``.

    ``purpose`` says what the file is ("config", "script", "data", ...) and
    ``extension`` has no leading dot ("yaml", "py", "xml", "hts").
    """
    _require(run, _FILE_KEYS)
    pieces = [
        _segment("batch", run["batch"]),
        _segment("data_source_code", run["data_source_code"]),
        _segment("site_code", run["site_code"]),
    ]
    if run.get("layer_label") is not None:
        pieces.append(_segment("layer_label", run["layer_label"]))
    pieces.append(_segment("purpose", purpose))
    return "_".join(pieces) + "." + _segment("extension", extension)


def _require(run: RunConfig, keys: tuple[str, ...]) -> None:
    """Fail clearly if the run config lacks anything needed for a path."""
    missing = [k for k in keys if run.get(k) is None]
    if missing:
        raise ValueError(
            f"Run config is missing {missing}, which are needed to build file "
            f"paths. (For site_code, run the fill stage first.)"
        )


def _segment(name: str, value: object) -> str:
    """Check one piece of a path or file name is safe, and return it as text.

    Raises rather than quietly altering the value: a silently change site
    name would give files a different identity from the config they camr from.
    """
    text = str(value)
    problem = None
    if not text or text != text.strip():
        problem = "is empty or has leading/trailing spaces"
    elif text in {".", ".."} or text.endswith("."):
        problem = "is '.', '..', or ends with a dot"
    elif any(ch in _ILLEGAL_CHARACTERS for ch in text):
        problem = 'contains one of \\ / : * ? < > | or a control character'
    if problem:
        raise ValueError(f"{name}={value!r} can't be used in a file path: it {problem}.")
    return text

