"""Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

import abc
import multiprocessing
from typing import List

from PiCN.Packets import Interest, Name


class ForwardingInformationBaseEntry(object):
    """An entry in the Forwarding Information Base"""

    def __init__(self, name: Name, faceid: int, static: bool = False, distance: int = None):
        self._name: Name = name
        self._faceid: int = faceid
        self._static: bool = static
        self._distance: int = distance

    def __eq__(self, other):
        return self._name == other._name and self._faceid == other._faceid

    def __str__(self):
        static = ' static' if self._static else ''
        dist = f' d={self._distance}' if self._distance is not None else ''
        return f'<FIB Entry: {self._name.to_string()} via {self._faceid}{static}{dist}>'

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def faceid(self):
        return self._faceid

    @faceid.setter
    def faceid(self, faceid):
        self._faceid = faceid

    @property
    def static(self):
        return self._static

    @static.setter
    def static(self, static):
        self._static = static

    @property
    def distance(self):
        return self._distance

    @distance.setter
    def distance(self, distance: int):
        self._distance = distance


class BaseForwardingInformationBase(object):
    """Abstract BaseForwardingInformationBase for usage in BasicICNLayer"""

    def __init__(self, manager: multiprocessing.Manager):
        self._container: List[ForwardingInformationBaseEntry] = manager.list()

    @abc.abstractclassmethod
    def add_fib_entry(self, name: Name, fid: int, static: bool, distance: int = None):
        """Add an Interest to the PIT"""

    @abc.abstractclassmethod
    def remove_fib_entry(self, name: Name):
        """Remove an entry from the PIT"""

    @abc.abstractclassmethod
    def find_fib_entry(self, name: Name, already_used: List[ForwardingInformationBaseEntry]) \
            ->ForwardingInformationBaseEntry:
        """Find an entry in the PIT"""

    def clear(self):
        self._container[:] = []

    @property
    def container(self):
        return self._container

    @container.setter
    def container(self, container):
        self._container = container

    @property
    def manager(self):
        return self._manager

    @manager.setter
    def manager(self, manager: multiprocessing.Manager):
        self._manager = manager
