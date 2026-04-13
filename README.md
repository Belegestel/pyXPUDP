# X-Plane UDP
The goal of this package is to allow for high-level, abstract communication with X-Plane via UDP without having to configure the connections manually. It is verified to work with X-Plane 12.4.0.
## Installation 
To install the package, simply type in your terminal 
```
python3 -m pip install pyxpudp
```
## Python API Documentation
The central point of the library is the `XPConnector` X-Plane connection object. It can be used either by normally creating the object and calling `.close()` to terminate the connection, or you can use the `with` construction, as in the [example file](https://github.com/Belegestel/pyXPUDP/blob/master/src/pyXPUDP/example.py). At the moment, it implements a few basic methods, as described below. All of the snippets should be functional in the default C172.

To get the object, simply call 
```py
with XPConnector():
    pass
```
Of course, it's allowed to specify :
- `host_ip` (default `'localhost'`)
- `send_port` (port, to which the messages will be sent, default `49000`)
- `receive_port` (port, that will receive messages from X-Plane, default `49001`)
- `listen_freq` (frequency of checking for new messages from X-Plane)

### Send command
Execute a command.
```py 
with XPConnector() as conn: 
    conn.send_command('sim/flight_controls/flaps_down')
```

### Set dataref 
Pass the dataref name, then value. Then, optionally the dataref type.
```py 
with XPConnector() as conn:
    conn.set_dataref('sim/cockpit/autopilot/heading_mag', 180)
```

### Subscribe to dataref
Subscribing to dataref allows you to fetch its value later on. Fetching without previous subscription automatically subscribes with the frequency of 1Hz.
Pass the dataref and then, optionally, the frequency, at which X-Plane is to send the data. 
To unsubscribe, send the subscription message with `freq=0`.
```py 
with XPConnector() as conn:
    conn.subscribe_to_dataref('sim/cockpit/autopilot/heading_mag')
```

### Get the value of a single dataref
To get the value of a single dataref, pass the dataref name. Optionally you can pass the is_blocking parameter - if it's `True` (default) the code will block until the dataref is received. If it's `False`, the requested dataref will return `None` if it has not been received yet. 
If the dataref hasn't been subscribed to before, it'll automatically subscribe at the frequency of 1Hz. Note, that in this case, the `is_blocking` is forced to be `True`.
```py 
with XPConnector() as conn:
    value = conn.get_dataref(
        'sim/cockpit/autopilot/heading_mag',
        is_blocking=False
    )
```

### Subscribe to multiple datarefs
This function is a simple way to subscribe to multiple datarefs.
Pass the dataref names and then, optionally, the frequency (keyword argument).
```py 
with XPConnector() as conn:
    conn.subscribe_to_datarefs(
        'sim/cockpit/autopilot/heading_mag',
        'sim/cockpit/radios/transponder_code',
        freq=2 
    )
```

### Get multiple datarefs 
This function is a simple way to subscribe to multiple datarefs.
Pass the dataref names and then, optionally, the is_blocking value (keyword argument). The last argument is documented in the `get_dataref` section.
```py 
with XPConnector() as conn:
    received_datarefs = conn.get_datarefs(
        'sim/cockpit/autopilot/heading_mag',
        'sim/cockpit/radios/transponder_code',
        is_blocking=False
    )
```

### Close the connection 
If not using the `with` construction, close the connection manually. Otherwise, the background threads will not terminate.
```py
conn = XPConnector()
conn.close()
```

## Callbacks 

### Register a callback 
```py 
with XPConnector() as conn:
    handle = conn.add_callback(func)
```
If the function is supposed to be ran only for a specific dataref, you can use the following syntax:
```py 
with XPConnector() as conn:
    handle = conn.add_callback(func, key='sim/cockpit/autopilot/heading_mag')
```

### Close all callbacks 
```py
with XPConnector() as conn:
    handle = conn.add_callback(func)
    ...
    conn.remove_callbacks()
```
If the function is supposed to wait for the scheduled callbacks to stop running:
```py
with XPConnector() as conn:
    handle = conn.add_callback(func)
    ...
    conn.remove_callbacks(stop_scheduled=False)
```

### Handles
Every callback returns a handle. This handle can be used to remove a callback:
```py
with XPConnector() as conn:
    handle = conn.add_callback(func)
    ...
    handle.remove()
```
Be advised, removing a callback that's already been removed will result in an exception.
