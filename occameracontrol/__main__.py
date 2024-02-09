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
import logging
import requests
import time
import threading

from confygure import setup, config
from dateutil.parser import parse
from datetime import datetime as dt

from occameracontrol.camera import Camera


logger = logging.getLogger(__name__)


def cutoff():
    ''' calculate the offset of now + 1 week
    '''
    return (int(time.time()) + 7*24*60*60)*1000


def parse_calendar(cal):
    '''Take the calendar data from Opencast and return a list of event data.
    '''
    events = []
    for event in cal:
        data = event['data']
        title = data['agentConfig']['event.title']
        logger.debug('Got event `%s` (start: %s, end: %s)',
                     title, data['startDate'], data['endDate'])

        start = int(parse(data['startDate'], dayfirst=True).timestamp() * 1000)
        end = int(parse(data['endDate'], dayfirst=True).timestamp() * 1000)

        events.append((title, start, end))
    return events


def get_calendar(agentId):
    server = config('opencast', 'server').rstrip('/')
    auth = (config('opencast', 'username'), config('opencast', 'password'))
    url = f'{server}/recordings/calendar.json'
    params = {'agentid': agentId, 'cutoff': cutoff()}

    logger.info('Updating calendar for agent `%s`', agentId)

    response = requests.get(url, auth=auth, params=params)
    response.raise_for_status()

    calendar = response.json()
    logger.debug('Calendar data: %s', calendar)

    return parse_calendar(calendar)


def calendar_loop(cameras: list):
    pass


def camera_loop(camera: Camera):
    last_updated = 0
    while True:
        # Update calendar
        if time.time() - last_updated > config('calendar', 'update_frequency'):
            events = get_calendar(camera.agent_id)
            # reverse sort, so pop returns the next event
            events = sorted(events, key=lambda x: x[1], reverse=True)
            last_updated = time.time()

        # Remove old events
        now = int(time.time()) * 1000
        events = [e for e in events if e[2] > now]

        # Set start end end to 0 if there is no event
        title, start, end = events[0] if events else ('', 0, 0)
        if now < start < end:
            logger.info('[%s] Next planned event `%s` starts in %s seconds',
                        camera.agent_id, title, (start - now) / 1000)
        elif start <= now < end:
            logger.info('[%s] Active events `%s` ends in %s seconds',
                        camera.agent_id, title, (end - now) / 1000)
        else:
            logger.info('[%s] No planned events', camera.agent_id)

        if start <= now < end:
            # TODO: Preset numbers should not be hard-coded
            if camera.position != 1:
                logger.info('[%s] Event `%s` started', camera.agent_id, title)
                logger.info('[%s] Moving to preset 1', camera.agent_id)
                # Move to recording preset
                camera.setPreset(1)

        else:  # No active event
            if camera.position != 10:
                # Return to netral preset
                logger.info('[%s] Returning to preset 10', camera.agent_id)
                camera.setPreset(10)

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

    setup(files=config_files, logger=('loglevel',))

    cameras = []
    for agent_id, agent_cameras in config('camera').items():
        logger.debug('Configuring agent %s', agent_id)
        for camera in agent_cameras:
            cam = Camera(agent_id, **camera)
            logger.debug('Configuring camera: %s', cam)
            cameras.append(cam)

    # TODO Create a list / dict of cameras
    threads = []
    for camera in cameras:
        logger.info('Starting camera control for %s @ %s',
                    camera.agent_id, camera.url)
        camera_control = threading.Thread(target=camera_loop, args=(camera,))
        threads.append(camera_control)
        camera_control.start()

    # Don't need that I think. Should implement restarting of a thread if function fails for some reason
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
