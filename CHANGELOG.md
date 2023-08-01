# Changelog 
#### for the documentation of earlier releases see docstring inside [mb_client_v2.py](https://github.com/ccatp/MODBUS/blob/05c387611b738852c8d53d44a64b80398edb9cda/modbusClient/src/mb_client_v2.py)
## unreleased (2023-mm-dd)
### Added
### Changed
### Fixed
### Deprecated
### Removed
### Security
## 3.5.1 (2023-08-01)
### Added
### Changed
### Fixed
- feature "isTag" is passed to output JSON only if provided in configFile. 
## 3.5.0 (2023-07-31)
### Added
- "min" and "max" features are passed on to the output for input and holding 
registers applicable to int and float parameters. Furthermore, when writing 
a parameter to a holding register throws exception if its value exceeds 
one of the limits.
### Changed
### Fixed
## 3.4.0 (2023-07-28)
### Added
- Rest API: method to list all host names of present device class 
### Changed
- IP address is host now. 
- pymodbus v3.4.1 deployed
### Fixed
### Removed
- no checks on IP or host name
## 3.3.1 (2023-07-27)
### Added
- changelog.md
### Changed
### Fixed
- catch exception when trying to write inappropriate value to holding 
register and issue in output message
## 3.3.0 (2023-07-25)
### Added
### Changed
- deploys pymodbus v3.4.0
### Fixed
## 3.2.0 (2023-07-23)
### Added
- updated registers after calling "write" method issued
in either result JSON or exception message
### Changed
### Fixed     
- holding register - string not right-stripped anymore