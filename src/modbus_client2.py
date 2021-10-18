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
        """

        :param client: instance
        MODBUS client
        :param mapping: dictionary
        mapping of all registers as from JSON
        :param entity: str
        register prefix
        """
        self.client = client
        self.entity = entity
        # select mapping for each entity
        self.register_maps = {key: value for key, value in
                              sorted(mapping.items()) if key[0] == self.entity}
        els = [i for i in self.register_maps]
        if not els:
            self.boundaries = {}
        else:
            last = els[-1]
            # length of key for e.g.
            # '3xxxx/3xxxx' or
            # '3xxxx/2 or just
            # '3xxxx
            mini = els[0].split("/")[0]
            if len(last) != 11:
                maxi = last.split("/")[0]
            else:
                maxi = last.split("/")[1]
            self.boundaries = {
                "min": mini,
                "max": maxi,
                "start": int(mini[1:]) - 1,
                "width": int(maxi[1:]) - int(mini[1:]) + 1
            }

    @staticmethod
    def diff(i, j):
        """
        :param i: str
        low register number
        :param j: str
        high register number
        :return: int
        gap between high-low in number of bytes
        """
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
        except BinaryStringError:
            logging.error("Error: wrong binary string in mapping")

    def formatter(self, decoder, decoded, register):
        """
        format the output dictionary and append by scanning through the mapping
        of the registers. If gaps in the mappings are detected they are skipped
        by the number of bytes.
        :param decoder: A deferred response handle from the register readings
        :param decoded: dictionary
        :param register: dictionary
        :return: dict
        """
        function = self.register_maps[register]['function']
        parameter = self.register_maps[register]['parameter']
        maps = self.register_maps[register].get('map')
        desc = self.register_maps[register].get('desc')
        value = getattr(decoder, function)()
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

    def formatter_bit(self, decoder, decoded, register):
        """
        indexes the result array of bits by the keys found in the mapping
        :param decoder: A deferred response handle from the register readings
        :param decoded: dictionary
        :param register: dictionary
        :return: dict
        """
        parameter = self.register_maps[register]['parameter']
        desc = self.register_maps[register].get('desc')
        decoded.append({
            "parameter": parameter,
            "value": decoder[int(register[1:]) - 1],
            "description": desc
        })

        return decoded

    def run(self):
        """
        instantiates the classes for the 4 register object types and invokes
        the run methods within an interval.
        :return: dictionary of output
        """
        if not self.boundaries:
            return []
        result = None
        if self.entity == '1':
            # for simplicity we read in the max of 2000 bits
            result = self.client.read_discrete_inputs(address=0,
                                                      count=2000)
        elif self.entity == '2':
            result = self.client.read_coils(address=0,
                                            count=2000)
        elif self.entity == '3':
            result = self.client.read_input_registers(
                address=self.boundaries['start'],
                count=self.boundaries['width'])
        elif self.entity == '4':
            result = self.client.read_holding_registers(
                address=self.boundaries['start'],
                count=self.boundaries['width'])
        assert (not result.isError())

        decoded = list()
        if self.entity in ['3', '4']:
            decoder = BinaryPayloadDecoder.fromRegisters(result.registers,
                                                         byteorder=Endian.Big)
            # loop incl. penultimate and find gaps not to be read-out
            for index, item in enumerate(list(self.register_maps.keys())[:-1]):
                decoded = self.formatter(
                    decoder,
                    decoded,
                    item)
                # find if there's something to skip
                skip = self.diff(
                    item,
                    list(self.register_maps.keys())[index + 1])
                decoder.skip_bytes(skip)
            # last entry in dict
            decoded = self.formatter(
                decoder,
                decoded,
                list(self.register_maps.keys())[-1])
        elif self.entity in ['1', '2']:
            decoder = result.bits
            for item in self.register_maps.keys():
                decoded = self.formatter_bit(
                    decoder,
                    decoded,
                    item)

        return decoded


def main():

    with open('client_config.json') as json_file:
        client_config = json.load(json_file)

    with open('client_mapping.json') as json_file:
        mapping = json.load(json_file)

    client = ModbusClient(host=client_config["server"]["listenerAddress"],
                          port=client_config["server"]["listenerPort"])
    client.connect()

    register_class = ['1', '2', '3', '4']
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
