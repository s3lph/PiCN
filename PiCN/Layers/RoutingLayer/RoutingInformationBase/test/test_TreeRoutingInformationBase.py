
import unittest

from datetime import datetime

from PiCN.Layers.RoutingLayer.RoutingInformationBase.TreeRoutingInformationBase import _RIBTreeNode

from PiCN.Packets import Name


class test_TreeRoutingInformationBase(unittest.TestCase):

    def test_insert(self):
        root: _RIBTreeNode = _RIBTreeNode()
        foo = _RIBTreeNode(b'foo')
        foo._distance_vector[0] = 1, datetime.utcnow()
        root._add_child(foo)
        ndn = _RIBTreeNode(b'ndn')
        root._add_child(ndn)
        edu = _RIBTreeNode(b'edu')
        ndn._add_child(edu)
        ch = _RIBTreeNode(b'ch')
        ndn._add_child(ch)
        ucla = _RIBTreeNode(b'ucla')
        edu._add_child(ucla)
        unibas = _RIBTreeNode(b'unibas')
        ch._add_child(unibas)
        unibe = _RIBTreeNode(b'unibe')
        unibe._distance_vector[2] = 10, datetime.utcnow()
        ch._add_child(unibe)
        print(root)
        root.insert(Name('/ndn/edu/ucla/ping'), 1, 10)
        root.insert(Name('/ndn/edu/ucla/ping'), 1, 10)
        root.insert(Name('/ndn/ch/unibas/cs/cn/test/foo'), 2, 20)
        root.insert(Name('/ndn/ch/unibas/cs/cn/test/bar'), 2, 21)
        print(root)
        print(root.collapse())
