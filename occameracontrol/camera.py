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

from enum import Enum
from requests.auth import HTTPDigestAuth


logger = logging.getLogger(__name__)


class CameraType(Enum):
    sony = 'sony'
    panasonic = 'panasonic'


class Camera:
    agent_id = None
    calendar = []
    password = None
    position = -1
    type = None
    url = None
    user = None

    def __init__(self,
                 agent_id: str,
                 url: str,
                 type: str,
                 user: str | None = None,
                 password: str | None = None):
        self.agent_id = agent_id
        self.url = url.rstrip('/')
        self.type = CameraType[type]
        self.user = user
        self.password = password

    def __str__(self):
        return f"'{self.agent_id}' @ '{self.url}' " \
                f"(type: '{self.type.value}', position: {self.position})"

    def updateCalendar(self, calendar):
        self.calendar = calendar

    def setPreset(self, preset):
        if self.type == CameraType.panasonic:
            params = {'cmd': f'#R{preset - 1:02}', 'res': 1}
            url = f'{self.url}/cgi-bin/aw_ptz'
            auth = (self.user, self.password) if self.user else None
            logger.debug('GET %s with params: %s', url, params)
            response = requests.get(url, auth=auth, params=params)
            response.raise_for_status()

        elif self.type == CameraType.sony:
            url = f'{self.url}/command/presetposition.cgi'
            params = {'PresetCall': preset}
            auth = HTTPDigestAuth(self.user, self.password)
            headers = {'referer': f'{self.url}/'}
            logger.debug('GET %s with params: %s', url, params)
            response = requests.get(url, auth=auth, headers=headers, params=params)
            response.raise_for_status()

        self.position = preset
