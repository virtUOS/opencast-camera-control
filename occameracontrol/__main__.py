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

from confygure import setup, config
from threading import Thread

from occameracontrol.agent import Agent
from occameracontrol.camera import Camera


logger = logging.getLogger(__name__)


def update_agents(agents: list[Agent]):
    while True:
        for agent in agents:
            try:
                agent.update_calendar()
            except requests.exceptions.HTTPError as e:
                logger.error('Failed to update calendar of agent %s: %s',
                             agent.agent_id, e)
        time.sleep(config('calendar', 'update_frequency'))


def control_camera(camera: Camera):
    while True:
        try:
            camera.update_position()
        except requests.exceptions.HTTPError as e:
            logger.error('Failed to communicate with camera %s: %s', camera, e)
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
    agents = []
    for agent_id, agent_cameras in config('camera').items():
        agent = Agent(agent_id)
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
        logger.info('Starting camera control for %s', camera)
        control_truead = Thread(target=control_camera, args=(camera,))
        threads.append(control_truead)
        control_truead.start()

    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
