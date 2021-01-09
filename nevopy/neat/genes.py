# MIT License
#
# Copyright (c) 2020 Gabriel Nogueira (Talendar)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

""" Implements the nodes (neurons) and edges (connections) of a genome.
"""

from __future__ import annotations
from typing import Union, Callable, Tuple, List, Optional
from enum import Enum
import uuid


class NodeGene:
    """ A gene that represents/encodes a neuron (node) in a neural network.

    A :class:`~NodeGene` is the portion of a :class:`.Genome` that encodes a
    neuron (node) of the neural network encoded by the :class:`.Genome`. It has
    an activation function, which is applied to inputs received from other nodes
    of the network.

    Args:
        node_id (int/None): An int specifying the node's ID or None, in which
            case a temporary ID will be generated.
        node_type (NodeGene.Type): the node's type.
        activation_func (Callable[[float], float]): Activation function to be
            used by the node. It should receive a float as input and return a
            float (the resulting activation) as output.
        initial_activation (float): initial value of the node's activation (used
            when processing recurrent connections between nodes).
        parent_connection_nodes (None/tuple): Should be None for non-hidden
            nodes. For hidden nodes (:attr:`~NodeGene.Type.HIDDEN`), this should
            be a tuple containing the nodes that form the connection where the
            node originated (a hidden node is created by breaking a connection
            between two existing nodes).
        debug_info (None/str): Used for debugging purposes. Should be ignored
            most of the time. Todo: remove.

    Attributes:
        in_connections (List[ConnectionGene]): List with the connections
            (:class:`.ConnectionGene`) leaving this node, i.e., connections that
            have this node as the source.
        out_connections (List[ConnectionGene]): List with the connections
            (:class:`.ConnectionGene`) coming to this node, i.e., connections
            that have this node as the destination.
        _temp_id (None/str): Stores a temporary ID for the node while it isn't
            assigned a definitive ID.
    """

    def __init__(self,
                 node_id: Union[int, str],
                 node_type: NodeGene.Type,
                 activation_func: Callable[[float], float],
                 initial_activation: float,
                 parent_connection_nodes: Optional[Tuple[NodeGene,
                                                         NodeGene]] = None,
                 debug_info: Union[None, str] = None) -> None:
        self._id = node_id
        self._type = node_type
        self._initial_activation = initial_activation
        self._activation = initial_activation
        self._function = activation_func
        self._parent_connection_nodes = parent_connection_nodes
        self.in_connections = []   # type: List[ConnectionGene]
        self.out_connections = []  # type: List[ConnectionGene]
        self._temp_id = None if self._id is not None else uuid.uuid4().hex[:12]
        self.debug_info = debug_info

    class Type(Enum):
        """ Specifies the possible types of node genes. """
        INPUT, BIAS, HIDDEN, OUTPUT = range(4)

    @property
    def id(self) -> Union[int, str]:
        """ Innovation ID of the gene.

        This ID is used to mate genomes and to calculate their difference.

        "The innovation numbers are historical markers that identify the
        original historical ancestor of each gene. New genes are assigned new
        increasingly higher numbers." - :cite:`stanley:ec02`

        Returns:
            If the node's ID has already been set: an int with the definitive ID
            of the node. Otherwise: a string containing a temporary hexadecimal
            unique ID for the node.
        """
        return self._id if self._id is not None else self._temp_id

    @id.setter
    def id(self, new_id: int) -> None:
        """ Assigns an ID to a node that has a temporary ID.

        Args:
            new_id (int): The node's definitive ID.

        Raises:
            NodeIdException: If the node already has a definitive ID, i.e., the
            node isn't using a temporary ID anymore. This will always be raised
            when this setter is called on non-hidden nodes.
        """
        if self._id is not None:
            raise NodeIdException("Attempt to assign a new ID to a node gene "
                                  "that already has an ID!")
        self._id = new_id
        self._temp_id = None

    def is_id_temp(self) -> bool:
        """ Checks whether the node has a temporary ID.

        Returns:
            True if the node is using a temporary ID, False otherwise (the node
            has already been assigned a definitive ID).
        """
        return self._id is None

    @property
    def type(self) -> NodeGene.Type:
        """ Type of the node (input, bias, hidden or output). """
        return self._type

    @property
    def activation(self) -> float:
        """
        The node's cached activation value, i.e., the node's output when it was
        last processed.
        """
        return self._activation

    @property
    def parent_connection_nodes(self) -> Optional[Tuple[NodeGene, NodeGene]]:
        """ The nodes that form the connection where this node originated.

        As specified in the original NEAT paper :cite:`stanley:ec02`, a hidden
        node (:attr:`~NodeGene.Type.HIDDEN`) is created by diving an existing
        connection between two nodes in the genome. We call these two nodes the
        parents of the newly created hidden node. They are later used to assign
        an innovation ID to the created node.

        The reason why a reference to the parents is kept, instead of just their
        ID, is that, when this node is created, one or both parents might not
        have been assigned a definitive ID. In this case, it wouldn't be
        possible to find then later (when their ID change) unless we keep a
        reference to them.

        Returns:
            A tuple with the nodes that form the connection where this node
            originated. The first node is the connection's source node and the
            second node is the connection's destination node.

            If the node doesn't have parents, None is returned. This behaviour
            isn't expected, since all hidden nodes are expected to have parents
            and calls to this property on non-hidden nodes should raise an
            exception.

        Raises:
            NodeParentsException: If the node type is not :attr:`~NodeGene.Type.HIDDEN`.
            Only hidden nodes have parents.
        """
        if self._type != NodeGene.Type.HIDDEN:
            raise NodeParentsException("Attempt to get the parents of a "
                                       "non-hidden node!")
        return self._parent_connection_nodes

    def activate(self, x: float) -> None:
        """ Applies the node's activation function to the given input.

        The node's activation value, i.e., the node's cached output, is updated
        by this call and can be later be accessed through the property
        :attr:`~NodeGene.activation`.

        Returns:
            None. The node's output is updated internally.
        """
        self._activation = self._function(x)

    def shallow_copy(self, debug_info: str = None) -> NodeGene:
        """ Makes and returns a shallow/simple copy of this node.

        The copied node shares the same values for all the attributes of the
        source node, except for the connections. The copied node is created
        without any connections. It has the same parent nodes as the source node
        (the same reference to the same objects).

        Returns:
            A copy of this node without its connections.
        """
        return NodeGene(node_id=self._id,
                        node_type=self._type,
                        activation_func=self._function,
                        initial_activation=self._initial_activation,
                        parent_connection_nodes=self._parent_connection_nodes,
                        debug_info=debug_info)

    def reset_activation(self) -> None:
        """
        Resets the node's activation value (it's cached output) to its initial
        value.
        """
        self._activation = self._initial_activation


class ConnectionGene:
    """ A connection between two nodes.

    A connection gene represents/encodes a connection (edge) between two nodes
    (neurons) of a neural network (phenotype of a genome).

    Args:
        cid (Union[int, None]): The innovation number of this connection. As
            described in the original NEAT paper :cite:`stanley:ec02`, this
            serves as a historical marker for the gene, helping to identify
            homologous genes. If None is passed as argument, the connection is
            created without an ID. In cases where it's necessary to create a
            bunch of connections for different genomes, delaying the assignment
            of an ID to the gene is useful, because, once all connections have
            been created, it's easier to assign similar IDs to homologous
            connections in different genomes. Unlike a hidden :class:`~NodeGene`,
            a temporary ID isn't required here (the identification of
            connections without IDs can be done through the nodes that compose
            it).
        from_node (NodeGene): Node from where the connection is originated. The
            source node of the connection.
        to_node (NodeGene): Node to where the connection is headed. The
            destination node of the connection.
        weight (float): The weight of the connection.
        enabled (bool): Whether the initial state of the newly created
            connection should enabled or disabled.
        debug_info (str): Used for debugging purposes. Should be ignored most
            of the time. Todo: remove.

    Attributes:
        weight (float): The weight of the connection.
        enabled (bool): Whether the connection is enabled or not. A disabled
            connection won't be considered during the computations of the neural
            network.
        debug_info (str): Used for debugging purposes. Should be ignored most of
            the time. Todo: remove.
    """

    def __init__(self,
                 cid: Optional[int],
                 from_node: NodeGene,
                 to_node: NodeGene,
                 weight: float,
                 enabled: bool = True,
                 debug_info: str = None) -> None:
        self._id = cid
        self._from_node = from_node
        self._to_node = to_node
        self.weight = weight
        self.enabled = enabled
        self.debug_info = debug_info

    @property
    def id(self) -> Optional[int]:
        """ Innovation number of the connection gene.

         As described in the original NEAT paper :cite:`stanley:ec02`, this
         value serves as a historical marker for the gene, helping to identify
         homologous genes. Although must of the identification is based on the
         nodes that form the connection, this ID is still helpful to make some
         comparisons faster. If it's `None`, then an ID has yet to be assigned
         to the gene.
        """
        return self._id

    @id.setter
    def id(self, new_id: int) -> None:
        """ Assigns an ID to a connection gene that was created without an ID.

        A connection gene can be created without an ID, in which case one can be
        assigned to it later, through this setter. In cases where it's necessary
        to create a bunch of connections for different genomes, delaying the
        assignment of an ID to the gene is useful, because, once all connections
        have been created, it's easier to assign similar IDs to homologous
        connections in different genomes. Unlike the a hidden :class:`~NodeGene`,
        a temporary ID isn't required here (the identification of connections
        without IDs can be done through the nodes that compose it).

        Args:
            new_id (int): The ID of the connection gene.

        Raises:
            ConnectionIdException: If the connection has already been assigned
            an ID, either during its creation or through a previous call to this
            setter.
        """
        if self._id is not None:
            raise ConnectionIdException(
                "Attempt to assign a new ID to a connection gene that already "
                "has an ID!"
            )
        self._id = new_id

    @property
    def from_node(self) -> NodeGene:
        """ Node from where the connection is originated (source node). """
        return self._from_node

    @property
    def to_node(self) -> NodeGene:
        """ Node to where the connection is headed (destination node). """
        return self._to_node


def connection_exists(src_node: NodeGene, dest_node: NodeGene) -> bool:
    """ Checks if the connection `src_node->dest_node` exists.

    A connection `A->B` between the nodes `A` and `B` exists if `A->B` is in
    node `A's` :attr:`~NodeGene.out_connections` or `A->B` is in node `B's`
    :attr:`~NodeGene.in_connections`.

    Args:
        src_node (NodeGene): The node from where the connection leaves (source
            node).
        dest_node (NodeGene): The node to where the connection is headed
            (destination node).

    Returns:
        True if the connection `src_node->dest_node` exists and False otherwise.
    """
    for dest_cin, src_cout in zip(dest_node.in_connections,
                                  src_node.out_connections):
        if (dest_cin.from_node.id == src_node.id
                or src_cout.to_node.id == dest_node.id):
            return True
    return False


def align_connections(
        con_list1: List[ConnectionGene],
        con_list2: List[ConnectionGene],
        print_alignment: bool = False
) -> Tuple[List[Union[ConnectionGene, None]], List[Union[ConnectionGene, None]]]:
    """ Aligns the matching connection genes of the given lists.

    In the context of NEAT :cite:`stanley:ec02`, aligning homologous connections
    genes is required both to compare the similarity of a pair of genomes and to
    perform sexual reproduction. Two connection genes are said to match or to be
    homologous if they have the same innovation ID, meaning that they represent
    the same structure.

    Genes that do not match are either disjoint or excess, depending on whether
    they occur within or outside the range of the other parent’s innovation
    numbers. They represent a structure that is not present in the other genome.

    Args:
        con_list1 (List[ConnectionGene]): The first list of connection genes.
        con_list2 (List[ConnectionGene]): The second list of connection genes.
        print_alignment: Whether to print the generated alignment or not. Used
            for debugging.

    Returns:
        A tuple containing two lists of the same size. Index 0 corresponds to
        the first list and index 1 to the second list. The returned lists
        contain connection genes or `None`. The order of the genes is preserved
        in the returned lists (but not their indices!).

        If, given a position, there are two genes (one in each list), the genes
        match. On the other hand, if, in the position, there is only one gene
        (on one of the lists) and a `None` value (on the other list), the genes
        are either disjoint or excess.
    """
    con_dict1 = {c.id: c for c in con_list1}
    con_dict2 = {c.id: c for c in con_list2}
    union = sorted(set(con_dict1.keys()) | set(con_dict2.keys()))

    aligned1, aligned2 = [], []
    for cid in union:
        aligned1.append(con_dict1[cid] if cid in con_dict1 else None)
        aligned2.append(con_dict2[cid] if cid in con_dict2 else None)

    # debug
    if print_alignment:
        for c1, c2 in zip(aligned1, aligned2):
            print(c1.id if c1 is not None else "-", end=" | ")
            print(c2.id if c2 is not None else "-")

    return aligned1, aligned2


class NodeIdException(Exception):
    """ Indicates that an attempt has been made to assign a new ID to a gene
    node that already has an ID.
    """
    pass


class ConnectionIdException(Exception):
    """ Indicates that an attempt has been made to assign a new ID to a
    connection gene that already has an ID.
    """
    pass


class NodeParentsException(Exception):
    """ Indicates that an attempt has been made to get the parents of a
    non-hidden node.
    """
    pass
