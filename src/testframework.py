import sys
import time
import unittest
from socket import *

from client_thread import ClientThread
from server_thread import ServerThread

timeout = 100  # Set the default timeout
winsize = 5  # Set the windows size
run_commands = False  # Set to True if you want to run commands
show_prints = False  # Set to True if you want to see the prints

intf = "lo"
netem_add = "sudo tc qdisc add dev {} root netem".format(intf)
netem_change = "sudo tc qdisc change dev {} root netem {}".format(intf, "{}")
netem_del = "sudo tc qdisc del dev {} root netem".format(intf)


def run_command_with_output(command, input=None, cwd=None, shell=True):
    """run command and retrieve output"""
    import subprocess
    try:
        process = subprocess.Popen(command, cwd=cwd, shell=shell, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
    except Exception:
        print("problem running command : \n   ", str(command))
    # no pipes set for stdin/stdout/stdout streams so does effectively only just wait for process ends  (same as process.wait()
    [stdoutdata, stderrdata] = process.communicate(input)
    if process.returncode:
        print(stderrdata)
        print("problem running command : \n   ", str(command), " ", process.returncode)
    return stdoutdata


def run_command(command, cwd=None, shell=True):
    """run command with no output piping"""
    import subprocess
    process = None
    try:
        process = subprocess.Popen(command, shell=shell, cwd=cwd)
        print(str(process))
    except Exception as inst:
        print("1. problem running command : \n   ", str(command), "\n problem : ", str(inst))
    process.communicate()  # wait for the process to end
    if process.returncode:
        print("2. problem running command : \n   ", str(command), " ", process.returncode)


class TestbTCPFramework(unittest.TestCase):
    """Test cases for bTCP"""

    def setUp(self):
        """Prepare for testing"""
        if run_commands:
            run_command(netem_add)
        self.server = ServerThread(winsize, timeout, show_prints)
        self.client = ClientThread(winsize, timeout, show_prints)

    def tearDown(self):
        """Clean up after testing"""
        if run_commands:
            run_command(netem_del)

    def test_ideal_network(self):
        """reliability over an ideal framework"""
        self.run_test()

    def test_flipping_network(self):
        """reliability over network with bit flips (which sometimes results in lower layer packet loss)"""
        if run_commands:
            run_command(netem_change.format("corrupt 1%"))
        self.run_test()

    def test_duplicates_network(self):
        """reliability over network with duplicate packets"""
        if run_commands:
            run_command(netem_change.format("duplicate 10%"))
        self.run_test()

    def test_lossy_network(self):
        """reliability over network with packet loss"""
        if run_commands:
            run_command(netem_change.format("loss 10% 25%"))
        self.run_test()

    def test_reordering_network(self):
        """reliability over network with packet reordering"""
        if run_commands:
            run_command(netem_change.format("delay 20ms reorder 25% 50%"))
        self.run_test()

    def test_delayed_network(self):
        """reliability over network with delay relative to the timeout value"""
        if run_commands:
            run_command(netem_change.format("delay "+str(timeout)+"ms 20ms"))
        self.run_test()

    def test_allbad_network(self):
        """reliability over network with all of the above problems"""
        if run_commands:
            run_command(netem_change.format("corrupt 1% duplicate 10% loss 10% 25% delay 20ms reorder 25% 50%"))
        self.run_test()

    def run_test(self):
        self.server.start()
        self.client.start()
        self.server.join()
        self.client.join()
        sent = self.client.get_sent_file()
        recv = self.server.get_recv_file()
        self.assertEqual(sent, recv)


if __name__ == "__main__":
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="bTCP tests")
    parser.add_argument("-w", "--window", help="Define bTCP window size used", type=int, default=100)
    parser.add_argument("-t", "--timeout", help="Define the timeout value used (ms)", type=int, default=timeout)
    args, extra = parser.parse_known_args()
    timeout = args.timeout
    winsize = args.window

    # Pass the extra arguments to unit test
    sys.argv[1:] = extra

    # Start test suite
    unittest.main()
