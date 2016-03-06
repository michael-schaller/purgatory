"""Purgatory command line interface."""


import argparse
import logging
import os
import sys

from . import dpkg_graph
import purgatory.logging


def _list_leaf_packages(parsed_args):
    """Lists the leaf packages.

    Args:
        parsed_args: The parsed command line arguments.

    Returns:
        Returns the exit code.
    """
    logging.debug("Initializing dpkg graph ...")
    graph = dpkg_graph.DpkgGraph(
        ignore_recommends=parsed_args.ignore_recommends,
        dpkg_db=parsed_args.dpkg_status_database)

    logging.debug("Determining leafs of the dpkg graph ...")
    leafs = graph.leafs
    logging.debug("  Leafs: %d", len(leafs))

    logging.debug("Listing leafs of the dpkg graph ...")
    leafs_str = []
    for leaf in leafs:
        # Most leafs consist only of a single PackageNode. The only exception
        # are leaf cycles that consist of several PackageNodes and
        # DependencyNodes to glue the PackageNodes together. Leaf cycles can
        # be arbitrarily complex and hence it is impossible to print the
        # relationship between the nodes in a leaf cycle as text output. So
        # only the PackageNodes are printed.
        leaf_str = []
        for node in leaf:
            if isinstance(node, dpkg_graph.package_node.PackageNode):
                leaf_str.append(str(node))
        leaf_str.sort()
        leaf_str = " ".join(leaf_str)
        leafs_str.append(leaf_str)
    leafs_str.sort()
    for leaf_str in leafs_str:
        print(leaf_str)

    return 0


def _purge_packages(parsed_args):
    """Purges the specified packages.

    Args:
        parsed_args: The parsed command line arguments.

    Returns:
        Returns the exit code.
    """
    logging.debug("Initializing dpkg graph ...")
    graph = dpkg_graph.DpkgGraph(
        ignore_recommends=parsed_args.ignore_recommends,
        dpkg_db=parsed_args.dpkg_status_database)

    logging.debug("Building map of package names to packages nodes ...")
    installed_pkg_to_pkg_node = {
        str(pkg_node): pkg_node for pkg_node in graph.package_nodes}

    logging.debug(
        "Checking if the packages to purge are part of the dpkg graph ...")
    parsed_args.packages.sort()
    pkg_nodes_to_purge = set()
    for pkg_to_purge in parsed_args.packages:
        pkg_node_to_purge = installed_pkg_to_pkg_node.get(pkg_to_purge)
        if pkg_node_to_purge is None:  # pragma: no cover
            logging.info(
                "The package '%s' is not installed and hence doesn't need to "
                "be marked for removal.", pkg_to_purge)
        else:
            pkg_nodes_to_purge.add(pkg_node_to_purge)

    logging.debug(
        "Mark the packages to purge and packages that are obsoleted by this "
        "operation for removal ...")
    graph.mark_members_including_obsolete_deleted(pkg_nodes_to_purge)

    logging.debug("Getting list of packages marked for removal ...")
    deleted_pkgs = [str(pkg_node) for pkg_node in graph.deleted_package_nodes]
    deleted_pkgs.sort()
    logging.debug("%d packages marked for removal.", len(deleted_pkgs))
    print(
        "Run this apt command to purge the requested packages and all "
        "packages that would be obsoleted by this operation:")
    cmd = "apt purge %s" % " ".join(deleted_pkgs)
    if os.geteuid() != 0:
        cmd = "sudo " + cmd
    print(cmd)

    return 0


def _parse_args(args):
    """Parses the command line arguments.

    Args:
        args: Command line arguments (sys.argv[1:]).

    Returns:
        Returns the namespace object returned by argparse.parse_args().
    """
    # Parent parser to parse commonly used optional arguments.
    common_args_parser = argparse.ArgumentParser(add_help=False)
    common_args_parser.add_argument(
        "-v", "--verbose", default=False, action="store_true",
        help="verbose output / debug logging")
    common_args_parser.add_argument(
        "-d", "--dpkg-status-database", default="/var/lib/dpkg/status",
        metavar="<dpkg status db>",
        help=("the dpkg status database file to use; defaults to "
              "'/var/lib/dpkg/status'"))
    common_args_parser.add_argument(
        "-i", "--ignore-recommends", default=False, action="store_true",
        help=("ignore recommends relationship between packages; typically "
              "allows to purge more packages but might result in unusual or "
              "undesirable configurations; use with great care"))

    # Actual parser with all the subparsers for the commands. Giving a command
    # is mandatory.
    root_parser = argparse.ArgumentParser(
        prog="purgatory", parents=[common_args_parser])

    subparsers = root_parser.add_subparsers(
        dest="command", metavar="<command>")
    subparsers.required = True

    # 'leafs' subcommand.
    subparsers.add_parser(
        "leafs", parents=[common_args_parser],
        help=("list the leaf packages; leaf packages are easily purgable "
              "because no other packages depend on them"))

    # 'purge' subcommand.
    purge_parser = subparsers.add_parser(
        "purge", parents=[common_args_parser],
        help=("purges the specified packages and packages that will be "
              "obsoleted by this operation"))
    purge_parser.add_argument(
        "packages", metavar="<package>", nargs="+", help="package to purge")

    # Parse command line arguments and determine the function to handle the
    # command.
    parsed_args = root_parser.parse_args(args)
    cmd_to_handler = {
        "leafs": _list_leaf_packages,
        "purge": _purge_packages,
    }
    handler = cmd_to_handler.get(parsed_args.command, None)
    if handler is None:  # pragma: no cover
        # cmd_to_handler needs to be updated.
        root_parser.error(
            "no registered handler for command '%s'." % parsed_args.command)
    else:
        parsed_args.command_handler = handler

    return parsed_args


def cli(args):
    """Purgatory command line interface.

    Args:
        args: Command line arguments (sys.argv[1:]).

    Returns:
        Returns the exit code of the program.
    """
    parsed_args = _parse_args(args)
    purgatory.logging.init_cli_logging(debug=parsed_args.verbose)
    return parsed_args.command_handler(parsed_args)


def main():  # pragma: no cover
    """Main entry point of the Purgatory command line interface."""
    sys.exit(cli(sys.argv[1:]))


if __name__ == "__main__":  # pragma: no cover
    main()
