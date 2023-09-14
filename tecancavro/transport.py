"""
transport.py

Contains transport layer subclasses of the `TecanAPI` class, which provides
Tecan OEM API frame handling. All subclasses expose instance method `sendRcv`,
which sends a command string (`cmd`) and returns a dictionary containing the
`status_byte` and `data` in the response frame. Current subclasses include:

`TecanAPISerial` : Provides serial encapsulation of TecanAPI frame handling.
                  Can facilitate communication with multiple Tecan devices
                  on the same RS-232 port (i.e., daisy-chaining) by sharing
                  a single serial port instance.

"""

import sys
from random import getrandbits # used as alternative to uuid

if sys.platform.startswith('win'):
    import serial
    import uuid
    from time import sleep

if sys.platform.startswith('rp2'):
        # Pi pico or similar
        from machine import UART, Pin
        from time import sleep
         
from tecancavro.tecanapi import TecanAPI, TecanAPITimeout

# From http://stackoverflow.com/questions/12090503/
#      listing-available-com-ports-with-python
def listSerialPorts():
    """Lists serial ports

    :raises EnvironmentError:
        On unsupported or unknown platforms
    :returns:
        A list of available serial ports
    """
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)] 

    elif sys.platform.startswith('rp2'):
        # Pi pico or similar
        ports = ['uart0'] # could also include uart1 if needed

    else:
        raise EnvironmentError('Unsupported platform')

    result = []

    if sys.platform.startswith('rp2'):
        for port in ports:
            result.append(port)

    else:
        for port in ports:
            try:
                # print(f'checking port {port}')
                s = serial.Serial(port)
                s.close()
                print(f'Found active port: {port}')
                result.append(port)
            except (OSError, serial.SerialException):
                # print('got OSError in listSerialPorts')
                pass
    return result

class TecanAPIMicro(TecanAPI):
    """
    Wraps the TecanAPI class to provide serial communication encapsulation
    and management for the Tecan OEM API. Designed to run on microcontrollers
    like the Pi Pico (RP2040). Maps devices to a state-monitored
    dictionary, `ser_mapping`, which allows multiple Tecan devices to
    share a serial port (provided that the serial params are the same).
    """

    ser_mapping = {}

    @classmethod
    def findSerialPumps(cls, tecan_addrs=[0], ser_baud=9600, ser_timeout=500,
                        max_attempts=2):
        ''' Find any enumerated syringe pumps on the serial ports.

        timeout in ms.

        Returns list of (<ser_port>, <pump_config>, <pump_firmware_version>)
        tuples.
        '''
        print('Starting findSerialPumps...')
        found_devices = []
        for port_path in listSerialPorts():
            print(f'Checking port {port_path}')
            for addr in tecan_addrs:
                print(f'Checking address {addr}...')
               
                try:
                    # print(f'try block: attempting to open port...')
                    p = cls(addr, port_path, ser_baud,
                            ser_timeout, max_attempts)
                    # print('Attempting to read pump configuration...')
                    config = p.sendRcv('?76')['data']
                    # print(f'pump configuration: {config}')
                    fw_version = p.sendRcv('&')['data']
                    found_devices.append((port_path, config, fw_version))
                except OSError as e:
                    if e.errno != 16:  # Resource busy
                        raise
                except TecanAPITimeout as err:
                    # print(err)
                    pass
        # print(f'devices found = {found_devices}')
        return found_devices

    def __init__(self, tecan_addr, ser_port, ser_baud, ser_timeout=500,
                 max_attempts=2):

        super(TecanAPIMicro, self).__init__(tecan_addr)

        self.id_ = getrandbits(32) # poor mans uuid
        # self.id_ = str(getrandbits(32)) # poor mans uuid
        self.ser_port = ser_port
        self.ser_info = {
            'baud': ser_baud,
            'timeout': ser_timeout,
            'max_attempts': max_attempts
        }
        self._registerSer()

    def sendRcv(self, cmd):
        # print("starting sendRcv...")
        attempt_num = 0
        while attempt_num < self.ser_info['max_attempts']:
            try:
                attempt_num += 1
                # print(f'Communication attempt num {attempt_num}')
                if attempt_num == 1:
                    frame_out = self.emitFrame(cmd)
                else:
                    frame_out = self.emitRepeat()
                # print(self)
                self._sendFrame(frame_out)
                sleep(0.1)
                frame_in = self._receiveFrame()
                if frame_in:
                    return frame_in
                sleep(0.05 * attempt_num)
            # except serial.SerialException:
            except:
                sleep(0.2)
        # raise(TecanAPITimeout('Tecan serial communication exceeded max '
        #                       'attempts [{0}]'.format(
        #                       self.ser_info['max_attempts'])))
        raise(TecanAPITimeout('Tecan timeout error'))

    def _sendFrame(self, frame):
        # print(f'frame to be sent: {frame.hex(" ")}')
        self._ser.write(frame)

    def _receiveFrame(self):
        raw_data = self._ser.read(50)
        # print(f'raw_data return from _receiveFrame: {raw_data}')
        return self.parseFrame(raw_data)

    def _registerSer(self):
        """
        Checks to see if another TecanAPISerial instance has registered the
        same serial port in `ser_mapping`. If there is a conflict, checks to
        see if the parameters match, and if they do, shares the connection.
        Otherwise it raises a `serial.SerialException`.
        """
        reg = TecanAPIMicro.ser_mapping
        port = self.ser_port
        # print(f'In _registerSer. Port = {port}')
        # print(f'reg = {reg}')
        if self.ser_port not in reg:
            # print(f'{self.ser_port} not in reg. Attemping to register port.')
            reg[port] = {}
            reg[port]['info'] = {k: v for k, v in self.ser_info.items()}
            # print( 'registered port info:', reg[port]['info'])
            uart = UART(int(port[-1]),9600) # last character of port name is port number
            uart.init(
                    baudrate=reg[port]['info']['baud'],
                    timeout=reg[port]['info']['timeout'],
                    tx=Pin(0),
                    rx=Pin(1),
                    flow = 0
                    ) # note pin numbers are logical GPnn, not physical pins 1..40
            reg[port]['_ser'] = uart
            # print(f"registered serial port after init: {reg[port]['_ser']}")
            reg[port]['_devices'] = [self.id_]
        else:
            if len(set(self.ser_info.items()) & set(reg[port]['info'].items())) != 3:
                raise Exception('TecanAPISerial conflict: ' \
                    'another device is already registered to {0} with ' \
                    'different parameters'.format(port))
            else:
                reg[port]['_devices'].append(self.id_)
        self._ser = reg[port]['_ser']

    def __del__(self):
        """
        Cleanup serial port registration on delete
        """
        port_reg = TecanAPISerial.ser_mapping[self.ser_port]
        try:
            dev_list = port_reg['_devices']
            ind = dev_list.index(self.id_)
            del dev_list[ind]
            if len(dev_list) == 0:
                port_reg['_ser'].deinit()
                del port_reg, TecanAPISerial.ser_mapping[self.ser_port]
        except KeyError:
            pass

class TecanAPISerial(TecanAPI):
    """
    Wraps the TecanAPI class to provide serial communication encapsulation
    and management for the Tecan OEM API. Maps devices to a state-monitored
    dictionary, `ser_mapping`, which allows multiple Tecan devices to
    share a serial port (provided that the serial params are the same).
    """

    ser_mapping = {}

    @classmethod
    def findSerialPumps(cls, tecan_addrs=[0], ser_baud=9600, ser_timeout=0.2,
                        max_attempts=2):
        ''' Find any enumerated syringe pumps on the local com / serial ports.

        Returns list of (<ser_port>, <pump_config>, <pump_firmware_version>)
        tuples.
        '''
        print('Starting findSerialPumps...')
        found_devices = []
        for port_path in listSerialPorts():
            print(f'Checking port {port_path}')
            for addr in tecan_addrs:
                print(f'Checking address {addr}')
               
                try:
                    p = cls(addr, port_path, ser_baud,
                            ser_timeout, max_attempts)
                    config = p.sendRcv('?76')['data']
                    fw_version = p.sendRcv('&')['data']
                    found_devices.append((port_path, config, fw_version))
                except OSError as e:
                    if e.errno != 16:  # Resource busy
                        raise
                except TecanAPITimeout:
                    pass
        # print(f'devices found = {found_devices}')
        return found_devices

    def __init__(self, tecan_addr, ser_port, ser_baud, ser_timeout=0.1,
                 max_attempts=5):

        super(TecanAPISerial, self).__init__(tecan_addr)

        self.id_ = str(uuid.uuid4())
        self.ser_port = ser_port
        self.ser_info = {
            'baud': ser_baud,
            'timeout': ser_timeout,
            'max_attempts': max_attempts
        }
        self._registerSer()

    def sendRcv(self, cmd):
        attempt_num = 0
        while attempt_num < self.ser_info['max_attempts']:
            try:
                attempt_num += 1
                if attempt_num == 1:
                    frame_out = self.emitFrame(cmd)
                else:
                    frame_out = self.emitRepeat()
                self._sendFrame(frame_out)
                frame_in = self._receiveFrame()
                if frame_in:
                    return frame_in
                sleep(0.05 * attempt_num)
            except serial.SerialException:
                sleep(0.2)
        raise(TecanAPITimeout('Tecan serial communication exceeded max '
                              'attempts [{0}]'.format(
                              self.ser_info['max_attempts'])))

    def _sendFrame(self, frame):
        # print(f'frame to be sent: {frame.hex(" ")}')
        self._ser.write(frame)

    def _receiveFrame(self):
        raw_data = b''
        raw_byte = self._ser.read()
        while raw_byte != b'':
            raw_data += raw_byte
            raw_byte = self._ser.read()
        return self.parseFrame(raw_data)

    def _registerSer(self):
        """
        Checks to see if another TecanAPISerial instance has registered the
        same serial port in `ser_mapping`. If there is a conflict, checks to
        see if the parameters match, and if they do, shares the connection.
        Otherwise it raises a `serial.SerialException`.
        """
        reg = TecanAPISerial.ser_mapping
        port = self.ser_port
        if self.ser_port not in reg:
            reg[port] = {}
            reg[port]['info'] = {k: v for k, v in self.ser_info.items()}
            reg[port]['_ser'] = serial.Serial(port=port,
                                    baudrate=reg[port]['info']['baud'],
                                    timeout=reg[port]['info']['timeout'])
            reg[port]['_devices'] = [self.id_]
        else:
            if len(set(self.ser_info.items()) &
               set(reg[port]['info'].items())) != 3:
                raise serial.SerialException('TecanAPISerial conflict: ' \
                    'another device is already registered to {0} with ' \
                    'different parameters'.format(port))
            else:
                reg[port]['_devices'].append(self.id_)
        self._ser = reg[port]['_ser']

    def __del__(self):
        """
        Cleanup serial port registration on delete
        """
        port_reg = TecanAPISerial.ser_mapping[self.ser_port]
        try:
            dev_list = port_reg['_devices']
            ind = dev_list.index(self.id_)
            del dev_list[ind]
            if len(dev_list) == 0:
                port_reg['_ser'].close()
                del port_reg, TecanAPISerial.ser_mapping[self.ser_port]
        except KeyError:
            pass

