import socket
import struct
import threading
import time
from itertools import batched

from .callbacks import _CallbackDispatcher


class XPConnector:
    '''
    Class, that serves as the main connection between the python script and X-Plane.
    '''

    def __init__(self,
                 host_ip=None,
                 send_port=49000,
                 listen_ip='0.0.0.0',
                 receive_port=0,
                 listen_freq=5,
                 max_callback_thread_workers=None
                 ):
        '''
        host_ip: IP address of the machine on which X-Plane is running
        send_port: port, to which the messages are sent (on which X-Plane is listening)
            Default is 49000
        listen_ip: IP at which the client will listen to X-Plane responses, default 0.0.0.0
            (therefore messages to the selected port coming to all possible IPs)
        receive_port: port, on which the client receives messages from X-Plane. 
            Default is 0 (system assigned)
        listen_freq: frequency, at which a background thread checks for new messages 
        max_callback_thread_workers: maximum number of threads handling the callbacks. 
            Default is None (unlimited)
        '''
        self.host_ip = host_ip if host_ip is not None else 'localhost'
        self.send_port = send_port 

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((listen_ip, receive_port))
        self.sock.settimeout(1 / listen_freq)

        # PRIVATE VARIABLES
        self._drefs = list()    # Names of the datarefs
        self._datarefs = dict() # Dict of datarefs name-value

        self._drefs_lock = threading.Lock()

        self._datarefs_lock = threading.Lock()
        self._dataref_update_condition = threading.Condition(self._datarefs_lock)
        self._stop_event = threading.Event()

        self._listener = threading.Thread(
                target=self._port_listener,
                args=(self.sock, listen_freq),
                kwargs={}
            )
        self._listener.start()

        # Callbacks 
        self._callback_dispatcher = _CallbackDispatcher(max_callback_thread_workers)


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _get_drefs(self):
        with self._drefs_lock:
            return self._drefs.copy()


    def close(self):
        '''
        When not created with the `with` syntax, close() must be called when exiting
        the program. Otherwise, some threads will keep running indefinitely.
        '''
        for d in self._get_drefs():
            self.subscribe_to_dataref(d, freq=0)
        self._stop_event.set()
        self._listener.join()

    # PRIVATE METHODS 

    def _port_listener(self, sock, freq):
        BUFFER_SIZE = 65534
        has_updated = False
        while not self._stop_event.is_set():
            try:
                data, addr = sock.recvfrom(BUFFER_SIZE)
                with self._datarefs_lock:
                    for k, v in self._decode_message(data):
                        self._datarefs[k] = v
                        self._callback_dispatcher._run_callbacks(k, v)
                has_updated = True
            except (BlockingIOError, TimeoutError):
                if has_updated: # end of data stream
                    with self._datarefs_lock:
                        self._dataref_update_condition.notify_all()
                has_updated = False
                # time.sleep(1/freq)

    def _decode_message(self, msg):
        if not msg.startswith(b'RREF,'):
            raise Exception(
                    f'Message should start with "RREF,", it starts with {msg[:5]}'
                    )
        res = list()
        msg = msg[5:]
        drefs = self._get_drefs()
        for m in batched(msg, n=8):
            m = bytes(m)
            idx, val = struct.unpack_from('<if', m)
            if idx > len(drefs):
                raise Exception(
                        f'Subscriptions running in the background. pyXPUDP works'
                        ' only with no subscriptions running in the background. '
                        'Restart the simulator and ensure that no other process '
                        'is requesting datarefs from X-Plane.'
                        )
            res.append((drefs[idx], val))
        return res


    # X-PLANE API
    def send_command(self, command: str):
        '''
        Sends a command to X-Plane. 
        command: the command to send
        '''
        message = b'CMND\x00' + command.encode()
        res = self.sock.sendto(message, (self.host_ip, self.send_port))
        return res

    def set_dataref(self, dataref, value, var_type='f'):
        '''
        Sets an X-Plane dataref.
        dataref: dataref to set 
        value: value of the dataref 
        var_type: variable type of the dataref. For available types, check:
            https://docs.python.org/3/library/struct.html#format-characters
        '''
        message = b'DREF\x00' 
        message += struct.pack('=' + var_type, value) 
        message += dataref.encode() + b'\0xx'
        message += b' ' * (509 - len(message))
        res = self.sock.sendto(message, (self.host_ip, self.send_port))
        return res

    def subscribe_to_dataref(self, dataref, freq=1):
        '''
        Subscribes to a dataref. This means that X-Plane will keep sending the 
            dataref to this machine with the `freq` frequency. Note that this 
            is not the same as the `listen_freq` parameter of `XPConnector`.
            When a dataref is subscribed to, the script can use the `get_dataref`
            method to retrieve its value. To unsubscribe, send a subscription 
            request with `freq = 0`. All datarefs are automatically unsubscribed when 
            leaving the `with` block or when calling `close()`.
        dataref: dataref to subscribe to.
        freq: frequency of X-Plane sending the data
        '''
        drefs = self._get_drefs()
        if dataref not in drefs:
            with self._drefs_lock:
                self._drefs.append(dataref)
        idx = drefs.index(dataref)
        message = b'RREF\x00' 
        message += struct.pack('<i', freq) 
        message += struct.pack('<i', idx)
        message += dataref.encode() 
        message += b'\x00' * (400 - len(dataref.encode()))
        res = self.sock.sendto(message, (self.host_ip, self.send_port))
        return res

    def subscribe_to_datarefs(self, *datarefs, freq=1):
        '''
        Generalization of the `subscribe_to_dataref` method. Allows the script to 
            subscribe to multiple datarefs at once. 
        freq: frequency of X-Plane sending the data
        '''
        for d in datarefs:
            self.subscribe_to_dataref(d, freq)

    def get_datarefs(self, *requested_datarefs, is_blocking=True):
        '''
        Retrieves the values of the provided datarefs. If the dataref hasn't been sent 
            yet, this will block the code until it is received. This behavior can 
            be changed to returning a null value with the `is_blocking` parameter.
            If the dataref hasn't been subscribed to yet, the function automatically 
            subscribes to it. In that case, it'll be blocking regardless of the 
            `is_blocking` value.
        requested_datarefs: one or more datarefs that the user desires to retrieve.
        is_blocking: parameter that allows the user to either block the code (default)
            or to return a null value whenever the desired dataref hasn't been 
            received yet.
        Returns: list of retrieved dataref values, in order.
        '''
        drefs = self._get_drefs()
        missing_datarefs = [d for d in requested_datarefs if d not in drefs]
        if len(missing_datarefs) != 0:
            is_blocking = True 
            with self._drefs_lock:
                self._drefs.extend(missing_datarefs)
            self.subscribe_to_datarefs(*missing_datarefs)
        with self._datarefs_lock:
            while is_blocking and any(
                    d not in self._datarefs.keys() for d in requested_datarefs
                    ):
                self._dataref_update_condition.wait()
            vals = [self._datarefs.get(key, None) for key in requested_datarefs]
        return vals

    def get_dataref(self, requested_dataref, is_blocking=False):
        '''
        A simplified version of `get_datarefs` that fetches a single dataref only.
        requested_dataref: dataref the user desires to retrieve
        Returns: the value of the dataref
        '''
        return self.get_datarefs(requested_dataref, is_blocking=is_blocking)[0]

    def add_callback(self, callback, key=None, auto_subscribe=True):
        '''
        Used to add a callback. It will be executed either when the dataref equals
            to the optional `key` argument or whenever a new dataref update is received.
            If the dataref is not subscribed to yet, it'll automatically be subscribed to, 
            unless specified otherwise (`auto_subscribe=False`)
        callback: callback function. Should take two arguments: 
            - key (received dataref name) and 
            - value
        key: key filtering the callback execution. Function is ran only 
            with datarefs matching the key. If `None`, then the function is 
            ran regardless of the received dataref.
        auto_subscribe: automatically subscribe to the dataref if it's not been subscribed 
            to yet. Optional, defaults to `True`
        returns: callback handle:
            - has a remove() function that removes the callback
        '''
        if key is not None and auto_subscribe and key not in self._get_drefs():
            self.subscribe_to_dataref(key)
        return self._callback_dispatcher._add_callback(callback, key=key)
