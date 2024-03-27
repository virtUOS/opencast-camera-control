# Created by pyp2rpm-3.3.8
%global pypi_name confygure
%global pypi_version 0.1.0

Name:           python-%{pypi_name}
Version:        %{pypi_version}
Release:        1%{?dist}
Summary:        A simple YAML based configuration library for Python

License:        MIT
URL:            None
Source0:        %{pypi_source}
BuildArch:      noarch

BuildRequires:  python3-devel
BuildRequires:  python3dist(setuptools)

%description
A simple YAML based configuration library for Python

%package -n     python3-%{pypi_name}
Summary:        %{summary}
%{?python_provide:%python_provide python3-%{pypi_name}}

Requires:       python3dist(pyyaml)
%description -n python3-%{pypi_name}
A simple YAML based configuration library for Python


%prep
%autosetup -n %{pypi_name}-%{pypi_version}
# Remove bundled egg-info
rm -rf %{pypi_name}.egg-info
# Patch setup.py
# This is a workaround for the Python toolchain in EL9 not supporting the new pyproject.toml
echo 'from setuptools import setup' > setup.py
echo "setup(name = 'confygure', $(grep version pyproject.toml), packages=['confygure'])" >> setup.py

%build
%py3_build

%install
%py3_install

%files -n python3-%{pypi_name}
%license LICENSE
%doc README.md
%{python3_sitelib}/%{pypi_name}
%{python3_sitelib}/%{pypi_name}-%{pypi_version}-py%{python3_version}.egg-info

%changelog
* Tue Mar 26 2024 Lars Kiesow <lkiesow@uos.de> - 0.1.0-1
- Initial package.
