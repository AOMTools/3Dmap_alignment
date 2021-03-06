
#Note: Vx should be Vz
import numpy as np
#from pylab import *
#import matplotlib.pyplot as plt
#import matplotlib.mlab as ml
from Counter import Countercomm
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
address_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_USB_Counter_Ucnt-QO10-if00'
miniusb=Countercomm(address_port)

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
stepV=0.01
numStepx=int(rangeVx/stepV)
numStepy=int(rangeVy/stepV)
xgrid = np.arange(-numStepx ,numStepx+1)*stepV
ygrid = np.arange(-numStepy ,numStepy+1)*stepV
print(xgrid)
xscan = []
yscan = []

Tcount=[]

filename='test2.dat'


#employ a rastering scan to possibly reduce hysterisis of PZT
#to generate all Vsteps for rastering scan
# define some grids
for i, yi in enumerate(ygrid):
    xscan.append(xgrid[::(-1)**i]) # reverse when i is odd
    yscan.append(np.ones_like(xgrid) * yi)

# squeeze lists together to vectors
xscan = np.concatenate(xscan)
yscan = np.concatenate(yscan)

#sending voltage and measurement

for i in range(np.size(xscan)):
    print(np.asarray((xscan[i],yscan[i])))
    setV(xscan[i]+V0x,yscan[i]+V0y)
    time.sleep(0.5)
    Tcount.append(getCount(miniusb))

result=np.column_stack((xscan,yscan,Tcount))
np.savetxt(filename,result,fmt='%1.3f')

#Plotting
'''
xi = np.linspace(min(xscan), max(xscan),100)
yi = np.linspace(min(yscan), max(yscan),100)
z=Tcount
#zi = ml.griddata(xscan, yscan, z, xi, yi, interp='nn')
zi = ml.griddata(xscan, yscan, z, xi, yi, interp='linear')

plt.contour(xi, yi, zi, 15, linewidths = 0.5, colors = 'k')
plt.pcolormesh(xi, yi, zi, cmap = plt.get_cmap('rainbow'))

plt.colorbar()
plt.scatter(xscan, yscan, marker = 'o', c = 'b', s = 10, zorder = 10)
plt.xlim(min(xscan), max(xscan))
plt.ylim(min(yscan), max(yscan))
plt.show()
'''
