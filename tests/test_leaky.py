import socket
import tempfile
import time

from leaky.leaky import FDS, UNCLOSED_TIMEOUT, patch_fds

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
    f = tempfile.NamedTemporaryFile()  # pylint: disable=R1732
    file_id = id(f)

    # Wait for the unclosed timeout
    time.sleep(UNCLOSED_TIMEOUT + 1)

    # The file should be detected as unclosed and removed from tracking
    assert file_id not in FDS

    # Clean up
    f.close()
