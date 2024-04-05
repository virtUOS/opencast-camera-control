# Created by pyp2rpm-3.3.8
%global pypi_name opencast-camera-control
%global pypi_version %{_camera_control_version}

%define uid   opencastcamera
%define gid   opencastcamera

Name:           %{pypi_name}
Version:        %{pypi_version}
Release:        1%{?dist}
Summary:        Automated Camera Control for Opencast

License:        GPLv3+

URL:            None
Source0:        https://github.com/virtUOS/%{name}/archive/refs/tags/%{version}.tar.gz
Source1:        https://raw.githubusercontent.com/virtUOS/%{name}/%{version}/camera-control.yml
Source2:        opencast-camera-control.service
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3dist(setuptools)

Requires:       python3dist(confygure) >= 0.1
Requires:       python3dist(prometheus-client)
Requires:       python3dist(python-dateutil)
Requires:       python3dist(requests)
Requires:       python3dist(setuptools)

BuildRequires:     systemd
Requires(post):    systemd
Requires(preun):   systemd
Requires(postun):  systemd

%description
Control PTZ camera to move to certain presets when
starting a scheduled recording.

%{?python_provide:%python_provide python3-%{pypi_name}}


%prep
%autosetup -n %{pypi_name}-%{pypi_version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info
# Patch setup.py
# This is a workaround for the Python toolchain in EL9 not supporting the new pyproject.toml
echo 'from setuptools import setup' > setup.py
echo "setup(name = 'opencast-camera-control', $(grep version pyproject.toml), packages=['occameracontrol']," >> setup.py
echo "  entry_points={'console_scripts':['opencast-camera-control = occameracontrol.__main__:main' ]})" >> setup.py

%build
%py3_build

%install
%py3_install

# Install configuration
install -m 0644 -p -D %{SOURCE1} %{buildroot}%{_sysconfdir}/camera-control.yml

# Install Systemd unit file
install -m 0644 -p -D %{SOURCE2} %{buildroot}%{_unitdir}/%{name}.service


%pre
# Create user and group if nonexistent
if [ ! $(getent group %{gid}) ]; then
	groupadd -r %{gid} > /dev/null 2>&1 || :
fi
if [ ! $(getent passwd %{uid}) ]; then
	useradd -M -r -g %{gid} %{uid} > /dev/null 2>&1 || :
fi


%post
%systemd_post %{name}.service


%preun
%systemd_preun %{name}.service


%postun
%systemd_postun_with_restart %{name}.service


%files
%license LICENSE
%doc README.md
%{_bindir}/opencast-camera-control
%{_unitdir}/%{name}.service
%{python3_sitelib}/occameracontrol
%{python3_sitelib}/opencast_camera_control-%{pypi_version}-py%{python3_version}.egg-info
%config(noreplace) %{_sysconfdir}/camera-control.yml

%changelog
* Tue Mar 26 2024 Lars Kiesow <lkiesow@uos.de> - 0.1.0-1
- Initial package.
