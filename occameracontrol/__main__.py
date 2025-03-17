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
import datetime
import logging
import sys
import time

from confygure import setup, config_t, config_rt
from threading import Thread

from occameracontrol.agent import Agent
from occameracontrol.camera import Camera
from occameracontrol.metrics import start_metrics_exporter, RequestErrorHandler

from occameracontrol.camera_control_server import start_camera_control_server


logger = logging.getLogger(__name__)


def update_agents(agents: list[Agent]):
    '''Control loop for updating the capture agent calendars on a regular basis
    '''
    update_frequency = config_t(int, 'calendar', 'update_frequency') or 120
    error_handlers = {
        agent.agent_id: RequestErrorHandler(
                agent.agent_id,
                f'Failed to update calendar of agent {agent.agent_id}')
        for agent in agents}

    # Continuously update agent calendars
    while True:
        for agent in agents:
            with error_handlers[agent.agent_id]:
                agent.update_calendar()
        time.sleep(update_frequency)


def control_camera(camera: Camera, reset_time: datetime.datetime):
    """Control loop to trigger updating the camera position based on currently
    active events.
    param camera: Camera object to control
    param reset_time: datetime to reset control to automatic (default: 03:00)
    """
    if reset_time is None:
        reset_time = datetime.datetime.combine(
            date=datetime.date.today(),
            time=datetime.time(3, 00, 00)
        )
    error_handler = RequestErrorHandler(
            camera.url,
            f'Failed to communicate with camera {camera}')
    while True:
        with error_handler:
            if reset_time < datetime.datetime.now():
                logger.info(f'current time is {datetime.datetime.now()}, '
                            f'the reset time is {reset_time}')
                logger.info(f'Reset {camera} to \'automatic\'')
                camera.control = "automatic"
                camera.position = -1
                reset_time = reset_time + datetime.timedelta(days=1)
                logger.info(f'Next reset time is set to {reset_time}')
            if camera.control == "automatic":
                camera.update_position()
            else:
                camera.activate_camera()
                camera.check_calendar()
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
    config_files = [
            './camera-control.yml',
            '~/camera-control.yml',
            '/etc/camera-control.yml']
    if args.config:
        config_files = [args.config]

    setup(files=config_files, logger=['loglevel'])
    if not config_t(dict):
        print('Could not find a configuration file in', config_files)
        sys.exit(1)

    cameras = []
    agents = []
    reset_time = datetime.datetime.combine(
        date=datetime.date.today(),
        time=datetime.time.fromisoformat(config_t(str,'reset_time'))
    )
    logger.info('reset time is set to %s', reset_time)
    for agent_id, agent_cameras in config_rt(dict, 'camera').items():
        agent = Agent(agent_id)
        agent.verify_agent()
        agents.append(agent)
        logger.debug('Configuring agent %s', agent_id)
        for camera in agent_cameras:
            cam = Camera(agent, **camera)
            logger.debug('Configuring camera: %s', cam)
            cameras.append(cam)

    threads = []
    agent_update = Thread(target=update_agents, args=(agents,))
    threads.append(agent_update)
    agent_update.start()

    for camera in cameras:
        logger.info('Starting camera control for %s with control status %s',
                    camera, getattr(camera, 'control'))
        control_thread = Thread(target=control_camera,
                                args=(camera, reset_time))
        threads.append(control_thread)
        control_thread.start()

    # Start delivering metrics
    start_metrics_exporter()

    # Start camera control server
    auth = (config_rt(str, 'basic_auth', 'username'),
            config_rt(str, 'basic_auth', 'password'))
    start_camera_control_server(cameras=cameras, auth=auth)

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
