from xpudp import XPConnector
from time import sleep

with XPConnector('127.0.0.1', 49000, 49001) as conn:
    conn.send_command('sim/flight_controls/flaps_down')
    sleep(3)
    conn.send_command('sim/flight_controls/flaps_up')
    sleep(2)
    conn.set_dataref('sim/cockpit/autopilot/heading_mag', 180)
    sleep(2)
    conn.set_dataref('sim/cockpit/autopilot/heading_mag', 0)

    conn.subscribe_to_dataref('sim/cockpit/autopilot/heading_mag')
    while (val := conn.get_dataref('sim/cockpit/autopilot/heading_mag')) < 180:
        sleep(1)
        print(f'Nope, value {val} less than 180!')
    print('Done :D')
