import multiprocessing
import threading
import socket
import os

from typing import List

from PiCN.Packets import Name, Packet, Content, Interest, Nack
from PiCN.Processes import LayerProcess
from PiCN.Layers.LinkLayer import UDP4LinkLayer
from PiCN.Layers.RepositoryLayer.Repository.BaseRepository import BaseRepository

_AUTOCONFIG_PREFIX: Name = Name('/autoconfig')
_AUTOCONFIG_FORWARDERS_PREFIX: Name = Name('/autoconfig/forwarders')
_AUTOCONFIG_SERVICE_LIST_PREFIX: Name = Name('/autoconfig/services')
_AUTOCONFIG_SERVICE_REGISTRATION_PREFIX: Name = Name('/autoconfig/service')


class AutoconfigRepoLayer(LayerProcess):

    def __init__(self, name: str, linklayer: UDP4LinkLayer, repo: BaseRepository,
                 addr: str, port: int = 9000, bcaddr: str = '255.255.255.255', bcport: int = 9000,
                 solicitation_timeout: float = None, solicitation_max_retry: int = 3, log_level: int = 255):
        super().__init__('AutoconfigRepoLayer', log_level)
        self._linklayer = linklayer
        self._repository = repo
        self._addr: str = addr
        self._port: int = port
        self._broadcast_addr: str = bcaddr
        self._broadcast_port: int = bcport
        self._service_name: str = name
        self._solicitation_timeout: float = solicitation_timeout
        self._solicitation_max_retry: int = solicitation_max_retry
        self._solicitation_timer: threading.Timer = None

        # Enable broadcasting on the link layer's socket.
        if self._linklayer is not None:
            self._linklayer.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    def start_process(self):
        super().start_process()
        self._start_forwarder_solicitation(self._solicitation_max_retry)

    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Got data from lower: {data}')
        if (not isinstance(data, list) and not isinstance(data, tuple)) or len(data) != 2:
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        if not isinstance(data[0], int) or not isinstance(data[1], Packet):
            self.logger.warn('Autoconfig layer expects to receive [face id, packet] from lower layer')
            return
        packet: Packet = data[1]
        if not _AUTOCONFIG_PREFIX.is_prefix_of(packet.name):
            to_higher.put(data)
            return
        if _AUTOCONFIG_FORWARDERS_PREFIX.is_prefix_of(packet.name):
            self._handle_forwarders(packet)
        elif _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX.is_prefix_of(packet.name):
            self._handle_service_registration(packet)
        pass

    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        self.logger.info(f'Got data from higher: {data}')
        to_lower.put(data)

    def _handle_forwarders(self, packet: Packet):
        if not isinstance(packet, Content):
            return
        self.logger.info('Received forwarder info')
        if self._solicitation_timer is not None:
            self._solicitation_timer.cancel()
            self._solicitation_timer = None
        lines: List[str] = packet.content.split('\n')
        host, port = lines[0].split(':')
        self.logger.info(f'forwarder: {host}:{port}')
        fwd_fid = self._linklayer.get_or_create_fid((host, int(port)), static=True)
        for line in lines[1:]:
            if len(line.strip()) == 0:
                continue
            t, n = line.split(':')
            if t == 'p':
                prefix = Name(n)
                self.logger.info(f'Got prefix {prefix}')
                registration_name: Name = _AUTOCONFIG_SERVICE_REGISTRATION_PREFIX
                registration_name += f'{self._addr}:{self._port}'
                registration_name += prefix
                registration_name += f'{self._service_name}'
                self.logger.info(f'Registering service {registration_name}')
                registration_interest = Interest(registration_name)
                self.logger.info('Sending service registration')
                self.queue_to_lower.put([fwd_fid, registration_interest])

    def _handle_service_registration(self, packet: Packet):
        if isinstance(packet, Nack):
            nack: Nack = packet
            self.logger.error(f'Service registration declined: {nack.reason}')
            return
        if isinstance(packet, Content):
            self.logger.info(f'Service registration accepted: {packet.name.components[3:]}')
            self._repository.set_prefix(Name(packet.name.components[3:]))
            return

    def _start_forwarder_solicitation(self, retry: int):
        self.logger.info('Soliciting forwarders')
        forwarders_interest = Interest(_AUTOCONFIG_FORWARDERS_PREFIX)
        autoconf_fid = self._linklayer.get_or_create_fid((self._broadcast_addr, self._broadcast_port), static=True)
        self.queue_to_lower.put([autoconf_fid, forwarders_interest])
        # Schedule re-solicitation, if enabled
        if self._solicitation_timeout is not None and retry > 1:
            self._solicitation_timer = threading.Timer(self._solicitation_timeout, self._start_forwarder_solicitation,
                                                       [retry - 1])
            self._solicitation_timer.start()
        elif retry <= 1:
            self.logger.fatal('No forwarder solicitation received in time')
            # FIXME: This is a potentially bad idea, as no cleanup happens, such as open files or network sockets
            # Oh, and it will kill unit tests, too
            os._exit(1)
