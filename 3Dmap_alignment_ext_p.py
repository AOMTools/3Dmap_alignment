#Note: Vx should be Vz
#modify 3Dmap_alignment_ext.py for Transmission of 810 monitor
#modify 3Dmap_alignment_ext_2.py for Transmission of 810 monitor and lock power 810
import numpy as np
from Counter import Countercomm
from CQTdevices import *
import time
import zmq
from sys import exit
import subprocess as sp


#filename

filename='landscape_ext_810_c2.dat'

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

dds810_port='/dev/ioboards/dds_QO0062'
channel_810=0
dds_810=DDSComm(dds810_port,channel_810)

init_power=600

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

def getPower(analogIO,channel=0,average=100):
    #Get the P810 transmission power on photodetector
    power=np.zeros(100)
    for i in range(average):
        power[i]=analogIO.get_voltage(channel)
    return np.mean(power)

def power_correct(p,dds,analogIO,tolerance=0.03,k1=50):
    #To correct for the power of 810
    #p is the measured power
    #target_power is the reference power to get
    #ps is the set RF power
    #dds is the dds control 810AOM
    ps=init_power
    max_power=800
    cf=True
    pac=0
    target_power=0.35
    setpower_tolerance=target_power*tolerance

    #start at init_power
    dds.set_power(int(init_power))

    if cf==True:
        num_turn=0
        while( (p<(target_power-setpower_tolerance)) or (p>(target_power+setpower_tolerance)) ):
            deltap=(target_power-p)
            e=deltap
            deltaps=k1*e
            ps=ps+deltaps
            print('delp:',str(deltap))
            print('step:',str(deltaps))
            print('Powerset:',ps)

            #to control number of correct steps and avoid excess rf power to aom
            num_turn=num_turn+1
            if ((ps>max_power) or (ps<0) or (num_turn>300)):
                print('Exceed RF Power or number of correction steps')
                break

            #setting rf power ps to aom
            dds.set_power(int(ps))
            time.sleep(0.1)
            #setpower_track.append(ps)
            p=getPower(analogIO)
            print(p)


        #measure T8100 again after correcting
        pac=getPower(analogIO)
        print('Power after correcting : ',pac)
        print('RF power set for the correction : ',ps)
        return (pac)


def return_initial():
    print('Setting the Piezo back to the initial values before the measurement')
    setV(V0x,V0y)
    print('Setting rf power to 810AOM back to originial values')
    dds_810.set_power(init_power)


##############################################################################################


#initial miniusb counter device
miniusb_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_USB_Counter_Ucnt-QO10-if00'
miniusb=Countercomm(miniusb_port)
miniusb.set_gate_time(30)


#initiate analogI0
analogIO_port='/dev/serial/by-id/usb-Centre_for_Quantum_Technologies_Analog_Mini_IO_Unit_MIO-QO13-if00'
analogIO=AnalogComm(analogIO_port)





#Parmeters defnition
#Retrieve current voltage set to PZT as the initial VX0,VY0
socket.send("CheckVolt 5")
V0y=float((socket.recv()).split()[-1])
socket.send("CheckVolt 6")
V0x=float((socket.recv()).split()[-1])
print('Initial Voltage: ',V0x,V0y)
#Scanning
rangeVx=0.09
rangeVy=0.09
stepV=0.03
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
Tcount=np.zeros((np.size(xscan),8))
#sending voltage and measurement
def start():
    print('Start the measurement...')
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
        if (i%3)==0:
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


        #P810 measurement and power correction
        p=getPower(analogIO)
        Tcount[i,6]=p
        print('Start correcting power')
        pac=power_correct(p,dds_810,analogIO)
        Tcount[i,7]=pac
        #power correction

        #Tmoton=getcount
        Tcount[i,4]=getCount(miniusb,average=500)

        #MOT off
        dds_mot.off()

        time.sleep(0.5)

        #Tmotoff=getcount
        Tcount[i,5]=getCount(miniusb,average=100)



        print('Tmoton, Tmotoff ',Tcount[i,4],Tcount[i,5])
        print('\n')
        print('Printing P810')
        print(Tcount[:,6])
        print('Printing P810 after correcting')
        print(Tcount[:,7])
        '''
        progress_deg=((np.size(xscan)+1)/(i+1))
        if (progress_deg==2):
            messg='Progress reported: 50% completed'
            sp.call(['./telegram_report.sh','Cavity',messg])
        '''
    print('Experiment finished')
    print('Saving data...')
    result=np.column_stack((xscan,yscan,Tcount))
    np.savetxt(filename,result,fmt='%1.3f')

    sp.call([READPROG+" -W -e 'msg Cavity Experiment finished...' "],shell=True)

    return_initial()

try:
    start()
except KeyboardInterrupt:
    print('Abruptly shutting down the program')
    print('Pos-Party Cleaning up')
    return_initial()
finally:
    print('Some errors')
    return_initial()
    sp.call([READPROG+" -W -e 'msg ALERT THERE ARE ERRORS...' "],shell=True)

#Close connections
#wf.close()
