# MODBUS
A simple universal MODBUS interface, where the 
mapping of the registers to the coil, discrete
input, input registers, and holding registers is entirely defined though a
[JSON](https://github.com/ccatp/MODBUS/blob/master/src/client_mapping.json) 
file, no modification to the python coding is required. This JSON file
comprises a key describing the register, a parameter (mandatory and unique over
all four register classes), a unit and description (optional) per value.
The key is in the formate: e.g. 30011, 30011/1 or 30011/2 for the leading and
trailing byte, or 30011/30012 for 32 or 64 bit register addresses. For input
and holding registers a function needs to be defined that translated the
8, 16, 32, or 64 bits into appropriate values, such as
```
            ('bits', decoder.decode_bits()),
            ('8int', decoder.decode_8bit_int()),
            ('8uint', decoder.decode_8bit_uint()),
            ('16int', decoder.decode_16bit_int()),
            ('16uint', decoder.decode_16bit_uint()),
            ('32int', decoder.decode_32bit_int()),
            ('32uint', decoder.decode_32bit_uint()),
            ('16float', decoder.decode_16bit_float()),
            ('16float2', decoder.decode_16bit_float()),
            ('32float', decoder.decode_32bit_float()),
            ('32float2', decoder.decode_32bit_float()),
            ('64int', decoder.decode_64bit_int()),
            ('64uint', decoder.decode_64bit_uint()),
            ('ignore', decoder.skip_bytes(8)),
            ('64float', decoder.decode_64bit_float()),
            ('64float2', decoder.decode_64bit_float())
```
and so on. If a map is defined, then description is chosen according to the
round(value). In case of a gap between keys byte skipping is calculated
automatically. The JSON format is to be defined in the following formate, e.g.:
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

not implemented yet.

This repository comprises a 
* MODBUS server simulator (the python code is extracted from 
https://hub.docker.com/r/oitc/modbus-server) with its 
[config](https://github.com/ccatp/MODBUS/blob/master/src/modbus_server.json) 
file.
* MODBUS [client](https://github.com/ccatp/MODBUS/blob/master/src/modbus_client.py).
[Parameters](https://github.com/ccatp/MODBUS/blob/master/src/client_config.json) 
comprise MODBUS server connection details, etc.

For the time being the output looks something like this (your input needed):
```
[
    {
        "parameter": "Operating State",
        "value": 3,
        "description": "Running"
    },
    {
        "parameter": "Compressor Running",
        "value": 1,
        "description": "On"
    },
    {
        "parameter": "Warning State",
        "value": -16.0,
        "description": "Oil running High"
    },
    {
        "parameter": "Alarm State",
        "value": 0.0,
        "description": "No Errors"
    },
    {
        "parameter": "Coolant In Temp",
        "value": 60.0,
        "description": "additional info on the coolant"
    },
    {
        "parameter": "Coolant Out Temp",
        "value": 80.6500015258789,
        "description": null
    },
    {
        "parameter": "Pressure",
        "value": 0,
        "description": "PSI"
    },
    {
        "parameter": "Temperature",
        "value": 0,
        "description": "Fahrenheit"
    },
    {
        "parameter": "Panel Serial Number",
        "value": 4711,
        "description": "This is supposed to be the Panel Serial Number"
    },
    {
        "parameter": "Model Major Number",
        "value": 4,
        "description": "1100 Series"
    },
    {
        "parameter": "Model Minor Number",
        "value": 10,
        "description": "H5"
    },
    {
        "parameter": "Software Rev",
        "value": 17,
        "description": "upgrade frequently!"
    }
]
```