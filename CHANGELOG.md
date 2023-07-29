# Changelog 
#### for the documentation of earlier releases see docstring inside [mb_client_v2.py](https://github.com/ccatp/MODBUS/blob/05c387611b738852c8d53d44a64b80398edb9cda/modbusClient/src/mb_client_v2.py)
## unreleased (2023-mm-dd)
### Added
- for int and float parameters of holding register 
check if their value exceed values of attributes "min" or "max" 
if provided and throw exception. 
### Changed
### Fixed
### Deprecated
### Removed
### Security
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