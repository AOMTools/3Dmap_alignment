
#Note: Vx should be Vz
import numpy as np
#from pylab import *
#import matplotlib.pyplot as plt
#import matplotlib.mlab as ml
from Counter import Countercomm
from CQTdevices import WindFreakUsb2
import time
import zmq


#Setup communication with Cavity_retreat
##############################################################################################
context = zmq.Context()

#  Socket to talk to server
print ("Connecting to the retreat controller server")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5556")
##############################################################################################




#Functions calls
##############################################################################################
def setV(Vx,Vy):
    '''
    set an absolute voltage to piezo via delegating to cavity_retreat controller
    '''
    #socket.send("SetVolt5 0")
    #message = socket.recv()
    command1="SetVolt5 "+str(Vy)
    command2="SetVolt6 "+str(Vx)
    print(command1)
    print(command2)
    socket.send(command1)
    message=socket.recv()
    socket.send(command2)
    message=socket.recv()

def getCount(miniusb,channel=0,average=10):
    counts=[]
    for i in range(average):
        counts.append(miniusb.get_counts(channel))
    average_count=np.mean(counts)
    return average_count
##############################################################################################


#initial miniusb counter device
miniusb_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_USB_Counter_Ucnt-QO10-if00'
miniusb=Countercomm(miniusb_port)

#initiate analogI0
analogI0_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_Analog_Mini_IO_Unit_MIO-QO13-if00'
analogI0=AnalogComm(analogI0_port)

#initiate windfreak
wf_port='/dev/serial/by-id/usb-Windfreak_Synth_Windfreak_CDC_Serial_014571-if00'
wf=WindFreakUsb2(wf_port)




#Parmeters defnition
#Retrieve current voltage set to PZT as the initial VX0,VY0
socket.send("CheckVolt 5")
V0y=float((socket.recv()).split()[-1])
socket.send("CheckVolt 6")
V0x=float((socket.recv()).split()[-1])
print('Initial Voltage: ',V0x,V0y)
#Scanning
rangeVx=0.1
rangeVy=0.1
stepV=0.02
numStepx=int(rangeVx/stepV)
numStepy=int(rangeVy/stepV)
xgrid = np.arange(-numStepx ,numStepx+1)*stepV
ygrid = np.arange(-numStepy ,numStepy+1)*stepV
print(xgrid)
xscan = []
yscan = []




filename='test3.dat'


#employ a rastering scan to possibly reduce hysterisis of PZT
#to generate all Vsteps for rastering scan
# define some grids
for i, yi in enumerate(ygrid):
    xscan.append(xgrid[::(-1)**i]) # reverse when i is odd
    yscan.append(np.ones_like(xgrid) * yi)

# squeeze lists together to vectors
xscan = np.concatenate(xscan)
yscan = np.concatenate(yscan)


#initial freq
f0=float(wf.get_freq())/1000
range_f=40
fnumstep=10
f=f0+np.arange(-40,41,fnumstep)
print(f)


#Tcount
Tcount=np.zeros((np.size(xscan),fnumstep))
print('xscan size')
print(np.size(xscan))
print('Tcount')
print(Tcount)

#sending voltage and measurement
for j in range(np.size(f)):
    wf.slow_set_freq(f[j],5)
    time.sleep(1)
    for i in range(np.size(xscan)):
        print(np.asarray((xscan[i],yscan[i])))
        setV(xscan[i]+V0x,yscan[i]+V0y)
        time.sleep(0.5)
        print('i,j are')
        print(i,j)
        print(Tcount[i,j])
        Tcount[i,j]=getCount(miniusb)

result=np.column_stack((xscan,yscan,Tcount))
np.savetxt(filename,result,fmt='%1.3f')


#Close connection
wf.close()
