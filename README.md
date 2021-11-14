# MODBUS

A simple universal MODBUS interface, where the mapping to coil,
discrete input, input registers, and holding registers is entirely defined
though a
[JSON](https://github.com/ccatp/MODBUS/blob/master/src/client_mapping.json)
file, with no modification to the coding required whatsoever. This JSON file
comprises a key pointing to the register(s) and several nested keys, such as

1) "function" (mandatory only for input and holding registers).
2) "parameter" (mandatory and unique over all register classes). 
3) "description" (optional).
4) "map" (optional), in the case a value needs to match an entry from a list 
   provided. This field value is then parsed through as description. A map 
   might contain one entry that matches one bit out of the leading or 
   trailing byte.
5) "muliplier" (optional only for input and holding registers).
6) "offset" (optional only for input and holding registers).

Furthermore, "value" and "datatype" are also reserved keys, since they
will be generated in the output dictionary. Additional dictionary key/value
pairs may be provided in the client registry mapping, which are just parsed 
to the output. 
To maintain consistancy over the various modbus clients, we urge
selecting same denominators for further keys, such as "defaultvalue", "unit", 
"min", or "max".

The register key are in the formate: e.g. "30011", "30011/1" or "30011/2" for
the leading and trailing byte of the (16 bit) register, respectively, and
furthermore, "30011/30012" or "30011/30014" for 32 or 64 bit register addresses.
A function needs to be defined for input and holding registers that translates
the 8, 16, 32, or 64 bits into appropriate values. This function is in the form,
e.g. "decode_32bit_uint" (see below for a selection):

| Function | Value | Avro |
|----------|-------|------|
| 8 bits of 1<sup>st</sup>/2<sup>nd</sup> byte | decode_bits | boolean |
| 8 bits of 1<sup>st</sup>/2<sup>nd</sup> byte = 1 character | decode_string | string| 
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
The result for the housekeeping (Kafka consumer) is a list of dictionaries, 
where most of its content is parsed through from the register mapping.

The current repository comprises a 
* MODBUS server simulator (the python code is extracted from 
https://hub.docker.com/r/oitc/modbus-server) with its 
[config](https://github.com/ccatp/MODBUS/blob/master/src/modbus_server.json) 
file.
* MODBUS [client](https://github.com/ccatp/MODBUS/blob/master/src/modbus_client.py), 
where the MODBUS server connection details, etc. are defined in
[Parameters](https://github.com/ccatp/MODBUS/blob/master/src/client_config.json).

#### Caveat:
not implemented yet:
* decoder.bit_chunks() - classmethod
* strings of length>1
* for coil and discrete input only the first 2000 bits are read in (hardcoded).

Contact: Ralf Antonius Timmermann, AIfA, University Bonn, email: 
rtimmermann@astro.uni-bonn.de