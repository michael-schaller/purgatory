"""Common/shared code between tests."""

# Tests don't require docstrings:
# pylint: disable=missing-docstring


import functools
import pstats
import unittest

import purgatory.logging


def cprofile(test):
    """Decorator to profile a test with cprofile"""
    @functools.wraps(test)
    def cprofile_wrapper(self):
        """Wrapper that profiles a test"""
        import cProfile
        prof = cProfile.Profile()
        prof.runcall(test, self)  # Run test under profiler
        stats = pstats.Stats(prof)
        #stats.strip_dirs()
        stats.sort_stats("cumulative")
        stats.print_stats(40)
        #stats.print_callers(".*<file>.*<function>.*")
        #stats.print_callees(".*<file>.*<function>.*")
        #stats.print_callees(".*/graph.py.*__init__.*")
        #stats.print_callees(".*/graph.py.*outgoing_(nodes|edges).*")
        #stats.print_callees(
        #    ".*/dpkg_graph.py.*__init_nodes_and_edges_phase1.*")
        #stats.print_callees(".*/dpkg_graph.py.*__init__.*")
        stats.print_callers(".*/graph.py.*_outgoing_nodes_recursive_get_cache.*")
        self.fail("fail to see profiler stats")

    return cprofile_wrapper


class PurgatoryTestCase(unittest.TestCase):
    """Common TestCase base class for Purgatory."""

    @classmethod
    def setUpClass(cls):
        purgatory.logging.configure_root_logger()
