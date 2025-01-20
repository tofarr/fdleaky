import pytest
from fdleaky.fdleaky import patch_fds, FDS


@pytest.fixture(autouse=True)
def setup_fdleaky():
    """Automatically patch file descriptors before each test"""
    patch_fds()
    yield
    FDS.clear()  # Clean up after each test
