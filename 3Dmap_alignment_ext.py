
#Note: Vx should be Vz
import numpy as np
#from pylab import *
#import matplotlib.pyplot as plt
#import matplotlib.mlab as ml
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

dds_mot_port='/dev/ioboards/dds_QO0019'
channel_mot=1
dds_mot=DDSComm(dds_mot_port,channel_mot)

amplmot=600
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

def getCount(miniusb,channel=0,average=10):
    counts=[]
    for i in range(average):
        counts.append(miniusb.get_counts(channel))
    average_count=np.mean(counts)
    return average_count

def getCountMax(miniusb,channel=0,average=10):
    counts=[]
    for i in range(average):
        counts.append(miniusb.get_counts(channel))
    max_count=np.max(counts)
    return max_count
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

#filenam
filename='landscape_ext.dat'


#Parmeters defnition
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








sp.call(['./telegram_report.sh','Cavity','#################################### \\n From Skynet \\n Starting new experiment'])
#employ a rastering scan to possibly reduce hysterisis of PZT
#to generate all Vsteps for rastering scan
# define some grids
for i, yi in enumerate(ygrid):
    xscan.append(xgrid[::(-1)**i]) # reverse when i is odd
    yscan.append(np.ones_like(xgrid) * yi)

# squeeze lists together to vectors
xscan = np.concatenate(xscan)
yscan = np.concatenate(yscan)
Tcount=np.zeros((np.size(xscan),6))
#sending voltage and measurement

print('Start the measurement..')
for i in range(np.size(xscan)):
    print('Set Vx Vy to: ',xscan[i],yscan[i])
    print(np.asarray((xscan[i],yscan[i])))
    
    setV(xscan[i]+V0x,yscan[i]+V0y)
    time.sleep(0.5)

    #Probeoff
    dds_probe.off()

    #MOToff
    dds_mot.off()

    time.sleep(0.5)
    
    #Fmotoff=getcount
    Fmotoff=getCountMax(miniusb)
    Tcount[i,3]=Fmotoff
    print('Fmotoff ',Fmotoff)
    #MOTon
    dds_mot.on(amplmot)
    
    #Fmoton=getcount
    Fmoton=getCountMax(miniusb,average=200)
    Tcount[i,2]=Fmoton
    print('Fmoton: ',Fmoton)
    #Hygience check for atom
    deltaF_tolerance=100
    if (Fmoton-Fmotoff)<=50:
        print('\x1b[6;30;42m' + 'Fail atom check. Exiting...' + '\x1b[0m')
        return_initial()

        messg='Fail atom check at ' + str(i)+ 'th iteration'
        sp.call(['./telegram_report.sh','Cavity',messg])
#	sp.call([READPROG+" -W -e 'msg Cavity Please check and restart measurement' "],shell=True)
        exit()
    
    #Probe ON
    dds_probe.on(amplprobe)

    time.sleep(1)
    
    #Tmoton=getcount
    Tcount[i,4]=getCount(miniusb,average=1000)
    
    #MOT off
    dds_mot.off()

    time.sleep(0.5)
    
    #Tmotoff=getcount
    Tcount[i,5]=getCount(miniusb,average=100)


result=np.column_stack((xscan,yscan,Tcount))
np.savetxt(filename,result,fmt='%1.3f')

sp.call([READPROG+" -W -e 'msg Cavity Experiment finished...' "],shell=True)
#Close connections
wf.close()
