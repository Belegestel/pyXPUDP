import socket
import struct
import threading
import time
from itertools import batched


class XPConnector:

    def __init__(self, host_ip, send_port, receive_port, listen_freq=5):
        self.host_ip = host_ip 
        self.send_port = send_port
        self.receive_port = receive_port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host_ip, self.receive_port))
        self.sock.setblocking(False)

        # PRIVATE VARIABLES
        self._drefs = list()
        self._stop_event = threading.Event()
        self._listener = threading.Thread(
                target=self._port_listener,
                args=(self.sock, listen_freq),
                kwargs={}
            )
        self._listener.start()

        self._datarefs = dict()

        # SEMAPHORES
        self._datarefs_sem = threading.Semaphore()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        for d in self._drefs:
            self.subscribe_to_dataref(d, freq=0)
        self._stop_event.set()
        self._listener.join()

    # PRIVATE METHODS 

    def _port_listener(self, sock, freq):
        BUFFER_SIZE = 65534
        while not self._stop_event.is_set():
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                for k, v in self._decode_message(data):
                    self._datarefs_sem.acquire()
                    self._datarefs[k] = v
                    self._datarefs_sem.release()
            except BlockingIOError:
                time.sleep(1/freq)

    def _decode_message(self, msg):
        if not msg.startswith(b'RREF,'):
            raise Exception(
                    f'Message should start with "RREF,", it starts with {msg[:5]}'
                    )
        res = list()
        msg = msg[5:]
        for m in batched(msg, n=8):
            m = bytes(m)
            idx, val = struct.unpack_from('<if', m)
            if idx > len(self._drefs):
                raise Exception(
                        f'Subscriptions running in the background. pyXPUDP works'
                        ' only with no subscriptions running in the background. '
                        'Restart the simulator and ensure that no other process '
                        'is requesting datarefs from X-Plane.'
                        )
            res.append((self._drefs[idx], val))
        return res



    def send_command(self, command: str):
        message = b'CMND\x00' + command.encode()
        res = self.sock.sendto(message, (self.host_ip, self.send_port))
        return res

    def set_dataref(self, dataref, value, var_type='f'):
        message = b'DREF\x00' 
        message += struct.pack('=' + var_type, value) 
        message += dataref.encode() + b'\0xx'
        message += b' ' * (509 - len(message))
        res = self.sock.sendto(message, (self.host_ip, self.send_port))
        return res

    def subscribe_to_dataref(self, dataref, freq=1):
        if dataref not in self._drefs:
            self._drefs.append(dataref)
        idx = self._drefs.index(dataref)
        message = b'RREF\x00' 
        message += struct.pack('<i', freq) 
        message += struct.pack('<i', idx)
        message += dataref.encode() 
        message += b'\x00' * (400 - len(dataref.encode()))
        res = self.sock.sendto(message, (self.host_ip, self.send_port))
        return res
    
    def get_datarefs(self, *requested_datarefs):
        for d in requested_datarefs:
            if d not in self._drefs:
                raise Exception('Dataref is not subscribed to, '
                                'you can only get subscribed datarefs.')
        self._datarefs_sem.acquire()
        vals = [self._datarefs[key] for key in requested_datarefs]
        self._datarefs_sem.release()
        return vals
    def get_dataref(self, requested_dataref):
        return self.get_datarefs(requested_dataref)[0]
