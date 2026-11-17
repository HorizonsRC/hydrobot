"""Guards against code that newer Python, numpy or pandas versions break.

HOW THESE TESTS WORK
--------------------
They read the package's own source and look for patterns that stop working as
the libraries move on. None of them run hydrobot's logic. Each one exists
because the pattern was found in the code once and should not come back.

The matching rule for pandas is in ``pyproject.toml``: ``filterwarnings`` turns
every ``Pandas4Warning`` (something that stops working in pandas 4) into a test
failure, for any code a test runs. These tests cover what that cannot: code no
test runs, and things that are not pandas.
"""
from pandas.tests.indexing.multiindex.test_indexing_slow import m

import ast
import pathlib
import warnings

import pytest

PACKAGE = pathlib.Path(__file__).parent.parent / "hydrobot"
SOURCES = sorted(PACKAGE.rglob("*.py"))

# Names numpy 2 removed. Using one raises AttributeError, but only when that
# line runs, which for rarely used code can be a long time after the upgrade.
REMOVED_NUMPY_NAMES = {
    "Inf",
    "Infinity",
    "infty",
    "NaN",
    "NAN",
    "NINF",
    "PZERO",
    "NZERO",
    "float_",
    "complex_",
    "longfloat",
    "cfloat",
    "string_",
    "unicode_",
    "bool8",
    "object0",
    "round_",
    "product",
    "cumproduct",
    "alltrue",
    "sometrue",
    "asfarray",
    "fing_common_type",
    "cast",
}


def name_of(path: pathlib.Path) -> str:
    """Return the path relative to the package, for test ids."""
    return str(path.relative_to(PACKAGE))


@pytest.mark.parametrize("path", SOURCES, ids=name_of)
def test_the_file_compiles_without_syntax_warnings(path):
    r"""Python warns about things it will make errors, such as ``"\d"`` in a string.

    The filter is set here so that the test does not depend on how pytest, or
    the person running it, has configured warnings.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", SyntaxWarning)

        compile(path.read_text(), str(path), "exec")


@pytest.mark.parametrize("path", SOURCES, ids=name_of)
def test_the_file_uses_no_numpy_names_that_numpy_2_removed(path):
    """No ``np.Inf``, ``np.NaN``, ``np.float`` and the like."""
    tree = ast.parse(path.read_text())
    found = [
        f"line {node.lineno}: {node.value.id}.{node.attr}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id in {"np", "numpy"}
        and node.attr in REMOVED_NUMPY_NAMES
    ]

    assert found == []
