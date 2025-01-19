import pytest
from leaky.leaky import patch_fds, FDS

@pytest.fixture(autouse=True)
def setup_leaky():
    """Automatically patch file descriptors before each test"""
    patch_fds()
    yield
    FDS.clear()  # Clean up after each test