# MODBUS

A simple universal MODBUS interface, where the mapping of the registers to coil,
discrete input, input registers, and holding registers is entirely defined
though a
[JSON](https://github.com/ccatp/MODBUS/blob/master/src/client_mapping.json)
file, with no modification to the python code required. This JSON file comprises
a key describing the register, a corresponding parameter (mandatory and unique
over all register classes), a unit and a description (optional). The key is in
the formate: e.g. 30011, 30011/1 or 30011/2 for the leading and trailing byte,
30011/30012 or 30011/30014 for 32 or 64 bit register addresses. For input and
holding registers a function needs to be defined that translated the 8, 16, 32,
or 64 bits into appropriate values, such as

```python
{
('bits', decoder.decode_bits()),
('8int', decoder.decode_8bit_int()),
('8uint', decoder.decode_8bit_uint()),
('16int', decoder.decode_16bit_int()),
('16uint', decoder.decode_16bit_uint()),
('32int', decoder.decode_32bit_int()),
('32uint', decoder.decode_32bit_uint()),
('16float', decoder.decode_16bit_float()),
('32float', decoder.decode_32bit_float()),
('64int', decoder.decode_64bit_int()),
('64uint', decoder.decode_64bit_uint()),
('64float', decoder.decode_64bit_float())
}
```

Function is in the form, e.g. "decode_32bit_uint". If a map is defined, then 
the description is chosen according to the round(value). In case of a gap 
between keys byte skipping is calculated automatically. The JSON format is to 
be defined in the following formate, e.g.:

```JSON
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
  
  ...
  
  "30011/30012": {
    "function": "decode_32bit_float",
    "parameter": "Oil Temp",
    "desc": "unit is provided here..."
    "unit": "e.g. Fahrenheit"
  
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

A check on the uniqueness of "parameter" is performed. So far the JSON output 
is display on stdout.

This repository comprises a 
* MODBUS server simulator (the python code is extracted from 
https://hub.docker.com/r/oitc/modbus-server) with its 
[config](https://github.com/ccatp/MODBUS/blob/master/src/modbus_server.json) 
file.
* MODBUS [client](https://github.com/ccatp/MODBUS/blob/master/src/modbus_client.py), 
where the MODBUS server connection details, etc are defined in
[Parameters](https://github.com/ccatp/MODBUS/blob/master/src/client_config.json).

For the time being the output looks something like this (your input needed): 

```JSON
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
        "value": 80.6500015258789
    },
    {
        "parameter": "Oil Temp",
        "value": 98.0,
        "unit": "Fahrenheit"
    },
    {
        "parameter": "Helium Temp",
        "value": 124.0
    },
    {
        "parameter": "Low Pressure",
        "value": 121.0
    },
    {
        "parameter": "Low Pressure Average",
        "value": 121.0
    },
    {
        "parameter": "High Pressure",
        "value": 315.0
    },
    {
        "parameter": "High Pressure Average",
        "value": 315.0
    },
    {
        "parameter": "Delta Pressure Average",
        "value": 200.0
    },
    {
        "parameter": "Motor Current",
        "value": 1.899999976158142
    },
    {
        "parameter": "Hours Of Operation",
        "value": 8333.0
    },
    {
        "parameter": "Pressure Scale",
        "value": 0,
        "description": "PSI"
    },
    {
        "parameter": "Temperature Scale",
        "value": 0,
        "description": "Fahrenheit"
    },
    {
        "parameter": "Panel Serial Number",
        "value": 4711
    },
    {
        "parameter": "Model Major Number",
        "value": 40
    },
    {
        "parameter": "Model Minor Number",
        "value": 156
    },
    {
        "parameter": "Software Rev",
        "value": 17,
        "description": "upgrade frequently!"
    }
]
```

#### Caveat:
not implemented yet
* decoder.decode_string(size=1) - Decodes a string from the buffer
* decoder.bit_chunks() - classmethod

