import socket
import tempfile
import time
from unittest.mock import MagicMock, patch

from fdleaky import fdleaky

# Monkey patches...
fdleaky.sys = MagicMock()
fdleaky.termios = MagicMock()
fdleaky.fcntl = MagicMock()
fdleaky.INTERVAL = 0.1
fdleaky.patch_fds()
fdleaky.start_sample_on_key_press()


def test_file_tracking():
    # Test file tracking
    with open(__file__, "r", encoding="UTF-8") as f:  # Use the test file itself
        file_id = id(f)
        assert file_id in fdleaky.FDS
    assert file_id not in fdleaky.FDS


def test_socket_tracking():
    # Test socket tracking
    sock = socket.socket()
    sock_id = id(sock)
    assert sock_id in fdleaky.FDS
    sock.close()
    assert sock_id not in fdleaky.FDS


def test_unclosed_detection():
    # Get number of open files
    num_open_files = len(fdleaky.FDS)

    # Create an unclosed file
    f = tempfile.NamedTemporaryFile()  # pylint: disable=R1732

    # Make sure the file has been registered
    assert len(fdleaky.FDS) == num_open_files + 1

    # Wait for key press
    fdleaky.sys.stdin.read.return_value = "p"
    time.sleep(1)

    # The file should be detected as unclosed and removed from tracking
    assert len(fdleaky.FDS) == num_open_files

    # Clean up
    f.close()
