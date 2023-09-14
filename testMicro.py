from tecancavro.models import XCaliburD

# from tecancavro.transport import TecanAPIMicro, TecanAPISerial
from tecancavro.transport import TecanAPIMicro
import sys

if sys.platform.startswith('win'):
    import serial
    from tecancavro.tecanapi import TecanAPI, TecanAPITimeout

# Functions to return instantiated XCaliburD objects for testing

def returnSerialXCaliburD():
    test0 = XCaliburD(com_link=TecanAPIMicro(0, '/dev/tty.usbserial', 9600))
    return test0

def returnNodeXCaliburD():
	test0 = XCaliburD(com_link=TecanAPINode(0, '192.168.1.140:80'), waste_port=6)
	return test0

def findSerialPumps():
    print("looking for pumps...")
    if sys.platform.startswith('win'):
         return TecanAPISerial.findSerialPumps()
    else: 
        return TecanAPIMicro.findSerialPumps()

def getSerialPumps():
    ''' Assumes that the pumps are XCaliburD pumps and returns a list of
    (<serial port>, <instantiated XCaliburD>) tuples
    '''
    pump_list = findSerialPumps()
    print(f'pump list = {pump_list}')
    if sys.platform.startswith('win'):
        return [(ser_port, XCaliburD(com_link=TecanAPISerial(0,
                ser_port, 9600))) for ser_port, _, _ in pump_list]
    if sys.platform.startswith('rp2'):
        # Pi pico or similar
        return [(ser_port, XCaliburD(com_link=TecanAPIMicro(0,
                ser_port, 9600))) for ser_port, _, _ in pump_list]


if __name__ == '__main__':
    # print(findSerialPumps())
    pumps = getSerialPumps()
    pumps_dict = dict(pumps)
    # print(pumps_dict)
    pump1 = pumps_dict['uart0']
    # pump1 = pumps_dict['COM13']
    pump1.init(in_port=1, out_port=3)
    pump1.extract(1,2000)
    pump1.dispense(3,2000)
    delay = pump1.executeChain()
    pump1.waitReady(delay)
    print("done")