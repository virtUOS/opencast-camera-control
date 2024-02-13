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

from confygure import config_t, config_rt
from dateutil.parser import parse

from occameracontrol.metrics import register_calendar_update


logger = logging.getLogger(__name__)


class Event:
    '''An scheduled Opencast event from an agent's calendar.
    '''
    title: str
    start: float
    end: float

    def __init__(self, title: str, start: float, end: float):
        self.title = title
        self.start = start
        self.end = end

    def active(self) -> bool:
        '''If the event is active based on the current time
        '''
        return self.start <= time.time() < self.end

    def future(self) -> bool:
        '''If the event is in the future based on the current time.
        '''
        return time.time() < self.start < self.end

    def __str__(self):
        '''A string representation of the event
        '''
        return f'{self.title} (start: {self.start:.3f}, end: {self.end:.3f})'


class Agent:
    '''A capture agent with it's name and calendar
    '''
    agent_id: str
    events: list[Event] = []

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    def cutoff(self) -> int:
        '''Returns the calendar cutoff time in milliseconds.
        '''
        week_in_seconds = 7 * 24 * 60 * 60
        cutoff_seconds = config_t(int, 'calendar', 'cutoff') or week_in_seconds
        return (int(time.time()) + cutoff_seconds) * 1000

    def parse_calendar(self, cal) -> list[Event]:
        '''Take the calendar data from Opencast and return a list of events.
        '''
        events = []
        for event in cal:
            data = event['data']
            title = data['agentConfig']['event.title']
            start = parse(data['startDate'], dayfirst=True).timestamp()
            end = parse(data['endDate'], dayfirst=True).timestamp()
            event = Event(title, start, end)

            logger.debug('Got event %s', event)
            events.append(event)

        # Make sure events are sorted
        return sorted(events, key=lambda e: e.start, reverse=False)

    def update_calendar(self):
        '''Get a calendar update fro Opencast
        '''
        server = config_rt(str, 'opencast', 'server').rstrip('/')
        username = config_rt(str, 'opencast', 'username')
        password = config_rt(str, 'opencast', 'password')
        auth = (username, password)
        url = f'{server}/recordings/calendar.json'
        params = {'agentid': self.agent_id, 'cutoff': self.cutoff()}

        logger.info('Updating calendar for agent `%s`', self.agent_id)

        response = requests.get(url, auth=auth, params=params, timeout=5)
        response.raise_for_status()

        calendar = response.json()
        logger.debug('Calendar data: %s', calendar)

        self.events = self.parse_calendar(calendar)
        register_calendar_update(self.agent_id)

    def active_events(self):
        '''Return a list of active events
        '''
        # Remove old events from cached events
        now = time.time()
        return [e for e in self.events if e.end >= now]

    def next_event(self) -> Event:
        '''Return the next scheduled event.
        If no future events are scheduled for this agent, and empty event with
        start and end set to 0 will be returned.
        '''
        events = self.active_events()
        if not events:
            return Event('', 0, 0)
        return events[0]
