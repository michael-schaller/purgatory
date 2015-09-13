"""Abstract OrEdge base class."""


from . import edge
from . import error


class OrEdge(edge.Edge):  # pylint: disable=abstract-method
    """Represents an or-relationship between edges.

    OrEdge represents edges that are in an or-relationship.  This means that
    any of the edges in the or-relationship satisfies the hierarchie but it is
    not important which one.  One can also think of the or-relationship as a
    single edge with one from-node but multiple to-nodes.  Because of this Edge
    and OrEdge can't be mixed in the outgoing edges set of a node!

    Edges of type OrEdge have a probability depending on how many edges are
    in the or-relationship.  If there is one OrEdge then it has a probability
    of 1/1.  If there are two edges in the or-relationship both have a
    probability of 1/2.  If there are three edges they all have 1/3 and so on.
    """

    @property
    def is_edge_instance(self):
        """Returns True if this object is an Edge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return True

    @property
    def is_oredge_instance(self):
        """Returns True if this object is an OrEdge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return True

    @property
    def probability(self):
        """Returns the probability of this edge.

        The probability is based on the edges in parallel to this edge.  Each
        one has the same probability to be choosen.
        """
        if self._deleted:
            raise error.DeletedMemberInUseError(self)
        outgoing_edges = self.from_node.outgoing_edges

        # Division by zero should be impossible as there is always at least
        # the current edge and hence len(outgoing_edges) should be >= 1.
        return 1 / len(outgoing_edges)
