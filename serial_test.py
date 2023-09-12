from machine import Pin, UART
from time import sleep

uart0 = UART(0,9600)
uart0.init(baudrate=9600,tx=Pin(0),rx=Pin(1), flow = 0, timeout=500)
print(uart0)

command = bytes(f'/1?76\r', 'utf-8')
# written = uart0.write(command)

OEMcommand = b'\x02\x31\x31?76\x03<'
written = uart0.write(OEMcommand)

print(f'{written} bytes were written')
sleep(0.5) 
resp = uart0.read(50)

if resp is not None:
    print(f'reply from pump: {resp.hex()}')
    print(resp[:2].hex())
    print(resp[2:-3])
else:
    print("no reply from pump")
# resp = uart0.read(50)
# print(resp.hex())
