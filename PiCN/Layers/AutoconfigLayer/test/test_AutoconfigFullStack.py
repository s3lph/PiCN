
import unittest
import multiprocessing
import time
import queue

from PiCN.LayerStack import LayerStack
from PiCN.Layers.ICNLayer import BasicICNLayer
from PiCN.Layers.PacketEncodingLayer import BasicPacketEncodingLayer
from PiCN.Layers.PacketEncodingLayer.Encoder import NdnTlvEncoder
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.RepositoryLayer import BasicRepositoryLayer
from PiCN.Layers.AutoconfigLayer import AutoconfigServerLayer, AutoconfigClientLayer, AutoconfigRepoLayer
from PiCN.Layers.ICNLayer.ContentStore import ContentStoreMemoryExact
from PiCN.Layers.ICNLayer.PendingInterestTable import PendingInterstTableMemoryExact
from PiCN.Layers.ICNLayer.ForwardingInformationBase import ForwardingInformationBaseMemoryPrefix
from PiCN.Layers.ChunkLayer import BasicChunkLayer
from PiCN.Layers.ChunkLayer.Chunkifyer import SimpleContentChunkifyer

from PiCN.Packets import Name, Interest, Content

from PiCN.Layers.AutoconfigLayer.test.mocks import MockRepository


class test_AutoconfigFullStack(unittest.TestCase):

    def setUp(self):

        # Set up forwarder
        manager = multiprocessing.Manager()
        ds = manager.dict()
        ds['cs'] = ContentStoreMemoryExact()
        ds['pit'] = PendingInterstTableMemoryExact()
        ds['fib'] = ForwardingInformationBaseMemoryPrefix()
        prefixes = [(Name('/test/prefix/repos'), True)]
        # Auto-assign port
        forwarder_linklayer = UDP4LinkLayer(port=0, manager=manager)
        forwarder_port = forwarder_linklayer.sock.getsockname()[1]
        forwarder_encoder = NdnTlvEncoder()
        icnlayer = BasicICNLayer()
        icnlayer._data_structs = ds
        self.forwarder = LayerStack([
            icnlayer,
            AutoconfigServerLayer(forwarder_linklayer, ds,
                                  registration_prefixes=prefixes, bcaddr='127.255.255.255'),
            BasicPacketEncodingLayer(forwarder_encoder),
            forwarder_linklayer
        ])

        # Set up repo
        repository = MockRepository(Name('/thisshouldbechanged'))
        repo_chunkifyer = SimpleContentChunkifyer()
        repo_chunklayer = BasicChunkLayer(repo_chunkifyer)
        repo_encoder = NdnTlvEncoder()
        # Auto-assign port
        repo_linklayer = UDP4LinkLayer(port=0, manager=manager)
        repo_port = repo_linklayer.sock.getsockname()[1]
        self.repo = LayerStack([
            BasicRepositoryLayer(repository),
            repo_chunklayer,
            AutoconfigRepoLayer('testrepo', repo_linklayer, repository, '127.0.0.1', repo_port,
                                bcaddr='127.255.255.255', bcport=forwarder_port),
            BasicPacketEncodingLayer(repo_encoder),
            repo_linklayer
        ])

        # Set up fetch client
        client_chunkifyer = SimpleContentChunkifyer()
        client_chunklayer = BasicChunkLayer(client_chunkifyer)
        client_encoder = NdnTlvEncoder()
        client_linklayer = UDP4LinkLayer(port=0, manager=manager)
        self.client = LayerStack([
            client_chunklayer,
            AutoconfigClientLayer(client_linklayer, bcaddr='127.255.255.255', bcport=forwarder_port),
            BasicPacketEncodingLayer(client_encoder),
            client_linklayer
        ])

    def tearDown(self):
        self.forwarder.stop_all()
        self.repo.stop_all()
        self.client.stop_all()

    def test_repo_forwarder_client_fetch_fixed_name(self):
        self.forwarder.start_all()
        time.sleep(1.0)
        self.repo.start_all()
        time.sleep(1.0)
        self.client.start_all()
        time.sleep(1.0)

        # Send an interest with a fixed name, let autoconfig figure out where to get the da10.0ta from
        name = Name('/test/prefix/repos/testrepo/testcontent')
        interest = Interest(name)
        self.client.queue_from_higher.put([None, interest])
        try:
            data = self.client.queue_to_higher.get(timeout=2.0)
        except queue.Empty:
            self.fail()
        self.assertIsInstance(data[1], Content)
        self.assertEqual(data[1].name, name)
        self.assertEqual(data[1].content, 'testcontent')