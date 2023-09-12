from machine import Pin, UART
from time import sleep

def _buildChecksum(partial_frame):
        """
        Builds a checksum based on a partial API frame (frame minus the
        checksum) by XORing the byte values. Returns the checksum as
        an int.

        Args:
            `partial_frame` (list or bytestring) : an assembled api frame
                (with start and end bytes but no checksum)
        """
        checksum = 0
        for byte in partial_frame:
            checksum ^= byte
        return checksum

uart0 = UART(0,9600)
uart0.init(baudrate=9600,tx=Pin(0),rx=Pin(1), flow = 0, timeout=500)
print(uart0)

# command = bytes(f'/1?76\r', 'utf-8')
# print(command)
# written = uart0.write(command)

# cmdStr = b'/1?76\r'
# print(cmdStr)
# test = cmdStr.hex(' ')
# print(test)

# OEMcommand = b'\x02\x31\x31?76\x03<'
# print(OEMcommand.hex())
# written = uart0.write(OEMcommand)

OEMcommand = b'\x02\x31\x31?76\x03c'
checksum = _buildChecksum(OEMcommand[:-1])
print(f'checksum: {checksum}')
print(OEMcommand.hex(' '))
written = uart0.write(OEMcommand)

print(f'{written} bytes were written')
sleep(0.5) 
resp = uart0.read(50)

if resp is not None:
    print(f'reply from pump: {resp.hex(" ")}')
    print(resp[:2].hex())
    print(resp[2:-3])
else:
    print("no reply from pump")
# resp = uart0.read(50)
# print(resp.hex())
