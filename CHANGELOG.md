# Changelog 
#### for the documentation of earlier releases see docstring inside *mb_client_xxx.py*
## unreleased (2023-mm-dd)
### Added
### Changed
### Fixed
### Deprecated
### Removed
### Security
## 5.0.1 (2023-08-21)
### Added
- timeout_connect option for async client
### Changed
### Fixed
### Deprecated
- async RestAPI: locking mechanism disabled 
## 5.0.0 (2023-08-10)
### Added
- Asynchronous MODBUS client
### Changed
### Fixed
## 4.2.0 (2023-08-07)
### Added
- additional integrity checks on features
### Changed
### Fixed
### Deprecated
### Removed
### Security
## 4.1.0 (2023-08-03)
### Added
- throw exception if feature name is not provided 
in [README.md](https://github.com/ccatp/MODBUS/blob/913e3f9ae53a86cc9def6d47ff442d4c4a991fa7/README.md)
### Changed
- features in dict are sorted for output
- code cleansing
### Fixed
- for coil and discrete input registers only features not listed 
in FEATURE_EXCLUDE_SET are passed on to output
## 4.0.0 (2023-08-02)
### Added
### Changed
- description not superseded by map any longer. 
- if map provided for int/float or one bit: provide new feature "value_alt" in output with the mapped value
- if map provided for many bits: provide new feature "parameter_alt" in output
### Fixed
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