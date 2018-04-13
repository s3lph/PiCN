
from typing import List

import multiprocessing
import threading
from datetime import datetime, timedelta

from PiCN.Processes import LayerProcess
from PiCN.Layers.RoutingLayer.RoutingInformationBase import TreeRoutingInformationBase
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Packets import Name, Content


class BasicRoutingLayer(LayerProcess):

    def __init__(self, rib: TreeRoutingInformationBase, log_level: int = 255):
        super().__init__('BasicRoutingLayer', log_level)
        self._linklayer: UDP4LinkLayer = None
        self._rib: TreeRoutingInformationBase = rib
        self._rib_maxage: timedelta = timedelta(seconds=3600)
        self._ageing_interval: float = 5.0
        self._ageing_timer: threading.Timer = None

    def start_process(self):
        super().start_process()
        self._ageing()

    def stop_process(self):
        super().stop_process()
        if self._ageing_timer is not None:
            self._ageing_timer.cancel()
            self._ageing_timer = None

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        if len(data) != 2:
            self.logger.warn('Expects [fid, Packet] from lower')
            return
        fid, packet = data
        if isinstance(packet, Content) and packet.name == Name('/autoconfig/forwarders'):
            if len(packet.content) > 0 and packet.content[0] == 128:
                self.logger.error('This implementation cannot handle the autoconfig binary wire format.')
                return
            lines: List[str] = packet.content.decode('utf-8').split('\n')
            scheme, addr = lines[0].split('://', 1)
            if scheme != 'udp4':
                self.logger.error(f'Don\'t know how to handle scheme {scheme}.')
                return
            for line in lines[1:]:
                if line.startswith('r:'):
                    typ, distance, pfx = line.split(':', 2)
                    distance = int(distance)
                    pfx = Name(pfx)
                    self._rib.insert(pfx, fid, distance, datetime.utcnow() + self._rib_maxage)
        self.queue_to_higher.put(data)
        pass

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        pass

    def _ageing(self):
        self._rib.ageing()
        self._rib_to_fib()
        self._start_forwarder_discovery()
        self._ageing_timer = threading.Timer(self._ageing_interval, self._ageing)
        self._ageing_timer.start()

    def _rib_to_fib(self):

        pass

    def _start_forwarder_discovery(self):
        pass
