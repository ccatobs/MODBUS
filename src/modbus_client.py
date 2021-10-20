from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import time
import json
import re
import sys
import logging


class BinaryStringError(Exception):
    """Base class for other exceptions"""
    pass


class MappingKeyError(Exception):
    """Base class for other exceptions"""
    pass


class DuplicateParameterError(Exception):
    """Base class for other exceptions"""
    pass


class ObjectType(object):
    def __init__(self, client, mapping, entity):
        """
        :param client: instance- MODBUS client
        :param mapping: dictionary - mapping of all registers as from JSON
        :param entity: str - register prefix
        """
        self.client = client
        self.entity = entity
        # select mapping for each entity and sort by key
        self.register_maps = {
            key: value for key, value in
            sorted(mapping.items()) if key[0] == self.entity
        }

        els = [i for i in self.register_maps]
        if not els:
            self.boundaries = {}
        else:
            mini = els[0].split("/")[0]
            maxi = els[-1].split("/")[0]
            if len(els[-1].split("/")) == 2:
                if els[-1].split("/")[1] not in ['1', '2']:
                    maxi = els[-1].split("/")[1]
            self.boundaries = {
                "min": mini,
                "max": maxi,
                "start": int(mini[1:]),
                "width": int(maxi[1:]) - int(mini[1:]) + 1
            }
            if self.entity in ['0', '1']:
                if self.boundaries['start'] + self.boundaries['width'] >= 2000:
                    logging.error("Error: number of registers superseed "
                                  "limit of 2000. Consider a redesign!")
                    sys.exit(1)

    @staticmethod
    def gap(low, high):
        """
        :param low: str - low register number
        :param high: str - high register number
        :return: int - gap between high and low registers in number of bytes
        """
        byt = 0
        hb = high.split("/")
        if len(hb) == 2:
            if hb[1] == "2":
                byt += 1
        lb = low.split("/")
        if len(lb) == 2:
            if lb[1] == "1":
                return (int(hb[0]) - int(lb[0]) - 1) * 2 + 1 + byt
            elif lb[1] == "2":
                return (int(hb[0]) - int(lb[0]) - 1) * 2 + byt
            else:
                return (int(hb[0]) - int(lb[1]) - 1) * 2 + byt
        else:
            return (int(hb[0]) - int(lb[0]) - 1) * 2 + byt

    @staticmethod
    def binary_map(binarystring):
        """
        position of True in binary string. Report if malformated in mapping.
        :param binarystring: str
        :return: integer
        """
        try:
            tmp = binarystring.split("0b")[1]
            if tmp.count('1') != 1:
                raise BinaryStringError
            return tmp[::-1].index('1')
        except IndexError:
            logging.error("Error: no binary string in mapping")
            sys.exit(1)
        except BinaryStringError:
            logging.error("Error: wrong binary string in mapping")
            sys.exit(1)

    def formatter(self, decoder, register):
        """
        format the output dictionary and append by scanning through the mapping
        of the registers. If gaps in the mappings are detected they are skipped
        by the number of bytes.
        :param decoder: A deferred response handle from the register readings
        :param register: dictionary
        :return: dictionary
        """
        function = self.register_maps[register]['function']
        parameter = self.register_maps[register]['parameter']
        maps = self.register_maps[register].get('map')
        desc = self.register_maps[register].get('desc')
        value = getattr(decoder, function)()
        decoded = list()
        if function == 'decode_bits':
            for key, name in self.register_maps[register]['map'].items():
                decoded.append(
                    {
                        "parameter": parameter,
                        "value": value[self.binary_map(binarystring=key)],
                        "description": name
                    }
                )
        else:
            desc = maps.get(str(round(value))) if maps else desc
            decoded.append(
                {
                    "parameter": parameter,
                    "value": value,
                    "description": desc
                }
            )

        return decoded

    def formatter_bit(self, decoder, register):
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param register: dictionary
        :return: dictionary
        """
        parameter = self.register_maps[register]['parameter']
        desc = self.register_maps[register].get('desc')

        return [
            {
                "parameter": parameter,
                "value": decoder[int(register[1:])],
                "description": desc
            }
        ]

    def run(self):
        """
        instantiates the classes for the 4 register object types and invokes
        the run methods within an interval.
        These two methods are not yet implemented !!!
            decoder.decode_string(size=1) - Decodes a string from the buffer
            decoder.bit_chunks() - classmethod
        :return: dictionary
        """
        if not self.boundaries:
            return []
        result = None
        if self.entity == '0':
            # ToDo: for simplicity we read first 2000 bits
            result = self.client.read_coils(address=0,
                                            count=2000
                                            )
        elif self.entity == '1':
            # ToDo: for simplicity we read first 2000 bits
            result = self.client.read_discrete_inputs(address=0,
                                                      count=2000
                                                      )
        elif self.entity == '3':
            result = self.client.read_input_registers(
                address=self.boundaries['start'],
                count=self.boundaries['width']
            )
        elif self.entity == '4':
            result = self.client.read_holding_registers(
                address=self.boundaries['start'],
                count=self.boundaries['width']
            )
        assert (not result.isError())

        decoded = list()
        if self.entity in ['3', '4']:
            decoder = BinaryPayloadDecoder.fromRegisters(
                registers=result.registers,
                byteorder=Endian.Big
            )
            # loop incl. penultimate and find gaps not to be read-out
            for index, register in enumerate(
                    list(self.register_maps.keys())[:-1]):
                decoded = decoded + self.formatter(
                    decoder=decoder,
                    register=register
                )
                # if there are bytes to skip
                skip = self.gap(
                    low=register,
                    high=list(self.register_maps.keys())[index + 1]
                )
                decoder.skip_bytes(nbytes=skip)
            # last entry in dictionary
            decoded = decoded + self.formatter(
                decoder=decoder,
                register=list(self.register_maps.keys())[-1])
        elif self.entity in ['0', '1']:
            decoder = result.bits
            for register in self.register_maps.keys():
                decoded = decoded + self.formatter_bit(
                    decoder=decoder,
                    register=register
                )

        return decoded


def main():

    with open('client_config.json') as config_file:
        client_config = json.load(config_file)

    myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
    logging.basicConfig(format=myformat,
                        level=logging.INFO,
                        datefmt="%Y-%m-%d %H:%M:%S")
    if client_config['debug']:
        logging.getLogger().setLevel(logging.DEBUG)

    with open('client_mapping.json') as json_file:
        mapping = json.load(json_file)

    # checks on the client mapping
    # test on keys in mapping
    # keys are of following formate: '3xxxx/3xxxx', '3xxxx/2 or '3xxxx'
    rev_dict = dict()
    try:
        for key, value in mapping.items():
            if not re.match(
                    r"^[0134][0-9]{4}(/([12]|[0134][0-9]{4}))?$",
                    key):
                raise MappingKeyError
            rev_dict.setdefault(value["parameter"], set()).add(key)
            parameter = [key for key, values in rev_dict.items()
                         if len(values) > 1]
            if parameter:
                raise DuplicateParameterError
    except MappingKeyError:
        logging.error("Error: wrong key in mapping: {0}".format(key))
        return 1
    except DuplicateParameterError:
        logging.error("Error: duplicate parameters: {0}".format(parameter))
        return 1

    client = ModbusClient(host=client_config["server"]["listenerAddress"],
                          port=client_config["server"]["listenerPort"])
    client.connect()

    register_class = ['0', '1', '3', '4']
    instance_list = list()
    for regs in register_class:
        instance_list.append(ObjectType(client=client,
                                        mapping=mapping,
                                        entity=regs))

    while True:
        decoded = list()
        for insts in instance_list:
            # append all decoded from all register classes
            decoded = decoded + insts.run()
        print(decoded)

        time.sleep(client_config["hk"]["interval"])


if __name__ == '__main__':
    main()
