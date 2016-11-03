from CQTdevices import *

analogIO_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_Analog_Mini_IO_Unit_MIO-QO13-if00'
analogIO=AnalogComm(analogIO_port)

def getPower(analogIO,channel=0,average=100):
    #Get the P810 transmission power on photodetector
    power=np.zeros(100)
    for i in range(average):
        power[i]=analogIO.get_voltage(channel)
    return np.mean(power)
while True:
    print(getPower(analogIO))

