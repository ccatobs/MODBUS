from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client.sync import ModbusTcpClient as ModbusClient
import time
import json
import logging

myformat = "%(asctime)s.%(msecs)03d :: %(levelname)s: %(filename)s - %(lineno)s - %(funcName)s()\t%(message)s"
logging.basicConfig(format=myformat,
                    level=logging.INFO,
                    datefmt="%Y-%m-%d %H:%M:%S")
logging.getLogger().setLevel(logging.INFO)


class BinaryStringError(Exception):
    """Base class for other exceptions"""
    pass


class ObjectType(object):
    def __init__(self, client, mapping, entity):
        self.client = client
        self.entity = entity
        # select mapping per entity
        self.register_maps = {key: value for key, value in mapping.items() if
                              key[0] == self.entity}
        els = [i for i in self.register_maps]
        if not els:
            self.boundaries = {}
        else:
            last = els[-1]
            # length of key for e.g. '3xxxx/3xxxx'
            if len(last) != 11:
                mini = els[0].split("/")[0]
                maxi = last.split("/")[0]
            else:
                mini = els[0].split("/")[0]
                maxi = last.split("/")[1]
            self.boundaries = {
                "min": mini,
                "max": maxi,
                "start": int(mini[1:]) - 1,
                "width": int(maxi[1:]) - int(mini[1:]) + 1
            }

    @staticmethod
    def diff(i, j):
        """gap in number of bytes"""
        high = j.split("/")[0]
        if len(i) == 11:
            low = i.split("/")[1]
        elif len(i) > 5:
            low = i.split("/")[0]
            if low == high:
                return 0
            if i.split("/")[1] == "1":
                return (int(high) - int(low) - 1) * 2 + 1
        else:
            low = i.split("/")[0]
        return (int(high) - int(low) - 1) * 2

    @staticmethod
    def binary_map(binarystring):
        try:
            tmp = binarystring.split("0b")[1]
            if tmp.count('1') != 1:
                raise BinaryStringError
            return tmp[::-1].index('1')
        except IndexError:
            logging.error("Error: no binary string in mapping")
        except BinaryStringError:
            logging.error("Error: wrong binary string in mapping")

    def formatter(self, decoder, decoded, register):
        function = self.register_maps[register]['function']
        parameter = self.register_maps[register]['parameter']
        maps = self.register_maps[register].get('map')
        value = getattr(decoder, function)()
        if function == 'decode_bits':
            for key, desc in self.register_maps[register]['map'].items():
                decoded.append(
                    {
                        "parameter": parameter,
                        "value": value[self.binary_map(binarystring=key)],
                        "description": desc
                    }
                )
        else:
            desc = maps.get(str(round(value))) if maps else parameter
            decoded.append(
                {
                    "parameter": parameter,
                    "value": value,
                    "description": desc
                }
            )

        return decoded

    def run(self):

        method = None
        # result = client.read_xxx_registers(start, width)
        if self.entity == '3':
            method = 'read_input_registers'
        elif self.entity == '4':
            method = 'read_holding_registers'
        result = getattr(self.client, method)(
            self.boundaries['start'],
            self.boundaries['width']
        )
        assert (not result.isError())
        decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                     byteorder=Endian.Big)
        # loop incl. penultimate and find gaps not to be read-out
        decoded = list()
        for index, item in enumerate(list(self.register_maps.keys())[:-1]):
            decoded = self.formatter(decoder,
                                     decoded,
                                     item)
            # find if there's something to skip
            skip = self.diff(item,
                             list(self.register_maps.keys())[index+1]
                             )
            decoder.skip_bytes(skip)
        # last entry in dict
        decoded = self.formatter(decoder,
                                 decoded,
                                 list(self.register_maps.keys())[-1]
                                 )

        return decoded


def main():

    with open('client_config.json') as json_file:
        client_config = json.load(json_file)

    with open('client_mapping.json') as json_file:
        mapping = json.load(json_file)

    client = ModbusClient(host=client_config["server"]["listenerAddress"],
                          port=client_config["server"]["listenerPort"])
    client.connect()

    register_class = ['3', '4']

    instance_list = list()
    for regs in register_class:
        instance_list.append(ObjectType(client=client,
                                        mapping=mapping,
                                        entity=regs))

    decoded = list()
    while True:
        for insts in instance_list:
            # append all decoded from all register classes
            decoded = decoded + insts.run()
        print(decoded)

        time.sleep(client_config["hk"]["interval"])


if __name__ == '__main__':
    main()
