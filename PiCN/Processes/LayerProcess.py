""" Abstract Class defining a Process running on a layer"""

import abc
import inspect
import multiprocessing
import os
import select
import time

from PiCN.Processes import PiCNProcess

class LayerProcess(PiCNProcess):
    """ Abstract Class defining a Process running on a layer"""

    def __init__(self, logger_name="PiCNProcess", log_level=255):
        super().__init__(logger_name, log_level)
        self._queue_from_lower: multiprocessing.Queue = None
        self._queue_from_higher: multiprocessing.Queue = None
        self._queue_to_lower: multiprocessing.Queue = None
        self._queue_to_higher: multiprocessing.Queue = None
        self.stop: bool = False

    @property
    def queue_from_lower(self):
        """Queue to get data from the lower layer"""
        return self._queue_from_lower

    @queue_from_lower.setter
    def queue_from_lower(self, q):
        self._queue_from_lower = q

    @property
    def queue_from_higher(self):
        """Queue to get data from the higher layer"""
        return self._queue_from_higher

    @queue_from_higher.setter
    def queue_from_higher(self, q):
        self._queue_from_higher = q

    @property
    def queue_to_lower(self):
        """Queue to send data to the lower layer"""
        return self._queue_to_lower

    @queue_to_lower.setter
    def queue_to_lower(self, q):
        self._queue_to_lower = q

    @property
    def queue_to_higher(self):
        """Queue to send data to the higher layer"""
        return self._queue_to_higher

    @queue_to_higher.setter
    def queue_to_higher(self, q):
        self._queue_to_higher = q

    @abc.abstractmethod
    def data_from_lower(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """ handle incoming data from the lower layer """

    @abc.abstractmethod
    def data_from_higher(self, to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue, data):
        """ handle incoming data from the higher layer """

    def _run_poll(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
            to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """ Process loop, handle incoming packets, use poll if many file descriptors are required
            :param from_lower: Queue to receive data from lower Layer
            :param from_higher: Queue to receive data from higher Layer
            :param to_lower: Queue to send data to lower Layer
            :param to_higher: Queue to send data to higher Layer
        """
        poller = select.poll()
        READ_ONLY = select.POLLIN | select.POLLPRI | select.POLLHUP | select.POLLERR
        if from_lower:
            poller.register(from_lower._reader, READ_ONLY)
        if from_higher:
            poller.register(from_higher._reader, READ_ONLY)
        while True:
            ready_vars = poller.poll()
            for filno, var in ready_vars:
                if from_lower and filno == from_lower._reader.fileno() and not from_lower.empty():
                    self.data_from_lower(to_lower, to_higher, from_lower.get())
                elif from_higher and filno == from_higher._reader.fileno() and not from_higher.empty():
                    self.data_from_higher(to_lower, to_higher, from_higher.get())

    def _run_select(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
             to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """ Process loop, handle incoming packets, use select if few file descriptors are required
            :param from_lower: Queue to receive data from lower Layer
            :param from_higher: Queue to receive data from higher Layer
            :param to_lower: Queue to send data to lower Layer
            :param to_higher: Queue to send data to higher Layer
        """
        in_queues = []
        if from_lower:
            in_queues.append(from_lower._reader)
        if from_higher:
            in_queues.append(from_higher._reader)
        while True:
            if len(in_queues) == 0:
                continue
            ready_vars, _, _ = select.select(in_queues, [], [])
            for var in ready_vars:
                if from_lower and var == from_lower._reader and not from_lower.empty():
                    self.data_from_lower(to_lower, to_higher, from_lower.get())
                elif from_higher and var == from_higher._reader and not from_higher.empty():
                    self.data_from_higher(to_lower, to_higher, from_higher.get())

    def _run_sleep(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
                   to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """ Process loop, handle incoming packets, use round-robin, required for NT since MS POSIX api do not support
            select on file descriptors nor polling
            :param from_lower: Queue to receive data from lower Layer
            :param from_higher: Queue to receive data from higher Layer
            :param to_lower: Queue to send data to lower Layer
            :param to_higher: Queue to send data to higher Layer
         """
        while True:
            dequeued: bool = False
            if from_lower and not from_lower.empty():
                self.data_from_lower(to_lower, to_higher, from_lower.get())
                dequeued = True
            if from_higher and not from_higher.empty():
                self.data_from_higher(to_lower, to_higher, from_higher.get())
            if not dequeued:
                time.sleep(0.3)

    def _run(self, from_lower: multiprocessing.Queue, from_higher: multiprocessing.Queue,
             to_lower: multiprocessing.Queue, to_higher: multiprocessing.Queue):
        """
        Initialize the execution loop. Switch between NT, Unix and Unittest. Use select for Unix, Use poll for
        unittest, since select cannot handle more than 1024 File Descriptors.
        :param from_lower: Queue to receive data from lower Layer
        :param from_higher: Queue to receive data from higher Layer
        :param to_lower: Queue to send data to lower Layer
        :param to_higher: Queue to send data to higher Layer
        """
        if os.name == 'nt': # Exception for windows since MS POSIX api do not support select on File Descriptors
            self._run_sleep(from_lower, from_higher, to_lower, to_higher)
        elif self.in_unittest():
            self._run_poll(from_lower, from_higher, to_lower, to_higher)
        else:
            self._run_select(from_lower, from_higher, to_lower, to_higher)

    def start_process(self):
        """Start the Layer Process"""
        self.process = multiprocessing.Process(target=self._run, args=[self._queue_from_lower,
                                                                            self._queue_from_higher,
                                                                            self._queue_to_lower,
                                                                            self._queue_to_higher])
        self.process.daemon = True
        self.process.start()

    def stop_process(self):
        """Stop the Layer Process"""
        if self.process:
            self.process.terminate()
            self.process.join()
        time.sleep(0.1)
        if self.queue_to_lower:
            self.queue_to_lower.close()
            self.queue_to_lower.join_thread()
        if self.queue_from_lower:
            self.queue_from_lower.close()
            self.queue_from_lower.join_thread()
        if self.queue_to_higher:
            self.queue_to_higher.close()
            self.queue_to_higher.join_thread()
        if self.queue_from_higher:
            self.queue_from_higher.close()
            self.queue_from_higher.join_thread()
        time.sleep(0.1)

    def in_unittest(self):
        """Check if unittest is running for using poller instead of select, to enable more file descriptor"""
        try:
            current_stack = inspect.stack()
            for stack_frame in current_stack:
                for program_line in stack_frame[4]:
                    if "unittest" in program_line:
                        return True
                    if "nose" in program_line:
                        return True
            return False
        except:
            return True