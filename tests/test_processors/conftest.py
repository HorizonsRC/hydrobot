"""Shared setup for the Processor tests."""

import pytest
from annalist.annalist import Annalist


@pytest.fixture(autouse=True)
def _annalist_configured():
    """Configure Annalist for every test in this folder.

    The Processor's methods are decorated with ``@ClassLogger``, which refuses
    to run until Annalist has been configured (as a real script does at the
    top). Nothing here reads the log; it just has to be set up.
    """
    Annalist().configure(analyst_name="test_processors")
