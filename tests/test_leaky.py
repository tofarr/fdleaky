import socket
import tempfile
import time

from leaky.leaky import FDS, UNCLOSED_TIMEOUT


def test_file_tracking():
    # Test file tracking
    with open(__file__, "r") as f:  # Use the test file itself
        file_id = id(f)
        assert file_id in FDS
    assert file_id not in FDS


def test_socket_tracking():
    # Test socket tracking
    from leaky.leaky import patch_fds  # Ensure socket is patched

    patch_fds()  # Re-patch to ensure socket is patched
    sock = socket.socket()
    sock_id = id(sock)
    assert sock_id in FDS
    sock.close()
    assert sock_id not in FDS


def test_unclosed_detection():

    # Create an unclosed file
    f = tempfile.NamedTemporaryFile()
    file_id = id(f)

    # Wait for the unclosed timeout
    time.sleep(UNCLOSED_TIMEOUT + 1)

    # The file should be detected as unclosed and removed from tracking
    assert file_id not in FDS

    # Clean up
    f.close()
