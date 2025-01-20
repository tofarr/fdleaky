import socket
import tempfile
import time
from unittest.mock import patch

from leaky.leaky import FDS, patch_fds

patch_fds()  # Re-patch to ensure socket is patched


def test_file_tracking():
    # Test file tracking
    with open(__file__, "r", encoding="UTF-8") as f:  # Use the test file itself
        file_id = id(f)
        assert file_id in FDS
    assert file_id not in FDS


def test_socket_tracking():
    # Test socket tracking
    sock = socket.socket()
    sock_id = id(sock)
    assert sock_id in FDS
    sock.close()
    assert sock_id not in FDS


def test_unclosed_detection():
    # Create an unclosed file
    with patch("leaky.leaky.UNCLOSED_TIMEOUT", 0.1):
        f = tempfile.NamedTemporaryFile()  # pylint: disable=R1732
        f.write(b"some_data")

        file_id = id(f)
        # Make sure the file has been registered
        assert file_id in FDS

        # Wait for the unclosed timeout
        time.sleep(0.5)

        # The file should be detected as unclosed and removed from tracking
        assert file_id not in FDS

        # Clean up
        f.close()
