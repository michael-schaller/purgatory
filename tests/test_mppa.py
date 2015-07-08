"""Tests for purgatory.mppa."""

import importlib
import unittest

import purgatory.logging

import purgatory.mppa
import apt  # Always needs to be imported after purgatory.mppa.


def setUpModule():
    """Module-wide setup."""
    purgatory.logging.configure_root_logger()


class TestMonkeyPatchPythonApt(unittest.TestCase):
    """Tests for purgatory.mppa."""

    def test_imported_but_unpatched_error(self):
        """Tests that the ImportedButUnpatchedError gets raised.

        This tests marks the apt module as unpatched and then forcefully
        reloads the apt module. This has to raise the ImportedButUnpatchedError
        exception.
        For an unknown reason self.assertRaises doesn't catch the exception but
        a manual try/except does. This might be because the purgatory.mppa
        module hasn't been fully imported on a failed module reimport/reload.
        """
        try:
            delattr(apt, "_monkey_patched_by_purgatory")
            raised = False
            try:
                importlib.reload(purgatory.mppa)
            except purgatory.mppa.ImportedButUnpatchedError:
                raised = True
            if not raised:
                self.fail("Exception purgatory.mppa.ImportedButUnpatchedError "
                          "hasn't been raised!")

        finally:
            # Mark again patched and force reimport of the apt module.
            setattr(apt, "_monkey_patched_by_purgatory", True)
            importlib.reload(purgatory.mppa)
