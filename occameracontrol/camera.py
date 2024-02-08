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

import requests
from requests.auth import HTTPDigestAuth


class Camera:
    def __init__(self, ID="", url="", manufacturer="", calendar="", pos=-1, status=0):
        self.ID = ID
        self.url = url
        self.manufacturer = manufacturer
        self.calendar = calendar
        self.pos = pos
        self.status = status

        print("Initialized: ", self)

    def __str__(self):
        return f"\'{self.ID}\' @ \'{self.url}\' (Type: \'{self.manufacturer}\') (Current Position: {self.pos})"

    def updateCalendar(self, calendar):
        self.calendar = calendar

    def setPreset(self, preset, verbose=False):
        # TODO: If code 200 --> update self.pos
        code = -1
        camera = self.url.rstrip('/')
        if self.manufacturer == "panasonic":
            if 0 <= preset <= 100:
                params = {'cmd': f'#R{preset - 1:02}', 'res': 1}
                url = f'{camera}/cgi-bin/aw_ptz'
                auth = ('admin', 'PASS')
                if verbose:
                    print("URL:" + url)
                code = requests.get(url, auth=auth, params=params)

            else:
                print("Could not use the specified preset number, because it is out of range.")
                print("The Range is from 0 to 100 (including borders)")
        elif self.manufacturer == "sony":
            if 1 <= preset <= 10:
                # Presets start at 1 for Sony cameras
                url = f'{camera}/command/presetposition.cgi'
                params = {'PresetCall': preset}
                auth = HTTPDigestAuth('admin', '<password>')
                headers = {'referer': f'{camera}/'}
                if verbose:
                    print("URL:" + url)
                code = requests.get(url, auth=auth, headers=headers, params=params)
            else:
                print("Could not use the specified preset number, because it is out of range.")
                print("The Range is from 1 to 10 (including borders)")

        else:
            print("Unknown Camera Type \'%s\'.\nKnown Types are \'panasonis\' and \'sony\'." % self.manufacturer)

        if code == 200:
            self.pos = preset
        return code
