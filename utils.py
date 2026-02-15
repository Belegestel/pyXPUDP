import socket
import struct

import time

HOST = ('127.0.0.1', 49000)
HOST_RECV = ('127.0.0.1', 49001)

_drefs = []

def send_command(sock, cmd: str):
    message = b'CMND\x00' + cmd.encode()
    res = sock.sendto(message, HOST)
    return res

def set_dataref(sock, dref, value, var_type='f'):
    '''
    var_type
    ---------------+---------
    char           | c
    unsigned char  | b
    bool           | ?
    short          | h
    unsigned short | H
    int            | i
    unsigned int   | I
    long           | l
    unsigned long  | L
    long long      | q
    unsigned ll    | Q
    float          | f
    double         | d
                   |  

    https://docs.python.org/3/library/struct.html#format-characters
    '''
    message = b'DREF\x00' + struct.pack('=' + var_type, value) + dref.encode() + b'\0xx'
    message = message + b' ' * (509 - len(message))
    res = sock.sendto(message, HOST)
    return res

def subscribe_to_dref(sock, dref, freq=1):
    global _drefs
    if dref in _drefs and freq != 0:
        print('WARNING! Attempting to fetch the same dataref again:', dref)
        return -1
    message = b'RREF\x00' 
    message += struct.pack('<i', freq) 
    message += struct.pack('<i', len(_drefs))
    message += b' ' * (413 - len(message))
    res = sock.sendto(message, HOST)
    if freq != 0:
        _drefs.append(dref)
    else:
        _drefs = [i if i != dref else None for i in _drefs]
        while len(_drefs) != 0 and _drefs[-1] is None:
            _drefs = _drefs[:-1]

def unsubscribe_from_dref(sock, dref):
    subscribe_to_dref(sock, dref, freq=0)

def unsubscribe_all(sock):
    global _drefs
    for d in _drefs:
        unsubscribe_from_dref(sock, d)

def get_dataref_once(sock, *dref):
    subscribe_to_dref(sock, dref)
    val = next(listen_to_port(sock, once=True))
    # GET THE DATA SOMETHING SOMETHING
    unsubscribe_from_dref(sock, dref)
    return val

def listen_to_port(sock, once=False):
    # BUFFER_SIZE = 4096
    BUFFER_SIZE = 65535 # Use if more size needed. No big memory penalty.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind(HOST_RECV)
        if once:
            data, addr = s.recvfrom(BUFFER_SIZE)
            yield data
        else:
            while True:
                data, addr = s.recvfrom(BUFFER_SIZE)
                yield data

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if False: # Check send_command
        send_command(sock, 'sim/flight_controls/flaps_down')
        time.sleep(1)
        send_command(sock, 'sim/flight_controls/flaps_up')
        time.sleep(1)
    if True: # Check set_dataref
        set_dataref(sock, 'sim/cockpit/autopilot/heading_mag', 180, 'f')
        time.sleep(1)
        set_dataref(sock, 'sim/cockpit/autopilot/heading_mag', 0, 'f')
        time.sleep(1)
    if True: # Check for subscriptions
        print(get_dataref_once(sock, 'sim/cockpit/autopilot/heading_mag'))
