"""Tests for purgatory.cli."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import io
import logging
import textwrap
import unittest
import unittest.mock

import purgatory.cli

from . import common


def _log_stdout_stderr(stdout, stderr):
    stdout = stdout.rstrip()
    stderr = stderr.rstrip()
    if stdout:
        logging.debug("Test stdout:\n%s", stdout)
    if stderr:
        logging.debug("Test stderr:\n%s", stderr)


class TestCLI(common.PurgatoryTestCase):

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_cli_no_command(self, mock_stdout, mock_stderr):
        args = []

        expected_exit_code = 2  # Parse error
        expected_stdout = ""
        expected_in_stderr = (
            "error: the following arguments are required: <command>"
        )

        try:
            exit_code = purgatory.cli.cli(args)
        except SystemExit as ex:
            exit_code = ex.code
        stdout = mock_stdout.getvalue()
        stderr = mock_stderr.getvalue()
        _log_stdout_stderr(stdout, stderr)

        self.assertEquals(exit_code, expected_exit_code)
        self.assertEquals(expected_stdout, stdout)
        self.assertIn(expected_in_stderr, stderr)

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_cli_leafs_command(self, mock_stdout, mock_stderr):
        args = [
            "leafs",
            "--dpkg-status-database",
            "../test-data/dpkg/jessie-amd64-minbase-dpkg-status-db.gz"
        ]

        expected_exit_code = 0
        expected_stdout = textwrap.dedent("""\
            apt
            base-passwd
            bash
            bsdutils
            diffutils
            findutils
            gcc-4.8-base
            grep
            gzip
            hostname
            init
            libc-bin
            login
            ncurses-base
            ncurses-bin
            sed
        """)
        expected_stderr = ""

        try:
            exit_code = purgatory.cli.cli(args)
        except SystemExit as ex:
            exit_code = ex.code
        stdout = mock_stdout.getvalue()
        stderr = mock_stderr.getvalue()
        _log_stdout_stderr(stdout, stderr)

        self.assertEquals(exit_code, expected_exit_code)
        self.assertEquals(expected_stdout, stdout)
        self.assertEquals(expected_stderr, stderr)

    @unittest.mock.patch("sys.stderr", new_callable=io.StringIO)
    @unittest.mock.patch("sys.stdout", new_callable=io.StringIO)
    def test_cli_purge_apt(self, mock_stdout, mock_stderr):
        args = [
            "purge",
            "--dpkg-status-database",
            "../test-data/dpkg/jessie-amd64-minbase-dpkg-status-db.gz",
            "apt"
        ]

        expected_exit_code = 0
        expected_in_stdout = (
            "sudo apt purge apt debian-archive-keyring gnupg gpgv "
            "libapt-pkg4.12 libreadline6 libstdc++6 libusb-0.1-4 "
            "readline-common"
        )
        expected_stderr = ""

        try:
            exit_code = purgatory.cli.cli(args)
        except SystemExit as ex:
            exit_code = ex.code
        stdout = mock_stdout.getvalue()
        stderr = mock_stderr.getvalue()
        _log_stdout_stderr(stdout, stderr)

        self.assertEquals(exit_code, expected_exit_code)
        self.assertIn(expected_in_stdout, stdout)
        self.assertEquals(expected_stderr, stderr)
