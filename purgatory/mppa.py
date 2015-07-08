"""Monkey-patch python-apt.

This module patches python-apt with code that isn't available in the currently
in use version of python-apt. Every docstring in this module has to either
specify since which python-apt version the code is supported or has to specify
a TODO to upstream the code.
"""

import importlib
import logging
import sys

import pkg_resources

import purgatory.mppa_patches as patches


_APT_MODULE_NAMES = ["apt", "apt_pkg"]
_PYTHON_APT_VERSION = pkg_resources.get_distribution("python-apt").version  # noqa  # pylint: disable=maybe-no-member


class ImportedButUnpatchedError(Exception):
    """Raised if an Apt module has been already imported but isn't patched."""

    def __init__(self, module):
        msg = ("The module '%s' is already imported but hasn't been monkey-"
               "patched, yet. This is an indicator that the unpatched version "
               "of the module '%s' is already in use. This is a programming "
               "error as the '%s' module should always be imported before any "
               "Apt module.") % (module, module, __name__)
        super().__init__(msg)


def _check_already_imported_modules():
    """Ensure that the imported Apt modules have been monkey-patched."""
    for module_name in sys.modules:
        if module_name in _APT_MODULE_NAMES:
            module = importlib.import_module(module_name)
            if not hasattr(module, "_monkey_patched_by_purgatory"):
                raise ImportedButUnpatchedError(module_name)


def _ensure_modules_are_imported():
    """Ensure that the Apt modules have been imported."""
    modules = {}
    for module_name in _APT_MODULE_NAMES:
        module = importlib.import_module(module_name)
        modules[module_name] = module

    logging.debug("Apt version: %s", modules["apt_pkg"].VERSION)
    logging.debug("python-apt version: %s", _PYTHON_APT_VERSION)

    return modules


def _apply_monkey_patches(modules):
    """Applies the monkey-patches to python-apt."""
    logging.debug("Applying monkey-patches to python-apt ...")
    patches.add_cache_installed_filter(modules, _PYTHON_APT_VERSION)


def _mark_as_monkey_patched(modules):
    """Mark the Apt modules as monkey-patched."""
    for module in modules.values():
        setattr(module, "_monkey_patched_by_purgatory", True)
    logging.debug("Successfully monkey-patched python-apt")


def _monkey_patch_python_apt():
    """Monkey-patch python-apt."""
    _check_already_imported_modules()
    modules = _ensure_modules_are_imported()
    _apply_monkey_patches(modules)
    _mark_as_monkey_patched(modules)


_monkey_patch_python_apt()
