"""Tests for purgatory.dpkg_graph.mppa."""


import purgatory.logging
import purgatory.dpkg_graph.mppa

import apt      # Needs to be imported after purgatory.dpkg_graph.mppa.
import apt_pkg  # Needs to be imported after purgatory.dpkg_graph.mppa.

from . import common


class TestMonkeyPatchPythonApt(common.PurgatoryTestCase):
    """Tests for purgatory.dpkg_graph.mppa."""

    def test_imported_but_unpatched_error(self):
        """Tests that the ImportedButUnpatchedError gets raised."""
        # Check that the apt and apt_pkg modules have been patched by importing
        # purgatory.dpkg_graph.
        self.assertTrue(hasattr(apt, "_monkey_patched_by_purgatory"))
        self.assertTrue(hasattr(apt_pkg, "_monkey_patched_by_purgatory"))

        # Fake that the apt module hasn't been already patched and then try to
        # patch it.  This has to raise the ImportedButUnpatchedError exception
        # as under normal conditions this would indicate that the apt module
        # has been imported and used before it got patched.
        delattr(apt, "_monkey_patched_by_purgatory")
        self.assertRaises(
            purgatory.dpkg_graph.mppa.ImportedButUnpatchedError,
            purgatory.dpkg_graph.mppa.monkey_patch_python_apt)
        setattr(apt, "_monkey_patched_by_purgatory", True)

        # Fake that the apt_pkg module hasn't been already patched and then try
        # to patch it.  This has to raise the ImportedButUnpatchedError
        # exception as under normal conditions this would indicate that the
        # apt_pkg module has been imported and used before it got patched.
        delattr(apt_pkg, "_monkey_patched_by_purgatory")
        self.assertRaises(
            purgatory.dpkg_graph.mppa.ImportedButUnpatchedError,
            purgatory.dpkg_graph.mppa.monkey_patch_python_apt)
        setattr(apt_pkg, "_monkey_patched_by_purgatory", True)
