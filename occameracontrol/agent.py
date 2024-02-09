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

from confygure import config
from dateutil.parser import parse


logger = logging.getLogger(__name__)


class Event:
    title = None
    start = -1
    end = -1

    def __init__(self, title: str, start: int, end: int):
        self.title = title
        self.start = start
        self.end = end

    def active(self):
        now = int(time.time()) * 1000
        return self.start <= now < self.end

    def future(self):
        now = int(time.time()) * 1000
        return now < self.start < self.end

    def __str__(self):
        return f'{self.title} (start: {self.start}, end: {self.end})'


class Agent:
    agent_id = None
    events: list[Event] = []

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def cutoff(self) -> int:
        '''Returns the calendar cutoff time in milliseconds.
        '''
        cutoff_seconds = config('calendar', 'cutoff') or (7 * 24 * 60 * 60)
        return (int(time.time()) + cutoff_seconds) * 1000

    def parse_calendar(self, cal):
        '''Take the calendar data from Opencast and return a list of events.
        '''
        events = []
        for event in cal:
            data = event['data']
            title = data['agentConfig']['event.title']
            start = int(parse(data['startDate'], dayfirst=True).timestamp() * 1000)
            end = int(parse(data['endDate'], dayfirst=True).timestamp() * 1000)
            event = Event(title, start, end)

            logger.debug('Got event %s', event)
            events.append(event)

        # Make sure events are sorted
        return sorted(events, key=lambda e: e.start, reverse=True)

    def update_calendar(self):
        server = config('opencast', 'server').rstrip('/')
        auth = (config('opencast', 'username'), config('opencast', 'password'))
        url = f'{server}/recordings/calendar.json'
        params = {'agentid': self.agent_id, 'cutoff': self.cutoff()}

        logger.info('Updating calendar for agent `%s`', self.agent_id)

        response = requests.get(url, auth=auth, params=params, timeout=5)
        response.raise_for_status()

        calendar = response.json()
        logger.debug('Calendar data: %s', calendar)

        self.events = self.parse_calendar(calendar)

    def active_events(self):
        '''Return a list of active events
        '''
        # Remove old events from cached events
        now = int(time.time()) * 1000
        return [e for e in self.events if e.end > now]

    def next_event(self):
        events = self.active_events()
        if not events:
            return Event('', 0, 0)
        return events[0]
