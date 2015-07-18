"""Common/shared code between tests."""

import functools
import pstats


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
        #stats.print_callees(".*graph.py.*outgoing_(nodes|edges).*")
        self.fail("fail to see profiler stats")

    return cprofile_wrapper
