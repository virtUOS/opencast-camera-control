# Opencast Camera Control

Enable the EPEL repository:

```
dnf install epel-release
```

Then install the RPM repository by adding a file `/etc/yum.repos.d/opencast-camera-control.repo`:

```
[opencast-camera-control]
name = Opencast camera control el$releasever repository
baseurl  = https://raw.githubusercontent.com/virtUOS/opencast-camera-control/rpm-el$releasever/
enabled  = 1
gpgcheck = 1
gpgkey = https://raw.githubusercontent.com/virtUOS/opencast-camera-control/rpm-el$releasever/opencast-camera-control.key
```
