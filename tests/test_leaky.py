import socket
import tempfile
import time

from leaky import leaky

leaky.INTERVAL = 0.1
leaky.UNCLOSED_TIMEOUT = 0.1
leaky.patch_fds()


def test_file_tracking():
    # Test file tracking
    with open(__file__, "r", encoding="UTF-8") as f:  # Use the test file itself
        file_id = id(f)
        assert file_id in leaky.FDS
    assert file_id not in leaky.FDS


def test_socket_tracking():
    # Test socket tracking
    sock = socket.socket()
    sock_id = id(sock)
    assert sock_id in leaky.FDS
    sock.close()
    assert sock_id not in leaky.FDS


def test_unclosed_detection():
    # Get number of open files
    num_open_files = len(leaky.FDS)

    # Create an unclosed file
    f = tempfile.NamedTemporaryFile()  # pylint: disable=R1732

    # Make sure the file has been registered
    assert len(leaky.FDS) == num_open_files + 1

    # Wait for the unclosed timeout
    time.sleep(1)

    # The file should be detected as unclosed and removed from tracking
    assert len(leaky.FDS) == num_open_files

    # Clean up
    f.close()
