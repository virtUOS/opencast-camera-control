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

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from flask import Flask, Response
from flask_basicauth import BasicAuth

logger = logging.getLogger(__name__)

app = Flask(__name__)
basic_auth = BasicAuth(app)


@app.route('/control/<string:status>/<string:req_camera_url>')
@basic_auth.required
def activate_camera(status, req_camera_url):
    """ Endpoint for switching between manual and automatic camera control.
        The desired camera is identified by the passed req_camera_url.
    """
    if status == "manual":
        logger.info('Camera with URL "[%s]" will be controlled manually and ' +
                    'therefore it\'s position won\'t be updated automatically',
                    req_camera_url)
    elif status == "automatic":
        logger.info('Camera with URL "[%s]" will switch to automatic ' +
                    'controlling. The camera\'s position will be ' +
                    'adjusted to the corresponding agent\'s status ' +
                    'automatically.', req_camera_url)
    else:
        return 'ERROR<br/>Given status %s is invalid.', status

    # Get rid of http or https prefixes to ensure reliable comparability
    sanitized_camera_url = (req_camera_url.replace('http://', '')
                            .replace('https://', ''))
    cameras = app.config["cameras"]
    for camera in cameras:
        camera_url = (getattr(camera, 'url').replace('http://', '')
                      .replace('https://', ''))
        if sanitized_camera_url == camera_url:
            setattr(camera, 'control', status)
            # Resets the current position of the camera
            setattr(camera, 'position', -1)
            return (
                f"Successfully set camera with url '{camera_url} "
                f"to control status <b>'{status}'</b>."
            )
    logger.info(f"Camera with url '{req_camera_url}' could not be found.")
    return f"ERROR<br/>Camera with url '{req_camera_url}' could not be found."


@app.route('/control_status/<string:req_camera_url>')
@basic_auth.required
def view_current_camera_control_status(req_camera_url):
    """ Endpoint for requesting the current control status
        (manual or automatic) for a camera.
        The desired camera is identified by the passed camera url.
    """
    # Get rid of http or https prefixes to ensure reliable comparability
    sanitized_camera_url = (req_camera_url.replace('http://', '')
                            .replace('https://', ''))
    cameras = app.config["cameras"]
    for camera in cameras:
        camera_url = (getattr(camera, 'url').replace('http://', '')
                      .replace('https://', ''))
        if sanitized_camera_url == camera_url:
            return (
                f"STATUS<br/>The control status of the camera "
                f"with url '{req_camera_url}' is "
                f"<b>{getattr(camera, 'control')}</b>"
            )
    logger.info(f"Camera with url '{req_camera_url}' could not be found.")
    return f"ERROR</br>Camera with url '{req_camera_url}' could not be found."


# expose camera control metrics
@app.route('/metrics')
def metrics():
    """ Endpoint for exposing the camera control metrics.
    """
    return Response(generate_latest(), content_type=CONTENT_TYPE_LATEST)


def start_camera_control_server(cameras, auth: tuple[str, str]):
    """Start the flask server for managing the camera control
    """
    logger.info('Starting camera control server')
    # start flask app
    # ToDo get host and port from config, default 127.0.0.1:8000
    app.config['cameras'] = cameras
    app.config['BASIC_AUTH_USERNAME'] = auth[0]
    app.config['BASIC_AUTH_PASSWORD'] = auth[1]
    app.run(host='127.0.0.1', port=8080)
