# A Universal MODBUS Client

## READER

A universal MODBUS interface, where the mapping of the parameters to coil,
discrete input, input and holding registers is entirely defined
by a JSON file, with no modification to the coding required whatsoever. 
The device class config file comprises a dictionary, where the key 
represents a MODBUS register, multiples or a single byte - major or minor - of it.
Note: a register key cannot be read out twice.
Its value comprises a dictionary of various features, namely

| Feature       | Description                                                                               | Applied To                          | Mandatory/<br/>Optional | Output         |
|---------------|-------------------------------------------------------------------------------------------|-------------------------------------|-------------------------|----------------|
| parameter     | unique parameter name to identify register space                                          | all                                 | mandatory               | yes            |
| function      | data type, see table below                                                                | all                                 | mandatory               | AVRO data type | 
| description   | parameter description                                                                     | all                                 | optional                | yes            |
| alias         | alternative identifier                                                                    | all                                 | optional                | yes            |
| unit          | units                                                                                     | int/float                           | optional                | yes            |
| defaultValue  | default value                                                                             | all but map of bits                 | optional                | yes            |
| map           | see below                                                                                 | all                                 | optional                | no             |
| isTag         | tag a parameter, for influxDB (boolean)                                                   | all but map of bits                 | optional                | yes            |
| min           | minimum of parameter value, write error if exceeded                                       | input & holding register, int/float | optional                | yes            |
| max           | maximum of parameter value, write error if exceeded                                       | input & holding register, int/float | optional                | yes            |
| multiplier    | multiply by register value: <br/> **<em>value = multiplier x register [+ offset] </em>**  | input & holding register, int       | optional                | no             |
| offset        | add offset to register value: <br/>**<em>value = [multiplier x] register + offset </em>** | input & holding register, int       | optional                | no             |

Features, such as "value" and "datatype" (AVRO naming conventions) are reserved for 
the output only. Same applies to "parameter_alt" and "value_alt". They are 
provided in case maps are used. Additional features may be provided in the 
client registry mapping, which will be merely passed on to the output. 

A map may be specified if a value needs to match an entry of a given list. In 
this case the corresponding field value of the map is passed on to the output 
as feature "value_alt". 
A map might also contain entries matching the 8 bits of the 
leading or trailing byte of a register. In that case the values of the 
individual bits are provided under the feature "parameter_alt".

Register keys are in the following formates: 
e.g. "30011" addressing the 12th register
of the input register class, "30011/1" or "30011/2" for
the leading and trailing byte of the 16 bit register, respectively.
Furthermore, "30011/30012" or "30011/30014" address 32 or 64 bit 
broad registers starting at the 12th register,
if registers are in zeroMode = True at the server's configuration.
A start/end register is to be provided for strings only, whereas the 
specification of an end register is not required for other data types.

[Note](https://en.wikipedia.org/wiki/Modbus): the number of registers per class 
de facto extends to 0xFFFF, such that 65536 registers could be utilized.



A function needs to be defined for input and holding registers that translates
the 8, 16, 32, or 64 bits into appropriate values. This function is in the form,
e.g. "decode_32bit_uint" (see below for a selection):

| Function                                     | Value              | Avro Data Type |
|----------------------------------------------|--------------------|----------------|
| 8 bits of 1<sup>st</sup>/2<sup>nd</sup> byte | decode_bits        | boolean        |
| string of variable length                    | decode_string      | string         | 
| 8 int of 1<sup>st</sup>/2<sup>nd</sup> byte  | decode_8bit_int    | int            |
| 8 uint of 1<sup>st</sup>/2<sup>nd</sup> byte | decode_8bit_uint   | int            |
| 16 int                                       | decode_16bit_int   | int            |
| 16 uint                                      | decode_16bit_uint  | int            |
| 32 int                                       | decode_32bit_int   | int            |
| 32 uint                                      | decode_32bit_uint  | int            |
| 16 float                                     | decode_16bit_float | float          |
| 32 float                                     | decode_32bit_float | float          |
| 64 int                                       | decode_64bit_int   | long           |
| 64 uint                                      | decode_64bit_uint  | long           | 
| 64 float                                     | decode_64bit_float | double         |

Gaps between registers are permitted. A check on the uniqueness of "parameter" is 
performed as well as validity checks on the JSON keys.

The JSON file for the client configuration and mapping of registers to parameters
is defined as follows. 

```JSON
{
  "endianness": {
    "byteorder": "<",
    "wordorder": ">"
  },
  "mapping": {
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
      },
      "isTag": true
    },
    "30002": {
      "function": "decode_16bit_uint",
      "parameter": "Compressor Running",
      "map": {
        "0": "Off",
        "1": "On"
      }
    },
    "30003": {
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
    "30011": {
      "function": "decode_32bit_float",
      "parameter": "Oil Temp",
      "description": "unit is provided here...",
      "unit": "e.g. Fahrenheit",
      "isTag": true
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
      "max": 50,
      "min": 10,
      "defaultvalue": 24.0
    }
  }
}
```
Note: "endianness" is optional, default is 
```JSON
{
    "byteorder": "<",
    "wordorder": ">"
}
```
Before decoding the modbus payloads, please consider that there is some 
confusion about Little-Endian vs. Big-Endian Word Order. The current modbus 
client allows the endiannesses of the byteorder (the Byte order of each word)
and the wordorder (the endianess of the word, when wordcount is >= 2) to be 
adjusted (see
[Parameters](https://github.com/ccatp/MODBUS/blob/625c77910993694c4dbdb4cad42c152e099af639/DeviceClassConfigs/mb_client_config_default.json)):

    ">" = Endian.Big 
    "<" = Endian.Little

Packing/unpacking depends on your CPU's word/byte order. MODBUS messages
are always using big endian. BinaryPayloadBuilder will per default use
what your CPU uses. The wordorder is applicable only for 32 and 64 bit values.
Let's say we need to write a value 0x12345678 to a 32 bit register.
The following combinations could be used to write the register 
[see also here](https://github.com/pymodbus-dev/pymodbus/blob/217469a234bc023a660acb9c448900288131022b/examples/client_payload.py). 

| Word Order | Byte order | Word1  | Word2  |
|------------|------------|--------|--------|
| Big        |     Big    | 0x1234 | 0x5678 |
| Big        |    Little  | 0x3412 | 0x7856 |
| Little     |     Big    | 0x5678 | 0x1234 |
| Little     |    Little  | 0x7856 | 0x3412 |

One note aside on bit maps to be read out of a register's 1<sup>st</sup> and/or 
2<sup>nd</sup> byte. Suppose a server's 16-bit register contains following 
hex value. The bit map
of a virtual parameter *TEST0* would look like:

```
         byte/1  byte/2
0x89AB = 1000100110101011
         h      lh      l
```

where l and h are the low and high bit of the byte, respectively. See also below,
when writing to registers with bit maps.
The byte order endianness on the client site
will absolutely not change the order of bits, 
whatsoever, if the *decode_bits* function is applied. What a relief!

Not implemented to date:
* decoder.bit_chunks() - coils

The result provided 
for the housekeeping (Kafka producer) is a list of dictionary objects.

Present MODBUS clients versions deploy the synchronous and 
asynchronous [ModbusTcpClients](https://pymodbus.readthedocs.io/en/latest/source/library/client.html#pymodbus.client.ModbusTcpClient) in its version v3.5.2 (as of 2023/10/01).

Run reader:
    
    python3 mb_client_readwrite.py --host <host address> \
                                   [--port <host port> (default: 502)] \
                                   [--debug]
                                   [--async_mode]
                                   [--config_filename <path to config file>]


## WRITER

Only the register classes coil (class 0) and holding registers (class 4)
are eligible for writing. Registers in those classes may be 
changed by utilizing the writer method of MODBUSClient class.

Run writer:
    
    python3 mb_client_readwrite.py --host <host address> \
                                   --payload "{\"test 32 bit int\": 720.04, ...}"
                                   [--port <host port> (default: 502)] \
                                   [--debug] \
                                   [--async_mode]
                                   [--config_filename <path to config file>]

It accepts - as input - a JSON with one or multiple
{"parameter": "value"} pairs, where parameter needs to match (required!)
its counterpart in the Reader JSON as already defined above.

Note: parameters defined for MODBUS register classes 1 and 3 will be ignored.

Caveat: 

* Owing to Python's pymodbus module, registers can solely be updated on the
whole, which particularly applies for strings, bits and 8 bit-integers 
of the leading and trailing bytes.
* No locking mechanism is applied for parallel reading and writing, except for 
the MODBUS Web API.
* When updating bit maps for a 16-bit register, say *TEST0*, 
note that the 
payload needs to be formatted as of below. If less than 16 bits are provided, 
it will populate the register starting at the low bit of byte/1, subsequent
will be set to false.

```
                        byte/1          byte/2
--payload "{\"TEST0\": [1,0,0,1,0,0,0,1,1,1,0,1,0,1,0,1]}"
                        l             h l             h
```

## MODBUS Web API

Run the Rest API comprising 
the previously described MODBUS READER and WRITER methods
of the *MODBUSClient* class. An internal 
locking mechanism prevents reading and writing to the same device simulaneously.

The JSON config file comprises 
{"parameter": "value"} pairs that can be read and updated on the modbus device,
where &lt;device&gt; denotes the extention for each modbus device class 
(to be updated):

| Extension | MODBUS Device Class               |
|-----------|-----------------------------------|
| default   | simulator                         |
| test      | testing reader & writer integrity |
| lhx       | Rack                              |
| Cryomech  | Cryocooler                        |

The appropriate config file for the device class 
is sought in modbusClient/configFiles directory.

To enroll a new modbus device class, just provide the 
config file mb_client_config_&lt;device&gt;.json to the DeviceClassConfigs 
directory. It will be copied appropriately with the Docker container setup.

Run the RestAPI for testing:

    python3 mb_client_RestAPI_<sync/async>.py --host <RestAPI host> (default: 127.0.0.1) \
                                              --port <RestAPI port> (default: 5100)

Get the read and write endpoints, by typing in the browser URL:

    <RestAPI host>:<RestAPI port>/docs#

![](https://github.com/ccatp/MODBUS/blob/a3cb28bf0e3df9b4a7fdd6e8e113a9134b3acd47/pics/API_swagger_MODBUS.png)

Alternatively, invoke cli *curl* for the Reader:

    curl <RestAPI host><RestAPI port>:/modbus/read/<host> 

and for the Writer:

    curl <RestAPI host>:<RestAPI port>/modbus/write/<host> -X PUT \
            -H 'accept: application/json' \
            -H 'Content-Type: application/json' \
            -d '{
            "test 32 bit int": 720.04, 
            "write int register": 10, 
            "string of register/1": "YZ", 
            "Coil 0": true, 
            "Coil 1": true, 
            "Coil 10": true
            }'

Caveat: 

Whilst environmental parameters are set in the Docker container, they have 
to be defined separately in the 
OS environment, ita est:

*ServerPort=&lt;MODBUS Server Port&gt;*,

*ServerIPS=&lt;MODBUS Server IP[, ...]&gt;*, and

*Debug=True/False*

## Content

The current repository comprises:

* class MODBUSClientSync (synchronous version)
    * read_register
    * write_register
    * close
* class MODBUSClientAsync (Asynchronous version)
    * read_register
    * write_register
* MODBUS Helper Routine
  * [Reader & Writer](https://github.com/ccatp/MODBUS/blob/339184677834f3a99d0d447083783113a0d5c1fc/helperRoutines/mb_client_readwrite.py) 
routine for both Synchronous & Asynchronous Clients
  * Server Simulator (cloned from https://hub.docker.com/r/oitc/modbus-server)
* MODBUS RestAPI
  * Synchronous
  * Asynchronous
* Docker 
  * Synchronous RestAPI
  * Asynchronous RestAPI
  * Synchronous RestAPI + ServerSimulator 
  (runs with additional Server Simulator)

MODBUS Server connection and register mapping details are defined in
mb_client_config_&lt;device&gt;.json.

For the Conda environment used, see [here](https://github.com/ccatp/MODBUS/blob/451ef17b0a7fc0eba00bc9a258781f206362849a/conda-env.yml)

Contact: Ralf Antonius Timmermann, AIfA, University Bonn, email: rtimmermann@astro.uni-bonn.de