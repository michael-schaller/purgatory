"""Patches for python-apt to be applied by purgatory.mppa.

There is no coverage analysis for a lot of code in this module as dependending
on the python-apt version in use only a subset of the patches gets applied and
hence coverage varies greatly.
"""


def add_cache_installed_filter(modules, unused_python_apt_version):
    """Adds a filter for installed packages to apt.cache.

    TODO: Add this functionality to the upstream version of python-apt.
    """
    apt = modules["apt"]

    class InstalledFilter(apt.cache.Filter):  # pylint: disable=no-init
        """Filter that returns all installed packages."""

        def apply(self, pkg):  # noqa  # pragma: no cover  # pylint: disable=no-self-use,missing-docstring
            if pkg.is_installed:
                return True
            else:
                return False

    if not hasattr(apt.cache, "InstalledFilter"):  # pragma: no cover
        setattr(apt.cache, "InstalledFilter", InstalledFilter)
