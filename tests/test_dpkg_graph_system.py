"""Tests for purgatory.dpkg_graph with the system dpkg status database."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import logging

import purgatory.dpkg_graph

from . import common
from . import common_dpkg_graph


class TestSystemDpkgGraph(
        common.PurgatoryTestCase,
        common_dpkg_graph.CommonDpkgGraphTestsMixin):
    """Tests for purgatory.dpkg_graph with the system's dpkg database."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__graph = None

    def setUp(self):
        super().setUp()
        self.graph.unmark_deleted()

    @property
    def graph(self):
        if self.__graph is None:
            logging.debug(
                "Initializing DpkgGraph (local system amd64 minbase) ...")
            self.__graph = purgatory.dpkg_graph.DpkgGraph(
                dpkg_db="/var/lib/dpkg/status")
            logging.debug("DpkgGraph initialized")
        return self.__graph
