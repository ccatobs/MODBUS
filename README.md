# MODBUS
Development of a general MODBUS interface, where the mappings of
coil, discrete input, input register, and holding register are entirely
defined in 
[JSON](https://github.com/ccatp/MODBUS/blob/master/src/client_mapping.json). 
In case of gaps (for input and holding registers) 
between the defined registers, the appropriate number of bytes is calculated 
and skipped accordingly.

The JSON format is to be defined in the following formate, e.g.:
```
{
  "10000": {
    "parameter": "UnitOn",                      # parameter mandatory
    "desc": "Unit On status: TRUE = Unit ON"    # desc optional
  },
  "10001": {
    "parameter": "Unit_Alarm"
  },
  
  ...

  "30001": {
    "function": "decode_16bit_uint",    # function mandatory for input and holding
    "parameter": "Operating State",
    "map": {
      "0": "Idling ‐ ready to start",   # if map provided, desc = map element
      "2": "Starting",
      "3": "Running",
      "5": "Stopping",
      "6": "Error Lockout",
      "7": "Error",
      "8": "Helium Cool Down",
      "9": "Power related Error",
      "15": "Recovered from Error"
    }
  },
  "30002": {
    "function": "decode_16bit_uint",
    "parameter": "Compressor Running",
    "map": {
      "0": "Off",
      "1": "On"
    }
  },
  "30003/30004": {
    "function": "decode_32bit_float",
    "parameter": "Warning State",
    "map": {
      "0": "No warnings",
      "-1": "Coolant IN running High",
      "-2": "Coolant IN running Low",
      "-4": "Coolant OUT running High",
      "-8": "Coolant OUT running Low",
      "-16": "Oil running High",
      "-32": "Oil running Low",
      "-64": "Helium running High",
      "-128": "Helium running Low",
      "-256": "Low Pressure running High",
      "-512": "Low Pressure running Low",
      "-1024": "High Pressure running High",
      "-2048": "High Pressure running Low",
      "-4096": "Delta Pressure running High",
      "-8192": "Delta Pressure running Low",
      "-131072": "Static Pressure running High",
      "-262144": "Static Pressure running Low",
      "-524288": "Cold head motor Stall"
    }
  },
  
  ...                    # possible gaps between keys are automatically skipped

  "30031": {
    "function": "decode_16bit_uint",
    "parameter": "Panel Serial Number",
    "desc": "This is supposed to be the Panel Serial Number"
  },
  ...
  "30033": {
    "function": "decode_16bit_uint",
    "parameter": "Software Rev"
  },
  "30034/2": {
    "function": "decode_bits",
    "parameter": "TEST",
    "map": {
      "0b00000001": "test0",    # for decode bits mapping binary string format 
      "0b00000010": "test1",
      "0b00000100": "test2",
      "0b00001000": "test3",
      "0b00010000": "test4",
      "0b00100000": "test5",
      "0b01000000": "test6",
      "0b10000000": "test7"
    }
  }
}
```
A check on the uniqueness of "parameter" is performed. Keys are to be in the 
format: 3xxxx, 3xxxx/1 or 3xxxx/2 for the leading/trailing byte or 3xxxx/3xxxx 
for 32/64 bit spanning registers. So far the JSON output is display on stdout.

Caveat:
* decoder.decode_string(size=1) - Decodes a string from the buffer
* decoder.bit_chunks() - classmethod

not considered yet.

This repository comprises a 
* MODBUSserver simulator (the python code is extracted from 
https://hub.docker.com/r/oitc/modbus-server)
* MODBUS [client](https://github.com/ccatp/MODBUS/blob/master/src/modbus_client.py).
[Parameters](https://github.com/ccatp/MODBUS/blob/master/src/client_config.json) 
comrprise MODBUS server details, etc.