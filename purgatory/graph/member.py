"""Abstract base class for members (nodes, edges) of a Graph."""


import abc


from . import error


class Member(abc.ABC):
    """Abstract base class for members (nodes, edges) of a Graph."""

    __uid_counter = 0
    __uid_to_uid_intid = {}  # uid:uid_intid

    def __init__(self, uid):
        # Get unique integer id based on the uid
        uid_intid = Member.__uid_to_uid_intid.get(uid)
        if uid_intid is None:
            uid_intid = Member.__uid_counter
            Member.__uid_to_uid_intid[uid] = uid_intid
            Member.__uid_counter += 1

        # Protected
        self._uid = uid
        self._uid_intid = uid_intid
        self._hash = hash(uid)
        self._str = None
        self._deleted = False
        self._graph = None

        # Init
        super().__init__()
        self._init_str()

    def __eq__(self, other):
        """Equals magic method with extreme speed optimizations.

        This method is in an extreme hot code path and thus has been profiled
        and optimized heavily.  As comparing the uid or hashes takes too long
        """
        try:
            other_uid_intid = other._uid_intid  # noqa  # pylint: disable=protected-access
        except AttributeError:  # pragma: no cover
            return False  # Not a Member class
        return self._uid_intid == other_uid_intid  # Unique id for all Members.

    def __ge__(self, other):
        return self._uid >= other.uid

    def __gt__(self, other):
        return self._uid > other.uid

    def __hash__(self):
        return self._hash

    def __le__(self, other):
        return self._uid <= other.uid

    def __lt__(self, other):
        return self._uid < other.uid

    def __ne__(self, other):
        return not self.__eq__(other)

    def __str__(self):
        return self._str

    def __repr__(self):
        return "%s(uid='%s')" % (self.__class__.__name__, self._uid)

    @abc.abstractmethod
    def _init_str(self):
        """Initializes self._str for self.__str__."""

    @property
    def deleted(self):
        """Returns True if this graph member has been marked as deleted."""
        return self._deleted

    @property
    def is_node_instance(self):  # pylint: disable=no-self-use
        """Returns True if this object is a Node instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return False

    @property
    def is_edge_instance(self):  # pylint: disable=no-self-use
        """Returns True if this object is an Edge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return False

    @property
    def is_oredge_instance(self):  # pylint: disable=no-self-use
        """Returns True if this object is an OrEdge instance.

        Python's isinstance is slow.  To avoid its slowness the is_*_instance
        properties will be used for the most important classes.
        """
        return False

    @property
    def graph(self):
        """Returns the graph to which this member belongs."""
        if not self._graph:
            raise error.UnregisteredMemberInUseError(self)
        return self._graph

    @graph.setter
    def graph(self, graph):
        """Sets the graph to which this member belongs.

        The graph can only be set once.
        """
        if self._graph:
            if self._graph == graph:
                raise error.MemberAlreadyRegisteredError(self)
            else:
                raise error.NotMemberOfGraphError(self)
        self._graph = graph

    @property
    def uid(self):
        """Returns the uid of the graph member."""
        return self._uid

    @abc.abstractmethod
    def mark_deleted(self):
        """Marks the graph member as deleted."""
