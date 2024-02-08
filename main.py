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
import json
import time
import threading

from confygure import setup, config
from dateutil.parser import parse
from datetime import datetime as dt
from requests.auth import HTTPDigestAuth

# Use command createCA for creation of capture agent. Has to be done daily.


# Works
def getCutoff():
    # calculate the offset of now + 1 week
    cutoff = (round(time.time()) + 7*24*60*60)*1000

    #print("Cutoff =",cutoff)
    return cutoff


# Works fine for now
# TODO: test for all possible presets
def setPreset(preset, camera, manufacturer, verbose=False):
    code = -1
    camera = camera.rstrip('/')
    print(camera, manufacturer)
    if manufacturer == "panasonic":
        if 0 <= preset <= 100:
            print("PANASONIC")
            params = {'cmd': f'#R{preset - 1:02}', 'res': 1}
            url = f'{camera}/cgi-bin/aw_ptz'
            auth = ('<user>', '<password>')
            if verbose:
                print("URL:" + url)
            code = requests.get(url, auth=auth, params=params)

        else:
            print("Could not use the specified preset number, because it is out of range.\nThe Range is from 0 to 100 (including borders)")
            return code
    elif manufacturer == "sony":
        if 1 <= preset <= 10:
            print("SONY")
            # Presets start at 1 for Sony cameras
            url = f'{camera}/command/presetposition.cgi'
            params = {'PresetCall': preset}
            auth = HTTPDigestAuth('<user>', '<password>')
            headers = {'referer': f'{camera}/'}
            if verbose:
                print("URL:" + url)
            code = requests.get(url, auth=auth, headers=headers, params=params)
            print(code)
        return code
    else:
        print("Could not use the specified preset number, because it is out of range.\nThe Range is from 1 to 10 (including borders)")
        return code


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


def loop(agentID, url, manufacturer):
    # Currently known camera position
    position = -1

    last_updated = 0
    while True:
        # Update calendar
        if time.time() - last_updated > config('calendar', 'update_frequency'):
            events, _, _ = getCalendar(agentID, getCutoff())
            # reverse sort, so pop returns the next event
            events = sorted(events, key=lambda x: x[1], reverse=True)
            last_updated = time.time()

        # Remove old events
        now = int(time.time()) * 1000
        events = [e for e in events if e[2] > now]

        # Set start end end to 0 if there is no event
        title, start, end = events[0] if events else ('', 0, 0)
        if now < start < end:
            print("[" + agentID + "] Next planned event is \'" + title+"\' in " + str((start - now)/1000) + " seconds")
        elif start <= now < end:
            print("[" + agentID + "] Active events \'" + title+"\' ends in " + str((end - now)/1000) + " seconds")
        else:
            print("[" + agentID + "] No planned events")

        if (start - now)/1000 == 3:
            print("[" + agentID + "] 3...")
        elif (start - now)/1000 == 2:
            print("[" + agentID + "] 2...")
        elif (start - now)/1000 == 1:
            print("[" + agentID + "] 1...")

        if start <= now < end:
            # TODO: Preset numbers should not be hard-coded
            if position != 1:
                print("[" + agentID + "] Event \'" + title + "\' has started!")
                # Move to recording preset
                print("[" + agentID + "] Move to Preset 1 for recording...")
                setPreset(1, url, manufacturer, True)
                position = 1

        else:  # No active event
            if position != 10:
                # Return to netral preset
                print("[" + agentID + "] Event \'" + title + "\' has ended!")
                print("[" + agentID + "] Return to Preset \'Home\'...")
                setPreset(10, url, manufacturer, True)
                position = 10

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
    print(cameras)
    for agentID in cameras.keys():
        print(agentID)
        for camera in cameras[agentID]:
            print(f'- {camera["url"]}')
            print(f'  {camera["type"]}')

    threads = list()
    for agentID, agent_cameras in cameras.items():
        for camera in agent_cameras:
            url = camera['url']
            manufacturer = camera['type']

            print(agentID, url, manufacturer)

            print("Starting Thread for ", agentID, " @ ", url)
            x = threading.Thread(target=loop, args=(agentID, url, manufacturer))
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
