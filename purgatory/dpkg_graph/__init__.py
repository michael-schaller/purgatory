"""Graph representing installed packages in the dpkg status database.

The DpkgGraph is a massively simplified graph compared to a full Apt graph.  It
only contains what is relevant for Purgatory - which is a representation of the
dpkg status database and data needed to remove packages.

Simplifications:
* Only the dpkg status database instead of the complete Apt database.
* Only installed packages.  This allows to collapse a respective Package and
  Version object into a single InstalledPackageNode.
* Only PreDepends, Depends and Recommends dependency types.  The dependencies
  are collapsed as much as possible.
* Only installed target versions and their respective packages.
"""


# Ignore all flake8 issues because F401 issues (unused imports) can't be
# silenced otherwise.
# gflake8: noqa

# Silence unused import warnings.
# pylint: disable=unused-import


# Monkey-patch python-apt.  This is needed in case of older python-apt
# versions that don't have the needed patches.  This needs to happen before
# any python-apt module gets imported.
from . import mppa
mppa.monkey_patch_python_apt()


# DpkgGraph-specific exceptions.
from .error import DependencyIsNotInstalledError
from .error import DpkgGraphError
from .error import EmptyAptCacheError
from .error import KeepNodeCanNotBeMarkedDeletedError
from .error import KeepNodeMustBeLeafError
from .error import PackageIsNotInstalledError
from .error import UnsupportedDependencyTypeError

# DpkgGraph-specific classes.
from .dependency_edge import DependencyEdge
from .dependency_node import DependencyNode
from .dpkg_graph import DpkgGraph
from .keep_node import KeepNode
from .package_node import PackageNode
from .target_edge import TargetEdge
