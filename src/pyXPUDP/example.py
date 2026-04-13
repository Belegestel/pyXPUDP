from pyXPUDP import XPConnector
from time import sleep

with XPConnector('192.168.137.1') as conn:
    # Send command
    conn.send_command('sim/flight_controls/flaps_down')
    sleep(3)
    conn.send_command('sim/flight_controls/flaps_up')
    sleep(2)

    # Set dataref
    conn.set_dataref('sim/cockpit/autopilot/heading_mag', 180)
    sleep(2)
    conn.set_dataref('sim/cockpit/autopilot/heading_mag', 0)

    # One of ways to get a dataref
    #conn.subscribe_to_dataref('sim/cockpit/autopilot/heading_mag')
    while (val := conn.get_dataref('sim/cockpit/autopilot/heading_mag')) < 180:
        print(f'Heading {val} is less than 180, turn the heading knob to a larger value.')
        sleep(1)
    print(f'Done, heading {val}')

    # Callbacks
    def say_hdg(_, v):
        print('Heading is', v)
    h = conn.add_callback(say_hdg)
    input() # Wait for user input before stopping the callbacks
    h.remove()
