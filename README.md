# MODBUS

## MODBUS READER

A universal MODBUS interface, where the mapping to coil,
discrete input, input registers, and holding registers is entirely defined
by a
[JSON](https://github.com/ccatp/MODBUS/blob/master/src/mb_client_mapping_default.json)
file, with no modification to the coding required whatsoever. This JSON file
comprises keys pointing to the register(s) and nested keys, such as

1) "parameter" (mandatory and unique over all register classes). 
2) "function" (mandatory for input and holding registers).
3) "description" (optional).
4) "map" (optional). 
5) "muliplier" (optional for input and holding registers of datatype integer).
6) "offset" (optional for input and holding registers of datatype integer).

The latter two, when provided, will not be passed on to the output, though.
They are parsed, such that the register's value is multiplied by "multiplier" 
and "offset" is added. A map is to be provided in case a value needs to match 
an entry from a list provided. The corresponding field value is passed on to 
the output as description that superseeds the input "description". A map might 
contain entries matching bits of the leading or trailing byte.
Moreover, "value" and "datatype" are
reserved keywords, since they will be generated in the output dictionary.
Additional dictionary key/value pairs may be provided in the client registry
mapping, which are merely passed on to the output. To maintain consistancy over
the various modbus clients, we urge selecting same denominators for further
keys, such as "defaultvalue", "unit", "min", or "max".

The register keys are in the formate: e.g. "30011", "30011/1" or "30011/2" for
the leading and trailing byte of the (16 bit) register, respectively,
furthermore, "30011/30012" or "30011/30014" for 32 or 64 bit register addresses.
A function needs to be defined for input and holding registers that translates
the 8, 16, 32, or 64 bits into appropriate values. This function is in the form,
e.g. "decode_32bit_uint" (see below for a selection):

| Function | Value | Avro |
|----------|-------|------|
| 8 bits of 1<sup>st</sup>/2<sup>nd</sup> byte | decode_bits | boolean |
| string of variable length | decode_string | string| 
| 8 int of 1<sup>st</sup>/2<sup>nd</sup> byte | decode_8bit_int | int |
| 8 uint of 1<sup>st</sup>/2<sup>nd</sup> byte | decode_8bit_uint | int |
| 16 int|  decode_16bit_int|  int |
| 16 uint|  decode_16bit_uint|  int |
| 32 int|   decode_32bit_int|  int |
| 32 uint|   decode_32bit_uint|  int |
| 16 float|   decode_16bit_float| float |
| 32 float|   decode_32bit_float| float |
| 64 int|   decode_64bit_int| long |
| 64 uint|   decode_64bit_uint| long | 
| 64 float|   decode_64bit_float | double |

If a map is defined, the description is chosen according to round(value). Gaps
between keys are permitted. A check on the uniqueness of "parameter" is 
performed. The JSON format for the mapping is to be defined in
the following formate, e.g.:

```JSON
{
  "10000": {
    "parameter": "UnitOn",
    "description": "Unit On status: TRUE = Unit ON"
  },
  "10001": {
    "parameter": "Unit_Alarm"
  },
  "30001": {
    "function": "decode_16bit_uint",
    "parameter": "Operating State",
    "map": {
      "0": "Idling ‐ ready to start",
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
  "30011/30012": {
    "function": "decode_32bit_float",
    "parameter": "Oil Temp",
    "description": "unit is provided here...",
    "unit": "e.g. Fahrenheit"
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
    "default": "test7",
    "map": {
      "0b10000000": "test7"
    }
  },
  "30034/2": {
    "function": "decode_bits",
    "parameter": "TEST2",
    "map": {
      "0b00000001": "test0",
      "0b00000010": "test1",
      "0b00000100": "test2",
      "0b00001000": "test3",
      "0b00010000": "test4",
      "0b00100000": "test5",
      "0b01000000": "test6",
      "0b10000000": "test7"
    }
  },
  "40009": {
    "parameter": "Water_Setpoint.SP_r",
    "function": "decode_16bit_int",
    "multiplier": 0.1,
    "offset": -273,
    "description": "Setpoint Water",
    "unit": "DegreesCelsius",
    "max": "Water_Setpoint.max_r",
    "min": "Water_Setpoint.min_r",
    "defaultvalue": 24.0
  }
}
```
Before decoding the modbus payloads, please consider that there is some 
confusion about Little-Endian vs. Big-Endian Word Order. The current modbus 
client allows the endiannesses of the byteorder (the Byte order of each word)
and the wordorder (the endianess of the word, when wordcount is >= 2) to be 
adjusted (see
[Parameters](https://github.com/ccatp/MODBUS/blob/master/src/mb_client_config_default.json)):

    ">" = Endian.Big 
    "<" = Endian.Little

The result for the housekeeping (Kafka consumer) is a list of dictionaries, 
where most of its content is passed on from the client-mapping JSON to the 
output.

Not implemented yet:
* decoder.bit_chunks()

## MODBUS WRITER

The reader - in its final version - will be invoked through a Flask Rest-API.
For the time being it accepts - as input - a dictionary with 
{"parameter": "value"} pairs, where the parameters need to match their 
counterparts as defined in
[JSON](https://github.com/ccatp/MODBUS/blob/master/src/mb_client_mapping_default.json).

Basic idea: write only to coil and holding registers defined in the 
appropriate reader mapping.

Modbus server connection parameters are defined in the client config 
parameter file, as well.

Caveat: 

* Owing to Python's pymodbus module, registers can solely be updated on the
  whole, which applies for strings, bits and 8bit-integers in the leading and
  trailing bytes. Hence, a leading or 
  trailing byte being updated, will result in "0x00" (empty) of the 
  respective other.

* Endianness of byteorder. 

## MODBUS REST API

Run the MODBUS Rest API with modbus_client.py and modbus_reader.py 
present in same directory, the same applies for the client_config.json and 
client_mapping.json files.

    python3 mb_client_rest_api.py

Invoke the Writer (e.g. from nanten):
    
    curl 10.10.1.9:5000/<device name>/write -X PUT -H "Content-Type: application/json" -d '{"MAX_COOLING": [false, false, false, false, false, false, false, false, false, false, false, false, false, false, false, true]}' 

Invoke the Reader:

    curl 10.10.1.9:5000/<device name>/read 

where `<device name>` denotes the extention for each device (equipment) or server.

## Content

The current repository comprises a 
* MODBUS server simulator (the python code is extracted from 
https://hub.docker.com/r/oitc/modbus-server) with its 
[config](https://github.com/ccatp/MODBUS/blob/master/src/modbus_server.json) 
file.
* MODBUS 
[Reader](https://github.com/ccatp/MODBUS/blob/master/src/mb_client_reader.py) 
* MODBUS
[Writer](https://github.com/ccatp/MODBUS/blob/master/src/mb_client_writer.py)
* MDOBUS 
[REST API](https://github.com/ccatp/MODBUS/blob/master/src/mb_client_rest_api.py)
comprising a Reader and Writer (see above). For Reader and Writer the MODBUS 
server connection details are defined in
mb_client_config_`<device name>`.json, whereas registry information is provided in 
mb_client_mapping_`<device name>`.json


Contact: Ralf Antonius Timmermann, AIfA, University Bonn, email: 
rtimmermann@astro.uni-bonn.de