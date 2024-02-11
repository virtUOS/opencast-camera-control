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

from confygure import config_t
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
    '''Context management object for catching request errors, log them and add
    them to the metrics. Using this you can do something like::

        handler = RequestErrorHandler('cam1', 'Unable to connect to cam 1')
        with handler:
            cam1.update()

    If `update()` raises an error, the handler will log the error but prevent
    the error from propagating any further.
    '''

    def __init__(self, resource, message):
        '''Create a RequestErrorHandler instance.

        :param ressource: Identifier of the resource
        :param message: Message to log in case of an error
        '''
        self.resource = resource
        self.message = message

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        '''Handler for then exiting the `with` block. Takes care of catching
        errors, logging them and updating the metrics.
        '''
        if exc_type:
            logger.exception(self.message)
            request_errors.labels(self.resource, exc_type.__name__).inc()
        # Silence Exception types
        return exc_type is None or issubclass(exc_type, Exception)


def register_calendar_update(agent_id: str):
    '''Update metrics for when a calendar update happened. This updates both
    the metrics for successful updates and the time of the last update.

    :param agent_id: Capture agent identifier
    '''
    agent_calendar_update_total.labels(agent_id).inc()
    agent_calendar_update_time.labels(agent_id).set(time.time())


def register_camera_move(camera: str, position: int):
    '''Update metrics for when a camera move has happened. This ensures the
    position the camera is available as part of the metrics.

    :param camera: Camera identifier
    :param position: New camera position
    '''
    camera_position.labels(camera).set(position)


def start_metrics_exporter():
    '''Start the web server for the metrics exporter endpoint if it is enabled
    in the configuration.
    '''
    if not config_t(bool, 'metrics', 'enabled'):
        return

    start_http_server(
        port=config_t(int, 'metrics', 'port') or 8000,
        addr=config_t(str, 'metrics', 'addr') or '127.0.0.1',
        certfile=config_t(str, 'metrics', 'certfile'),
        keyfile=config_t(str, 'metrics', 'keyfile'))
