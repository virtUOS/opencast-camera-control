# Opencast Camera Control

Control PTZ camera to move to certain presets when starting a scheduled recording.

## Getting started

```
❯ pip install -r requirements.txt
❯ python -m occameracontrol
```

## Metrics

You can enable an OpenMetrics endpoint in the configuration. This can give you
insight into current camera positions and will report occurring errors.

The resulting metrics data will look like this:

```
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
