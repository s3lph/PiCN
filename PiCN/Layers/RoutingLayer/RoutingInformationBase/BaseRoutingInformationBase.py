
import abc
import datetime

from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Packets import Name


class BaseRoutingInformationBase(abc.ABC):
    """
    Abstract base class to be implemented by RoutingInformationBase classes.
    """

    @abc.abstractmethod
    def ageing(self):
        """
        Remove outdated entries from the RIB.
        """
        pass

    @abc.abstractmethod
    def insert(self, name: Name, fid: int, distance: int, timeout: datetime = None):
        """
        Insert a new route into the RIB.
        :param name: The ICN name of the route
        :param fid: The face ID  of the route
        :param distance: The distance of the route
        :param timeout: The timestamp after which to consider the route
        :return:
        """
        pass

    @abc.abstractmethod
    def build_fib(self, fib: BaseForwardingInformationBase):
        """
        Construct FIB entries from the RIB data, and insert them into the passed FIB object.
        All previous entries in the FIB will be deleted.
        :param fib: The FIB to fill with routes.
        """
        pass
