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
import time

from confygure import config
from prometheus_client import Counter, Gauge
from prometheus_client import start_http_server


logger = logging.getLogger(__name__)

request_errors = Counter('request_errors',
                         'Number of errors related to HTTP requests',
                         ('ressource', 'type'))
agent_calendar_update_total = Gauge('agent_calendar_update_total',
                                    'Nuber of calendar update',
                                    ('agent',))
agent_calendar_update_time = Gauge('agent_calendar_update_time',
                                   'Time of the last calendar update',
                                   ('agent',))
camera_position = Gauge('camera_position',
                        'Last position (preset number) a camera moved to',
                        ('camera',))


class RequestErrorHandler():
    def __init__(self, ressource, message):
        self.ressource = ressource
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            logger.exception(self.message)
            request_errors.labels(self.ressource, exc_type.__name__).inc()
        # Silence Exception types
        return exc_type is None or issubclass(exc_type, Exception)


def register_calendar_update(agent_id: str):
    agent_calendar_update_total.labels(agent_id).inc()
    agent_calendar_update_time.labels(agent_id).set(time.time())


def register_camera_move(camera: str, position: int):
    camera_position.labels(camera).set(position)


def start_metrics_exporter():
    if not config('metrics', 'enabled'):
        return

    start_http_server(
        port=config('metrics', 'port') or 8000,
        addr=config('metrics', 'addr') or '127.0.0.1',
        certfile=config('metrics', 'certfile'),
        keyfile=config('metrics', 'keyfile'))
