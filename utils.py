import socket
import struct

from itertools import batched
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

    if dref not in _drefs:
        _drefs.append(dref)
    idx = _drefs.index(dref)
    # print(f'Sending RREF request. {_drefs =}, {dref = }, {idx = }')

    message = b'RREF\x00' 
    message += struct.pack('<i', freq) 
    message += struct.pack('<i', idx)
    message += dref.encode() + b'\x00' * (400 - len(dref.encode()))
    # message += b'\x00' * (413 - len(message))
    res = sock.sendto(message, HOST)
    # print(f'RREF request sent. {_drefs =}')

def decode_message(msg):
    global _drefs

    if not msg.startswith(b'RREF,'):
        raise Exception(
                f'Message should start with "RREF,", it starts with {msg[:5]}'
                )
    res = list()
    msg = msg[5:]
    print('pruned_msg', msg)
    for m in batched(msg, n=8):
        m = bytes(m)
        idx, val = struct.unpack_from('<if', m)
        res.append((_drefs[idx], val))
    return res

def unsubscribe_from_dref(sock, dref):
    subscribe_to_dref(sock, dref, freq=0)

def unsubscribe_all(sock):
    global _drefs
    for d in _drefs:
        unsubscribe_from_dref(sock, d)

def get_dataref_once(sock, dref):
    subscribe_to_dref(sock, dref, freq=5)
    for _ in range(10):
        val = next(listen_to_port(sock, once=True))
        val = decode_message(val)
        time.sleep(1)
        # print('Decoded:', val)
        if any(i != 0.0 for _, i in val):
            print('\nSUCCESS HELL YEAH\n')
    unsubscribe_from_dref(sock, dref)
    return val

def listen_to_port(sock, once=False):
    # BUFFER_SIZE = 4096
    BUFFER_SIZE = 65535 # Use if more size needed. No big memory penalty.
    if once:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        yield data
    else:
        while True:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            yield data

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 49001))
    if False: # Check send_command
        send_command(sock, 'sim/flight_controls/flaps_down')
        time.sleep(1)
        send_command(sock, 'sim/flight_controls/flaps_up')
        time.sleep(1)
    if False: # Check set_dataref
        set_dataref(sock, 'sim/cockpit/autopilot/heading_mag', 180, 'f')
        time.sleep(1)
        set_dataref(sock, 'sim/cockpit/autopilot/heading_mag', 0, 'f')
        time.sleep(0)
    if True: # Check for subscriptions
        # set_dataref(sock, 'sim/cockpit/autopilot/heading_mag', 180, 'f')
        # print('HDG set 180')
        time.sleep(0.1)
        print('RECEIVED:', get_dataref_once(sock, 'sim/cockpit/autopilot/heading_mag'))
        time.sleep(1)

        # set_dataref(sock, 'sim/cockpit/autopilot/heading_mag', 0, 'f')
        # print('HDG set 0')
        time.sleep(0.1)
        print('RECEIVED:', get_dataref_once(sock, 'sim/cockpit/autopilot/heading_mag'))
        print('RECEIVED:', get_dataref_once(sock, 'sim/cockpit/radios/com1_freq_hz'))
        exit()
        subscribe_to_dref(sock, 'sim/cockpit/autopilot/heading_mag', freq=5)
        subscribe_to_dref(sock, 'sim/cockpit/radios/com1_freq_hz', freq=5)
        for _ in range(1):
            val = next(listen_to_port(sock, once=True))
            val = decode_message(val)
            time.sleep(1)
            print('Decoded:', val)
    unsubscribe_all(sock)
