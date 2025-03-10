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

import datetime
import logging
import requests
import time

from confygure import config_t
from enum import Enum
from requests.auth import HTTPDigestAuth
from typing import Optional

from occameracontrol.agent import Agent
from occameracontrol.metrics import register_camera_move, \
        register_camera_expectation


logger = logging.getLogger(__name__)


class CameraType(Enum):
    '''Enumm with supported camera manufacturer types
    '''
    sony = 'sony'
    panasonic = 'panasonic'


class Camera:
    '''A camera with data about its web interface
    '''
    agent: Agent
    password: Optional[str] = None
    position: int = -1
    type: CameraType
    url: str
    user: Optional[str] = None
    preset_active: int = 1
    preset_inactive: int = 10
    last_updated: float = 0.0
    update_frequency: int = 300
    # Flag for switching between automatic and manual camera control
    # automatic  = The corresponding camera will be controlled automatically,
    #              i.e. the camera position will be adjusted
    #              according to the agent's state and the values given
    #              in preset_active and preset_inactive
    # manual     = The corresponding camera will be controlled manually.
    #              Values in preset_active and preset_inactive will
    #              be ignored as well as the agent's status
    control: str = "automatic"

    def __init__(self,
                 agent: Agent,
                 url: str,
                 type: str,
                 user: Optional[str] = None,
                 password: Optional[str] = None,
                 preset_active: int = 1,
                 preset_inactive: int = 10,
                 control: str = "automatic"):
        self.agent = agent
        self.url = url.rstrip('/')
        self.type = CameraType[type]
        self.user = user
        self.password = password
        self.preset_active = preset_active
        self.preset_inactive = preset_inactive
        self.update_frequency = config_t(int, 'camera_update_frequency') or 300
        self.control = control

    def __str__(self) -> str:
        '''Returns a string representation of this camera
        '''
        return f"'{self.agent.agent_id}' @ '{self.url}'"

    def activate_camera(self, on=True):
        """Activate the camera or put it into standby mode.
        :param bool on: camera should be online or standby (default: True)
        """
        if self.type == CameraType.panasonic:
            url = f'{self.url}/cgi-bin/aw_ptz'
            command = '#On' if on else '#Of'
            params = {'cmd': command, 'res': 1}
            auth = (self.user, self.password) \
                if self.user and self.password else None
            logger.debug('GET %s with params: %s', url, params)
            response = requests.get(url, auth=auth, params=params, timeout=5)
            response.raise_for_status()

        elif self.type == CameraType.sony:
            url = f'{self.url}/command/main.cgi'
            command = 'on' if on else 'standby'
            params = {'System': command}
            headers = {'referer': f'{self.url}/'}
            auth = HTTPDigestAuth(self.user, self.password) \
                if self.user and self.password else None
            logger.debug('GET %s with params: %s', url, params)
            response = requests.get(url,
                                    auth=auth,
                                    headers=headers,
                                    params=params,
                                    timeout=5)
            response.raise_for_status()

    def move_to_preset(self, preset: int):
        '''Move the PTZ camera to the specified preset position
        '''
        self.activate_camera()
        register_camera_expectation(self.url, preset)
        if self.type == CameraType.panasonic:
            params = {'cmd': f'#R{preset - 1:02}', 'res': 1}
            url = f'{self.url}/cgi-bin/aw_ptz'
            auth = (self.user, self.password) \
                if self.user and self.password else None
            logger.debug('GET %s with params: %s', url, params)
            response = requests.get(url, auth=auth, params=params, timeout=5)
            response.raise_for_status()

        elif self.type == CameraType.sony:
            url = f'{self.url}/command/presetposition.cgi'
            params = {'PresetCall': f'{preset},24'}
            headers = {'referer': f'{self.url}/'}
            auth = HTTPDigestAuth(self.user, self.password) \
                if self.user and self.password else None
            logger.debug('GET %s with params: %s', url, params)
            response = requests.get(url,
                                    auth=auth,
                                    headers=headers,
                                    params=params,
                                    timeout=5)
            response.raise_for_status()

        self.position = preset
        register_camera_move(self.url, preset)
        self.last_updated = time.time()

    def from_now(self, ts: float) -> str:
        '''Get a string representation of the time until the provided time
        stamp is reached.
        '''
        seconds = int(ts - time.time())  # seconds are enough accuracy
        return str(datetime.timedelta(seconds=seconds))

    def check_calendar(self):
        agent_id = self.agent.agent_id
        level = logging.DEBUG if int(time.time()) % 60 else logging.INFO

        while not self.agent.calendar_initialized:
            logger.log(level, '[%s] Calendar not yet initialized…', agent_id)
            time.sleep(1)

        event = self.agent.next_event()
        if event.future():
            logger.log(level, '[%s] Next event `%s` starts in %s',
                       agent_id, event.title[:40], self.from_now(event.start))
        elif event.active():
            logger.log(level, '[%s] Active event `%s` ends in %s',
                       agent_id, event.title[:40], self.from_now(event.end))
        else:
            logger.log(level, '[%s] No planned events', agent_id)

        return event

    def update_position(self):
        '''Check for currently active events with the camera's capture agent
        and move the camera to the appropriate (active, inactive) position if
        necessary.
        '''
        agent_id = self.agent.agent_id
        event = self.check_calendar()
        if event.active():  # active event
            if self.position != self.preset_active:
                logger.info('[%s] Event `%s` started', agent_id, event.title)
                logger.info('[%s] Moving to preset %i', agent_id,
                            self.preset_active)
                self.move_to_preset(self.preset_active)
        else:  # No active event
            if self.position != self.preset_inactive:
                logger.info('[%s] Returning to preset %i', agent_id,
                            self.preset_inactive)
                self.move_to_preset(self.preset_inactive)

        if time.time() - self.last_updated >= self.update_frequency:
            logger.info('[%s] Re-sending preset %i to camera', agent_id,
                        self.position)
            self.move_to_preset(self.position)
