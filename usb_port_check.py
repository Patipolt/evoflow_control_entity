from serial.tools import list_ports

# list all available serial ports
def list_serial_ports():
    ports = list_ports.comports()
    return [port.device for port in ports]

ports = list_serial_ports()
for port in ports:
    print(port)