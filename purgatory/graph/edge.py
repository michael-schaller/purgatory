"""Abstract Edge base class."""


import abc

from . import const
from . import error
from . import member


class Edge(member.Member):
    """Abstract Edge base class.

    This class represents a directed edge in the Graph that isn't in an or-
    relationship with other edges.
    """

    def __init__(self, from_node, to_node):
        # Check
        if not from_node.is_node_instance:
            raise error.NotANodeError(from_node)
        if not to_node.is_node_instance:
            raise error.NotANodeError(to_node)

        # Private
        self.__from_node = from_node
        self.__to_node = to_node

        # Init
        uid = self._nodes_to_edge_uid(from_node, to_node)
        super().__init__(uid)

        from_node._add_outgoing_edge(self)  # pylint: disable=protected-access
        try:
            to_node._add_incoming_edge(self)  # noqa  # pylint: disable=protected-access
        except:
            # Remove the previously added edge from the outgoing edges set
            # again and then reraise the exception.
            from_node._outgoing_edges.remove(self)  # noqa  # pylint: disable=protected-access
            raise

    @abc.abstractmethod
    def _nodes_to_edge_uid(self, from_node, to_node):
        """Returns an uid for this directed edge based on the nodes."""

    @property
    def is_edge_instance(self):
        """Returns True if this object is an Edge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return True

    @property
    def probability(self):
        """Returns the probability of this edge. Defaults to 1.0."""
        if self._deleted:
            raise error.DeletedMemberInUseError(self)
        return 1.0

    @property
    def from_node(self):
        """Returns the source (from) node of the edge."""
        return self.__from_node

    @property
    def to_node(self):
        """Returns the destination (to) node of the edge."""
        return self.__to_node

    def mark_deleted(self):
        """Marks the edge as deleted. This might also affect its outgoing node.

        As a graph represents a hierarchie the nodes that are above a node also
        need to be marked as deleted as long as there is no alternative edge
        that ensures that the hierarchie isn't violated.
        """
        if self._deleted:  # pragma: no cover
            return  # Stop recursion

        # set.add and set.remove is slow. Use |= and -= and the same set as
        # much as possible.
        self_set = set((self,))

        # Get all needed data from the edge and then mark it as deleted.
        graph = self.graph
        from_node = self.__from_node
        to_node = self.__to_node
        probability = self.probability
        self._deleted = True
        graph._deleted_edges |= self_set

        # Update/invalidate incoming caches:
        # ----------------------------------

        # Update incoming edges cache set of the from node.
        if to_node._incoming_edges_without_deleted is None:  # noqa  # pylint: disable=protected-access
            to_node._incoming_edges_without_deleted = set(  # noqa  # pylint: disable=protected-access
                to_node._incoming_edges - self_set)  # noqa  # pylint: disable=protected-access
        else:
            to_node._incoming_edges_without_deleted -= self_set  # noqa  # pylint: disable=protected-access

        # Update incoming nodes cache set of the from node.
        if to_node._incoming_nodes_without_deleted is None:  # noqa  # pylint: disable=protected-access
            to_node._incoming_nodes_without_deleted = set(  # noqa  # pylint: disable=protected-access
                to_node._incoming_nodes - set((from_node,)))  # noqa  # pylint: disable=protected-access
        else:
            to_node._incoming_nodes_without_deleted -= set((from_node,))  # noqa  # pylint: disable=protected-access

        # The incoming edges and nodes sets without the deleted nodes have been
        # touched on this node.  Mark this node as touched to reset it on
        # Graph.unmark_deleted().
        to_node._incoming_without_deleted_touched = True  # noqa  # pylint: disable=protected-access

        # Increase cache level of the incoming recursive nodes to invalidate
        # these caches graph-wide.  Once a single cache will be accessed it
        # uses this information to detect that the cache could be invalid and
        # then evaluates if the cache is still valid by its built at cache
        # level and invalidated at cache level fields.  See the
        # _incoming_nodes_recursive_get_cache method for details.
        graph._mark_deleted_incoming_cache_level += 1
        graph_cl = graph._mark_deleted_incoming_cache_level  # noqa  # pylint: disable=protected-access
        from_node._incoming_nodes_recursive_invalidated_at_cl = graph_cl  # noqa  # pylint: disable=protected-access

        # Update/invalidate outgoing caches:
        # ----------------------------------

        # The outgoing caches only need to be recalculated if an OrEdge has
        # been marked as deleted that has other OrEdges in parallel as marking
        # an edge as deleted only affects the nodes and edges above (incoming).
        # If an Edge or OrEdge with probability 1.0 will be marked as deleted
        # then this will also mark its from node and all nodes above as deleted
        # and hence there is no node or edge above that would need their cache
        # updated/invalidated and all nodes and edges below it still have a
        # valid cache.
        if probability < 1.0:
            # Update outgoing edges cache set of the from node.
            # Note: from_node._outgoing_edges_without_deleted is always
            # initialized because checking the probability initializes it.
            from_node._outgoing_edges_without_deleted -= self_set  # noqa  # pylint: disable=protected-access

            # Update outgoing nodes cache set of the from node.
            if from_node._outgoing_nodes_without_deleted is None:  # noqa  # pylint: disable=protected-access
                from_node._outgoing_nodes_without_deleted = set(  # noqa  # pylint: disable=protected-access
                    from_node._outgoing_nodes - set((to_node,)))  # noqa  # pylint: disable=protected-access
            else:
                from_node._outgoing_nodes_without_deleted -= set((to_node,))  # noqa  # pylint: disable=protected-access

            # The incoming edges and nodes sets without the deleted nodes have
            # been touched on this node.  Mark this node as touched to reset it
            # on Graph.unmark_deleted().
            from_node._outgoing_without_deleted_touched = True  # noqa  # pylint: disable=protected-access

            # Increase cache level of the outgoing recursive nodes to
            # invalidate these caches graph-wide.  Once a single cache will be
            # accessed it uses this information to detect that the cache could
            # be invalid and then evaluates if the cache is still valid by its
            # built at cache level and invalidated at cache level fields.
            # see the _outgoing_nodes_recursive_get_cache method for details.
            graph._mark_deleted_outgoing_cache_level += 1
            graph_cl = graph._mark_deleted_outgoing_cache_level  # noqa  # pylint: disable=protected-access
            from_node._outgoing_nodes_recursive_invalidated_at_cl = graph_cl  # noqa  # pylint: disable=protected-access

        # Check if the hierarchy is violated and mark the from-node as deleted
        # if necessary.
        if abs(probability - 1.0) < const.EPSILON:
            from_node.mark_deleted()
