
from typing import List, Tuple

import multiprocessing
import threading
from datetime import datetime, timedelta

from PiCN.Processes import LayerProcess
from PiCN.Layers.ICNLayer.ForwardingInformationBase import BaseForwardingInformationBase
from PiCN.Layers.RoutingLayer.RoutingInformationBase import BaseRoutingInformationBase
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Packets import Name, Content, Interest


class BasicRoutingLayer(LayerProcess):

    # TODO: RIB into managed dict, see ICN Layer L24

    def __init__(self, linklayer: UDP4LinkLayer, rib: BaseRoutingInformationBase, fib: BaseForwardingInformationBase,
                 bcaddrs: List[Tuple[str, int]] = None, log_level: int = 255):
        super().__init__('BasicRoutingLayer', log_level)
        self._linklayer: UDP4LinkLayer = linklayer
        self._rib: BaseRoutingInformationBase = rib
        self._fib: BaseForwardingInformationBase = fib
        self._rib_maxage: timedelta = timedelta(seconds=3600)
        self._bcaddrs: List[Tuple[str, int]] = bcaddrs if bcaddrs is not None else []
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
        self.logger.info(f'Received data from lower: {data}')
        self.logger.info(self._rib)
        if len(data) != 2:
            self.logger.warn('Expects [fid, Packet] from lower')
            return
        fid, packet = data
        if isinstance(packet, Content) and packet.name == Name('/autoconfig/forwarders'):
            if len(packet.content) > 0 and packet.content[0] == 128:
                self.logger.error('This implementation cannot handle the autoconfig binary wire format.')
                return
            lines: List[str] = packet.content.split('\n')
            scheme, addr = lines[0].split('://', 1)
            if scheme != 'udp4':
                self.logger.error(f'Don\'t know how to handle scheme {scheme}.')
                return
            for line in lines[1:]:
                if line.startswith('r:'):
                    typ, distance, pfx = line.split(':', 2)
                    if distance == '-1':
                        self.logger.info(f'Route doesn\'t have distance information; discarding: {pfx}.')
                        continue
                    distance = int(distance)
                    pfx = Name(pfx)
                    self._rib.insert(pfx, fid, distance + 1, datetime.utcnow() + self._rib_maxage)
        self.queue_to_higher.put(data)

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.queue_to_lower.put(data)

    def _ageing(self):
        self._rib.ageing()
        self._rib_to_fib()
        self._send_forwarder_solicitation()
        self._ageing_timer = threading.Timer(self._ageing_interval, self._ageing)
        self._ageing_timer.start()

    def _rib_to_fib(self):
        self._rib.build_fib(self._fib)

    def _send_forwarder_solicitation(self):
        solicitation: Interest = Interest(Name('/autoconfig/forwarders'))
        for addr in self._bcaddrs:
            fid = self._linklayer.get_or_create_fid(addr, static=False)
            self.queue_to_lower.put([fid, solicitation])
