# Opencast Camera Control

Control PTZ camera to move to certain presets when starting a scheduled recording.

This tool communicated with [Opencast](https://opencast.org) to get scheduled
evens for a list of configured capture agents. When an event starts, cameras
configured to be part of the agent's setup are then automatically turned to an
active position specified by a configurable camera preset. When the event ends,
the camera is turned back to a neutral position.

This allows you, for example, to automatically turn cameras to the wall when no
recordings are active.

https://github.com/virtUOS/opencast-camera-control/assets/1008395/a8e37229-f760-4a54-82b2-1a555c960736

<small><i>(Camera moves when a one minute scheduled recording starts and returns to point at the wall at the end)</i></small>

## Getting started

```
❯ pip install -r requirements.txt
❯ python -m occameracontrol
```


## Configuration

Take a look at the [camera-control.yml](camera-control.yml) configuration file.
All available options are documented in there.

You can provide custom configuration files using the `--config` option:

```
❯ python -m occameracontrol --config custom-config.yml
```

## Opencast User

To improve security, you can limit the access rights for the Opencast user by
creating a user which has only the role `ROLE_CAPTURE_AGENT` assigned.

## Metrics

You can enable an OpenMetrics endpoint in the configuration. This can give you
insight into current camera positions and will report occurring errors.

The resulting metrics data will look like this:

```properties
# HELP request_errors_total Number of errors related to HTTP requests
# TYPE request_errors_total counter
request_errors_total{ressource="http://camera-3-panasonic.example.com",type="ConnectionError"} 77.0
request_errors_total{ressource="http://camera-panasonic.example.com",type="ReadTimeout"} 12.0
# HELP request_errors_created Number of errors related to HTTP requests
# TYPE request_errors_created gauge
request_errors_created{ressource="http://camera-3-panasonic.example.com",type="ConnectionError"} 1.707571882114209e+09
request_errors_created{ressource="http://camera-panasonic.example.com",type="ReadTimeout"} 1.7075718871156712e+09
# HELP agent_calendar_update_total Nuber of calendar update
# TYPE agent_calendar_update_total gauge
agent_calendar_update_total{agent="test_agent"} 4.0
# HELP agent_calendar_update_time Time of the last calendar update
# TYPE agent_calendar_update_time gauge
agent_calendar_update_time{agent="test_agent"} 1.707571943100096e+09
# HELP camera_position Last position (preset number) a camera moved to
# TYPE camera_position gauge
camera_position{camera="http://camera-2-panasonic.example.com"} 10.0
```

## Docker

We also provide a container image.
A simple docker compose example would look like this

```yaml
---
version: '3'
services:
  app:
    image: ghcr.io/virtuos/opencast-camera-control:main
    ports:
      - '8000:8000'
    volumes:
      - './your_config.yml:/etc/camera-control.yml'
```
