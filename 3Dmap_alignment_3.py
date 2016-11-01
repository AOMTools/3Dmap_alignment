
#Note: Vx should be Vz
#Modify for scanning in time
import numpy as np
from Counter import Countercomm
from CQTdevices import *
import time
import zmq
from sys import exit
import subprocess as sp



#telegram
READPROG="telegram-cli"




#Setup communication with Cavity_retreat
##############################################################################################
context = zmq.Context()

#  Socket to talk to server
print ("Connecting to the retreat controller server")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5556")
##############################################################################################

#Initialize DDS
##############################################################################################
dds_probe_port='/dev/ioboards/dds_QO0037'
channel_probe=1
dds_probe=DDSComm(dds_probe_port,channel_probe)


#dds channel for REPUMP
dds_mot_port='/dev/ioboards/dds_QO0019'
channel_mot=0
dds_mot=DDSComm(dds_mot_port,channel_mot)

amplmot=500
amplprobe=140
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

def getCount(miniusb,channel=0,average=10,c=0):
    counts=[]
    for i in range(average):
        counts.append(miniusb.get_counts(channel))
    average_count=np.mean(counts)
    max_count=np.max(counts)
    if c==0:
        return average_count
    else:
        return (average_count,max_count)

def return_initial():
    print('Setting the Piezo back to the initial values before the measurement')
    setV(V0x,V0y)
    
##############################################################################################


#initial miniusb counter device
miniusb_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_USB_Counter_Ucnt-QO10-if00'
miniusb=Countercomm(miniusb_port)
miniusb.set_gate_time(30)
#initiate windfreak
wf_port=''
#wf=WindFreakUsb2(wf_port)

##################################  
#Parameters defnition
##################################
#filename


#number of times
numtime=10


#Retrieve current voltage set to PZT as the initial VX0,VY0
socket.send("CheckVolt 5")
V0y=float((socket.recv()).split()[-1])
socket.send("CheckVolt 6")
V0x=float((socket.recv()).split()[-1])
print('Initial Voltage: ',V0x,V0y)
#Scanning
rangeVx=0.05
rangeVy=0.05
stepV=0.01
numStepx=int(rangeVx/stepV)
numStepy=int(rangeVy/stepV)
xgrid = np.arange(-numStepx ,numStepx+1)*stepV
ygrid = np.arange(-numStepy ,numStepy+1)*stepV
print(xgrid)
xscan = []
yscan = []

#########################################






sp.call(['./telegram_report.sh','Cavity','#################################### \\n From Skynet \\n Starting new experiment 3Dmap_alignment \\n '])


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

print('Start the measurement..')
for j in range(numtime):
    Tcount=[]
    for i in range(np.size(xscan)):
        print('Set Vx Vy to: ',xscan[i],yscan[i])
        #print(np.asarray((xscan[i],yscan[i])))

        setV(xscan[i]+V0x,yscan[i]+V0y)
        time.sleep(0.5)
        Tcount.append(getCount(miniusb,average=100))

        print('\n')
        progress_deg=int(np.size(xscan)/(i+1))
    print('Finish '+str(j)+'th iteration')
    print('Saving data...')
    filename='f'+str(j)+'.dat'
    result=np.column_stack((xscan,yscan,Tcount))
    np.savetxt(filename,result,fmt='%1.3f')
    print('Moving to the next iteration')
    print('#############################')

    if (j==5):
        messg='Progress reported: 50% completed'
        sp.call(['./telegram_report.sh','Cavity',messg])
print('Experiment finished')
print('Saving data...')


sp.call([READPROG+" -W -e 'msg Cavity Experiment finished...' "],shell=True)
#Close connections
wf.close()
