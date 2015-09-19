"""Tests for purgatory.dpkg_graph with an empty dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import tempfile

import purgatory.dpkg_graph

from . import common


class TestEmptyDpkgGraph(common.PurgatoryTestCase):
    """Tests for purgatory.dpkg_graph with an empty dpkg status database."""

    def test_constructor(self):
        with tempfile.NamedTemporaryFile() as tf:
            # The temporary file is empty and hence an EmptyAptCacheError will
            # be raised.
            with self.assertRaises(purgatory.dpkg_graph.EmptyAptCacheError):
                purgatory.dpkg_graph.DpkgGraph(dpkg_db=tf.name)

            # Apt is still configured to use the empty temporary file.  This
            # setting will persist if no other dpkg_db will be specified and
            # hence an EmptyAptCacheError will be raised again.
            with self.assertRaises(purgatory.dpkg_graph.EmptyAptCacheError):
                purgatory.dpkg_graph.DpkgGraph()
