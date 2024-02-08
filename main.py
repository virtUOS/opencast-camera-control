# Opencast Camera Control
# Copyright 2024 Osnabrück University, virtUOS
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import argparse
import requests
import time
import threading
import camera as cam

from confygure import setup, config
from dateutil.parser import parse
from datetime import datetime as dt

# Use command createCA for creation of capture agent. Has to be done daily.


# Works
def getCutoff():
    # calculate the offset of now + 1 week
    return (int(time.time()) + 7*24*60*60)*1000


def printPlanned(cal):
    events = []
    for event in cal:
        data = event['data']
        print("\nEvent Name: ", data['agentConfig']['event.title'])
        print("Start: ", data['startDate'])
        print("End Date: ", data['endDate'])

        start = int(dt.strptime(str(parse(data['startDate'], dayfirst=True)), '%Y-%m-%d %H:%M:%S').timestamp() * 1000)
        end = int(dt.strptime(str(parse(data['endDate'], dayfirst=True)), '%Y-%m-%d %H:%M:%S').timestamp() * 1000)

        print(start, end, end-start)

        events.append((data['agentConfig']['event.title'], start, end))
    return events


def getCalendar(agentId, cutoff, verbose=False):
    server = config('opencast', 'server').rstrip('/')
    auth = (config('opencast', 'username'), config('opencast', 'password'))
    url = f'{server}/recordings/calendar.json'
    params = {'agentid': agentId, 'cutoff': cutoff}
    print("[" + agentId + "] REQUEST:", url)

    calendar = requests.get(url, auth=auth, params=params)
    if verbose:
        print("STATUS:", calendar.status_code)
        print("JSON:", calendar.json())

    events = printPlanned(calendar.json())

    return events, calendar.status_code, calendar


def calendar_loop(cameras: list):
    pass


def camera_loop(camera: cam.camera):
    last_updated = 0
    while True:
        # Update calendar
        if time.time() - last_updated > config('calendar', 'update_frequency'):
            events, _, _ = getCalendar(camera.ID, getCutoff())
            # reverse sort, so pop returns the next event
            events = sorted(events, key=lambda x: x[1], reverse=True)
            last_updated = time.time()

        # Remove old events
        now = int(time.time()) * 1000
        events = [e for e in events if e[2] > now]

        # Set start end end to 0 if there is no event
        title, start, end = events[0] if events else ('', 0, 0)
        if now < start < end:
            print("[" + camera.ID + "] Next planned event is \'" + title+"\' in " + str((start - now)/1000) + " seconds")
        elif start <= now < end:
            print("[" + camera.ID + "] Active events \'" + title+"\' ends in " + str((end - now)/1000) + " seconds")
        else:
            print("[" + camera.ID + "] No planned events")

        if (start - now)/1000 == 3:
            print("[" + camera.ID + "] 3...")
        elif (start - now)/1000 == 2:
            print("[" + camera.ID + "] 2...")
        elif (start - now)/1000 == 1:
            print("[" + camera.ID + "] 1...")

        if start <= now < end:
            # TODO: Preset numbers should not be hard-coded
            if camera.pos != 1:
                print("[" + camera.ID + "] Event \'" + title + "\' has started!")
                # Move to recording preset
                print("[" + camera.ID + "] Move to Preset 1 for recording...")
                camera.setPreset(1, True)

        else:  # No active event
            if camera.pos != 10:
                # Return to netral preset
                print("[" + camera.ID + "] Event \'" + title + "\' has ended!")
                print("[" + camera.ID + "] Return to Preset \'Home\'...")
                camera.setPreset(10, True)

        time.sleep(1)


def main():
    parser = argparse.ArgumentParser(description='Opencast Camera Control')
    parser.add_argument(
        '-c', '--config',
        type=str,
        default=None,
        help='Path to a configuration file'
    )
    args = parser.parse_args()
    config_files = (
            './camera-control.yml',
            '~/camera-control.yml',
            '/etc/camera-control.yml')
    if args.config:
        config_files = (args.config,)

    setup(files=config_files, logger=('loglevel'))

    cameras = config('camera')
    for agentID in cameras.keys():
        print(agentID)
        for camera in cameras[agentID]:
            print(f'- {camera["url"]}')
            print(f'  {camera["type"]}')

    cameras_list = list()
    for agentID, agent_cameras in cameras.items():
        for camera in agent_cameras:
            c = cam.camera(agentID, camera['url'], camera['type'], "", 10, 0)
            c.updateCalendar(getCalendar(c.ID, getCutoff()))
            cameras_list.append(c)

    for c in cameras_list:
        print(c)

    # TODO Create a list / dict of cameras
    threads = list()
    for camera in cameras_list:
        print(camera.ID, camera.url, camera.manufacturer)

        print("Starting Thread for ", camera.ID, " @ ", camera.url)
        x = threading.Thread(target=camera_loop, args=(camera,))
        threads.append(x)
        x.start()

    # Don't need that I think. Should implement restarting of a thread if function fails for some reason
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
