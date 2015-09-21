"""A graph node that has edges to installed packages that need to be kept."""


from . import error

from .. import graph


class KeepNode(graph.Node):
    """Node that has edges to installed packages that need to be kept.

    The Purgatory command line tool allows to specify installed packages that
    need to be kept.  A dpkg graph has a single KeepNode and KeepEdges to all
    the PackageNodes that need to be kept.  Furthermore a KeepNode can't have
    incoming edges and hence will be always a leaf node.
    """

    def __init__(self):
        """KeepNode constructor.

        The node uid is '!!KEEP!!' for all KeepNodes which ensures that only
        one keep node can be in each graph. Furthermore '!!KEEP!!' is an
        invalid package name according to the debian policy manual:
        https://www.debian.org/doc/debian-policy/ch-controlfields.html#s-f-Source  # noqa  # pylint: disable=line-too-long
        """
        super().__init__("!!KEEP!!")

    def _init_str(self):
        """Initializes self._str for self.__str__."""
        self._str = "keep"

    def _add_incoming_edge(self, edge):
        """Registers an edge as incoming edge with this node.

        KeepNodes can't have incoming edges as they are required to be a leaf
        of the graph.  An attempt to add an incoming edge will raise a
        KeepNodeMustBeLeafError.
        """
        raise error.KeepNodeMustBeLeafError()

    def mark_deleted(self):
        """Marks the node and its incoming and outgoing edges as deleted.

        KeepNodes can't be marked as deleted as KeepNodes and all nodes below
        them need to be kept.  If a node or edge below a KeepNode would be
        marked as deleted then this would in turn mark the KeepNode as deleted.
        Marking a KeepNode as deleted raises a
        KeepNodeCanNotBeMarkedDeletedError.
        """
        raise error.KeepNodeCanNotBeMarkedDeletedError()
