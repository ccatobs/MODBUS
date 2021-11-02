# MODBUS

A simple universal MODBUS interface, where the mapping of the registers to coil,
discrete input, input registers, and holding registers is entirely defined
though a
[JSON](https://github.com/ccatp/MODBUS/blob/master/src/client_mapping.json)
file, with no modification to the coding required whatsoever. This JSON file
comprises a key pointing to the register(s) and several nested keys, such as

1) "parameter" (mandatory and unique over all register classes), 
2) "description" (optional) or
3) "map" (optional), in the case a value needs to match an entry from a list 
   provided. This field value is then parsed through as description. A map 
   might contain only one entry that matches one bit out of the leading or 
   trailing byte.

Additional dictionary key/value pairs may be provided in the
client registry mapping, which are just parsed. In order to maintain 
consistancy amongst the various modbus clients, we suggest to select 
same denominators for further keys, such as "default value", "unit", "min", 
and "max".

The register key has to be in
the formate: e.g. "30011", "30011/1" or "30011/2" for the leading and trailing 
byte of the (16 bit) register, respectively, and furthermore,
"30011/30012" or "30011/30014" for 32 or 64 bit register addresses. In such case
a function needs to be defined for input and holding registers that 
translates the 8, 16, 32, or 64 bits into appropriate values. This function 
is in the form, e.g. "decode_32bit_uint" (see below for a selection): 


| Function | Value |
|----------|-------|
| 8 bits of 1<sup>st</sup>/2<sup>nd</sup> byte | decode_bits |
| 8 int | decode_8bit_int |
| 8 uint | decode_8bit_uint |
| 16 int|  decode_16bit_int| 
| 16 uint|  decode_16bit_uint| 
| 32 int|   decode_32bit_int| 
| 32 uint|   decode_32bit_uint| 
| 16 float|   decode_16bit_float| 
| 32 float|   decode_32bit_float| 
| 64 int|   decode_64bit_int| 
| 64 uint|   decode_64bit_uint| 
| 64 float|   decode_64bit_float |

If a map is defined, the description is chosen according to round(value). In
case of a gap between keys, byte skipping is calculated and performed
automatically. A check on the uniqueness of "parameter" is performed. The JSON
format for the mapping is to be defined in the following formate, e.g.:

```JSON
{
  "10000": {
    "parameter": "UnitOn",                            // parameter mandatory
    "description": "Unit On status: TRUE = Unit ON"   // description optional
  },
  "10001": {
    "parameter": "Unit_Alarm"
  }, 
  "30001": {
    "function": "decode_16bit_uint", // function mandatory for input and holding register
    "parameter": "Operating State",
    "map": {
      "0": "Idling ‐ ready to start", // if map provided, desc = map element
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
  },                     // possible gaps between keys are automatically skipped
  "30011/30012": {
    "function": "decode_32bit_float",
    "parameter": "Oil Temp",
    "description": "unit is provided here...",
    "unit": "e.g. Fahrenheit"   // unit optional
  },
  "30031": {
    "function": "decode_16bit_uint",
    "parameter": "Panel Serial Number",
    "description": "This is supposed to be the Panel Serial Number"
  },
  "30033": {
    "function": "decode_16bit_uint",
    "parameter": "Software Rev"
  },
  "30034/1": {
    "function": "decode_bits",
    "parameter": "TEST1", 
    "default": "ZERO",
    "map": {
      "0b10000000": "test7"   // becomes description
    },
  "30034/2": {
    "function": "decode_bits",
    "parameter": "TEST2",
    "map": {
      "0b00000001": "test0",    // for decode_bits mapping binary string format 
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

This repository comprises a 
* MODBUS server simulator (the python code is extracted from 
https://hub.docker.com/r/oitc/modbus-server) with its 
[config](https://github.com/ccatp/MODBUS/blob/master/src/modbus_server.json) 
file.
* MODBUS [client](https://github.com/ccatp/MODBUS/blob/master/src/modbus_client.py), 
where the MODBUS server connection details, etc. are defined in
[Parameters](https://github.com/ccatp/MODBUS/blob/master/src/client_config.json).

For the time being the output is a list of dictionaries:

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
not implemented yet:
* decoder.decode_string(size=1) - Decodes a string from the buffer
* decoder.bit_chunks() - classmethod
* for coil and discrete input only the first 2000 bits are read in (hardcoded).

Contact: Ralf Antonius Timmermann, AIfA, University Bonn, email: 
rtimmermann@astro.uni-bonn.de