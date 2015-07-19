"""Tests for purgatory.dpkg_graph."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import tempfile

import purgatory.dpkg_graph
import purgatory.logging

import tests.common
import tests.common_dpkg_graph


class TestEmptyDpkgGraph(tests.common.PurgatoryTestCase):
    """Tests for purgatory.dpkg_graph with an empty dpkg status database."""

    def test_constructor(self):
        with self.assertRaises(purgatory.dpkg_graph.EmptyAptCacheError):
            with tempfile.NamedTemporaryFile() as tf:
                purgatory.dpkg_graph.DpkgGraph(dpkg_db=tf.name)
