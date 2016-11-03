
#Note: Vx should be Vz
#modify 3Dmap_alignment_ext.py for Transmission of 810 monitor
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
    #getCount from miniusb apd
    counts=[]
    for i in range(average):
        counts.append(miniusb.get_counts(channel))
    average_count=np.mean(counts)
    max_count=np.max(counts)
    if c==0:
        return average_count
    else:
        return (average_count,max_count)

def getPower(analogI0,channel=0,average=100):
    #Get the P810 transmission power on photodetector
    power=np.zeros(100)
    for i in range(average):
        power[i]=analogI0.get_voltage(channel)
    return np.mean(power)
'''
def power_correct(p,setpower_tolerance,k1=10):
    #To correct for the power of 810
    #p is the measured power
    #target_power is the reference power to get
    #ps
    ps=init_power
    if cf==True:
        while( (p<(target_power-setpower_tolerance)) or (p>(target_power+setpower_tolerance)) ):
            deltap=(target_power-p)
            e=deltap
            deltaps=k1*e
            ps=ps+deltaps
            print('delp:',str(deltap))
            print('step:',str(deltaps))

            print('powerset:',ps)
            dds.set_power(int(ps))
            setpower_track.append(ps)
            value=[]
            time.sleep(0.1)
            for m in range(average):
                power = pm.get_power(wavelength)
                value.append(power)
                time.sleep(5e-2) # delay between asking for next value
            p=np.mean(value)
            powers_track.append(p)
            print(p)
            num_turn=num_turn+1
            if ((ps>max_power) or (ps<0) or (num_turn>300)):
                break
        setpower.append(int(ps))
        value=[]
        for m in range(average):
            power = pm.get_power(wavelength)
            value.append(power)
            time.sleep(5e-2) # delay between asking for next value
        powers_adj.append(np.mean(value))
'''

def return_initial():
    print('Setting the Piezo back to the initial values before the measurement')
    setV(V0x,V0y)


##############################################################################################


#initial miniusb counter device
miniusb_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_USB_Counter_Ucnt-QO10-if00'
miniusb=Countercomm(miniusb_port)
miniusb.set_gate_time(30)


#initiate analogI0
print('initiating analogIO')
analogI0_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_Analog_Mini_IO_Unit_MIO-QO13-if00'
analogI0=AnalogComm(analogI0_port)


#filename
filename='landscape_ext_810_1.dat'


#Parmeters defnition
#Retrieve current voltage set to PZT as the initial VX0,VY0
socket.send("CheckVolt 5")
V0y=float((socket.recv()).split()[-1])
socket.send("CheckVolt 6")
V0x=float((socket.recv()).split()[-1])
print('Initial Voltage: ',V0x,V0y)
#Scanning
rangeVx=0.06
rangeVy=0.06
stepV=0.02
numStepx=int(rangeVx/stepV)
numStepy=int(rangeVy/stepV)
xgrid = np.arange(-numStepx ,numStepx+1)*stepV
ygrid = np.arange(-numStepy ,numStepy+1)*stepV
print(xgrid)
xscan = []
yscan = []








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
Tcount=np.zeros((np.size(xscan),7))
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
    Fmotoff=getCount(miniusb)
    Tcount[i,3]=Fmotoff
    print('Fmotoff ',Fmotoff)

    #MOTon
    dds_mot.on(amplmot)
    (Fmoton,Fmotonmax)=getCount(miniusb,average=300,c=1)
    Tcount[i,2]=Fmoton
    print('Fmoton: ',Fmoton)
    print('Fmoton_max: ',Fmotonmax)


    #Hygience check for atom
    deltaF_tolerance=100
    if (i%2)==0:
        print('Checking atom...')
        if (Fmotonmax-Fmotoff)<=40:
            print('\x1b[6;30;42m' + 'Fail atom check. Exiting...' + '\x1b[0m')
            return_initial()

            messg='Fail atom check at ' + str(i)+ 'th iteration'
            sp.call(['./telegram_report.sh','Cavity',messg])
        #	sp.call([READPROG+" -W -e 'msg Cavity Please check and restart measurement' "],shell=True)
            exit()
        print('Pass the atom check')
        print('Continue with measurement')
    #Probe ON
    dds_probe.on(amplprobe)

    time.sleep(1)

    #Tmoton=getcount
    Tcount[i,4]=getCount(miniusb,average=500)

    #MOT off
    dds_mot.off()

    time.sleep(0.5)

    #Tmotoff=getcount
    Tcount[i,5]=getCount(miniusb,average=100)

    #P810 measurement
    Tcount[i,6]=getPower(analogI0)

    print('Tmoton, Tmotoff ',Tcount[i,4],Tcount[i,5])
    print('\n')
    print('Printing P810')
    print(Tcount[:,6])
    progress_deg=int(np.size(xscan)/(i+1))
    if (progress_deg==2):
        messg='Progress reported: 50% completed'
        sp.call(['./telegram_report.sh','Cavity',messg])
print('Experiment finished')
print('Saving data...')
result=np.column_stack((xscan,yscan,Tcount))
np.savetxt(filename,result,fmt='%1.3f')

sp.call([READPROG+" -W -e 'msg Cavity Experiment finished...' "],shell=True)
#Close connections
wf.close()
