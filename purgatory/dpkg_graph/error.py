"""DpkgGraph-specific exceptions."""


from .. import error


class DpkgGraphError(error.PurgatoryError):
    """Base class for all dpkg graph related errors."""


class EmptyAptCacheError(DpkgGraphError):
    """Raised if the Apt cache doesn't contain installed packages."""

    def __init__(self):
        msg = "The Apt cache doesn't contain any installed packages!"
        super().__init__(msg)


class PackageIsNotInstalledError(DpkgGraphError):
    """Raised if a package that is expected to be installed isn't."""

    def __init__(self, pkg):
        msg = ("The package '%s' was expected to be installed but it "
               "currently isn't installed!") % (pkg)
        super().__init__(msg)


class DependencyIsNotInstalledError(DpkgGraphError):
    """Raised if a dependency that is expected to be installed isn't."""

    def __init__(self, dep):
        msg = ("The dependency '%s' was expected to be installed but it "
               "currently isn't installed!") % (dep)
        super().__init__(msg)


class UnsupportedDependencyTypeError(DpkgGraphError):
    """Raised if a dependency has an unsupported type."""

    def __init__(self, dep):
        msg = ("The dependency '%s' has the unsupported type '%s'!") % (
            dep.rawstr, dep.rawtype)
        super().__init__(msg)
