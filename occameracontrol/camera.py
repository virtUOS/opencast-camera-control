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

import logging
import requests
import time

from enum import Enum
from requests.auth import HTTPDigestAuth
from typing import Optional

from occameracontrol.agent import Agent
from occameracontrol.metrics import register_camera_move


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

    def __init__(self,
                 agent: Agent,
                 url: str,
                 type: str,
                 user: Optional[str] = None,
                 password: Optional[str] = None,
                 preset_active: int = 1,
                 preset_inactive: int = 10):
        self.agent = agent
        self.url = url.rstrip('/')
        self.type = CameraType[type]
        self.user = user
        self.password = password
        self.preset_active = preset_active
        self.preset_inactive = preset_inactive

    def __str__(self) -> str:
        '''Returns a string representation of this camera
        '''
        return f"'{self.agent.agent_id}' @ '{self.url}'"

    def move_to_preset(self, preset: int):
        '''Move the PTZ camera to the specified preset position
        '''
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
            params = {'PresetCall': preset}
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

    def update_position(self):
        '''Check for currently active events with the camera's capture agent
        and move the camera to the appropriate (active, inactive) position if
        necessary.
        '''
        agent_id = self.agent.agent_id
        event = self.agent.next_event()

        if event.future():
            logger.info('[%s] Next event `%s` starts in %i seconds',
                        agent_id, event.title, event.start - time.time())
        elif event.active():
            logger.info('[%s] Active event `%s` ends in %i seconds',
                        agent_id, event.title, event.end - time.time())
        else:
            logger.info('[%s] No planned events', agent_id)

        if event.active():
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
