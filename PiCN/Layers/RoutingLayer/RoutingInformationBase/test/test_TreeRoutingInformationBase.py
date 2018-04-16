import multiprocessing
import unittest
from datetime import datetime, timedelta

from PiCN.Layers.RoutingLayer.RoutingInformationBase.TreeRoutingInformationBase import _RIBTreeNode
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase, TreeRoutingInformationBase
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase, ForwardingInformationBaseMemoryPrefix
from PiCN.Packets import Name


class test_TreeRoutingInformationBase(unittest.TestCase):

    def test_insert(self):
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name('/foo/bar'), 42, 1337)
        self.assertEqual(0, len(tree._distance_vector))
        self.assertIn(b'foo', tree._children.keys())
        foo: _RIBTreeNode = tree._children[b'foo']
        self.assertEqual(0, len(foo._distance_vector))
        self.assertIn(b'bar', foo._children.keys())
        bar: _RIBTreeNode = foo._children[b'bar']
        self.assertEqual(1, len(bar._distance_vector))
        self.assertIn(42, bar._distance_vector.keys())
        self.assertEqual((1337, None), bar._distance_vector[42])

    def test_insert_nonroot_fail(self):
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name('/foo'), 42, 1337)
        foo: _RIBTreeNode = tree._children[b'foo']
        with self.assertRaises(ValueError):
            foo.insert(Name('/bar'), 42, 1337)

    def test_best_fid(self):
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name([]), 1337, 20)
        tree.insert(Name([]), 42, 10)
        tree.insert(Name([]), 2, 15)
        fid = tree._get_best_fid()
        self.assertEqual(42, fid)

    def test_collapse_single_route(self):
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name('/foo/bar'), 42, 1337)
        fib = tree.collapse()
        self.assertEqual([([b'foo', b'bar'], 42)], fib)

    def test_collapse_two_routes_same_name(self):
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name('/foo/bar'), 42, 1337)
        tree.insert(Name('/foo/bar'), 23, 10)
        fib = tree.collapse()
        self.assertEqual([([b'foo', b'bar'], 23)], fib)

    def test_collapse_subtree_entries(self):
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name('/ndn'), 0, 5)
        tree.insert(Name('/ndn/ch/unibas'), 1, 10)
        fib = tree.collapse()
        self.assertIn(([b'ndn'], 0), fib)
        self.assertIn(([b'ndn', b'ch', b'unibas'], 1), fib)

    def test_collapse_mixed(self):
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name('/local'), 0, 1)
        tree.insert(Name('/ndn/edu/ucla/ping'), 1, 42)
        tree.insert(Name('/ndn/ch/unibas/cs'), 2, 10)
        tree.insert(Name('/ndn/ch/unibas/dmi/cn'), 2, 11)
        tree.insert(Name('/ndn/ch/unibas/dmi/cn'), 3, 20)
        tree.insert(Name('/ndn/ch/unibe'), 3, 12)
        fib = tree.collapse()
        self.assertIn(([b'local'], 0), fib)
        self.assertIn(([b'ndn', b'edu', b'ucla', b'ping'], 1), fib)
        self.assertIn(([b'ndn', b'ch', b'unibas'], 2), fib)
        self.assertIn(([b'ndn', b'ch', b'unibe'], 3), fib)
        self.assertEqual(4, len(fib))

    def test_ageing(self):
        timeout1 = datetime.utcnow() + timedelta(hours=24)
        timeout2 = datetime.utcnow() - timedelta(seconds=10)
        tree: _RIBTreeNode = _RIBTreeNode()
        tree.insert(Name([]), 0, 1, timeout1)
        tree.insert(Name([]), 1, 2, timeout2)
        self.assertEqual(2, len(tree._distance_vector))
        self.assertIn(0, tree._distance_vector)
        self.assertIn(1, tree._distance_vector)
        tree.ageing(datetime.utcnow())
        self.assertIn(0, tree._distance_vector)
        self.assertNotIn(1, tree._distance_vector)

    def test_wrapper_class(self):
        manager = multiprocessing.Manager()
        rib: BaseRoutingInformationBase = TreeRoutingInformationBase()
        fib: BaseForwardingInformationBase = ForwardingInformationBaseMemoryPrefix(manager)
        rib.insert(Name('/foo/bar'), 0, 42)
        rib.insert(Name('/ndn/ch/unibas/dmi/cn'), 1, 10)
        rib.build_fib(fib)
        for c in fib.container:
            print(c)
