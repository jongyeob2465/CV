# test LCR meter
import os
import numpy as np
import pylab as plt
import pyvisa
import time
import signal
import matplotlib as mp
from util import mkdir, getdate

mp.rcParams.update({'font.size':15})

opathroot = r'C:\LGAD_test\C-V_test' 
#sensorname = r'FBK_USFD3_CMS_2'
#sensorname = r'code test'
sensorname = r'CVtest'
Nmeas = r'test20240826'
Npad = '1'
Ntimes = True
Iteration = int(input("Enter a positive integer for Iteration: "))

V0 = 0 
V1 = -20
npts = 41

V2 = -15
V3 = -30
npts1 = 31

date = getdate()

def CVmeasurement(freq, return_sweep=False):
    rm = pyvisa.ResourceManager()
    rlist = rm.list_resources()
    print (rlist)

    pau = rm.open_resource('GPIB0::22::INSTR')
    lcr = rm.open_resource('GPIB0::6::INSTR')
    lcr.read_termination = '\n'
    lcr.write_termination = '\n'

    print(pau.query("*IDN?"))
    print(lcr.query('*IDN?'))

    pau.write("*RST")
    pau.write("curr:range 2e-4")
    pau.write("INIT")
    pau.write("syst:zch off")
    pau.write("SOUR:VOLT:STAT off")
    pau.write("SOUR:VOLT:RANG 500")
    #pau.write("SOUR:VOLT:ILIM 2.5e-5")
    pau.write("SOUR:VOLT:ILIM 1e-4")
    pau.write("FORM:ELEM READ,UNIT,STAT,VSO")

    lcr.write(":MEAS:NUM-OF-TESTS 1")
    lcr.write(":MEAS:FUNC1 C")
    lcr.write(":MEAS:FUNC2 Z")
    lcr.write(":meas:equ-cct par")
    lcr.write(":MEAS:SPEED fast")
    lcr.write(":MEAS:LEV 0.1")
    lcr.write(":MEAS:V-BIAS 0V")
    lcr.write(f":MEAS:FREQ {freq}")

    def handler(signum, frame):
        print ("User interrupt. Turning off the output ...")
        pau.write(":sour:volt:lev 0")
        pau.write(":sour:volt:stat off")
        lcr.write(":MEAS:BIAS OFF")
        lcr.write(":MEAS:V-BIAS 0V")
        lcr.close()
        print ("WARNING: Please make sure the output is turned off!")

        exit(1)

    signal.signal(signal.SIGINT, handler)

    ## C-V
    Varr = np.linspace(V0, V1, npts)

    if (V2 is not None):
        if (V2 > V1) and (V3 > V1):
            VarrL = Varr[Varr > V2]
            VarrH = Varr[Varr < V3]
            VarrM = np.linspace(V2, V3, npts1)
            Varr = np.concatenate([VarrL, VarrM, VarrH])

    print (Varr)

    if return_sweep:
        Varr_return = np.linspace(V1,V0,int(abs(V0-V1)/10 + 1))
        Varr = np.concatenate([Varr, Varr_return])

    Vpau_arr = []
    Ipau_arr = []
    CV_arr = []
    RV_arr = []

    pau.write(":sour:volt 0")
    pau.write(":sour:volt:stat on")
    lcr.write(":MEAS:V-BIAS 0V")
    lcr.write("meas:bias OFF")
    time.sleep(1)

    t0 = time.time()
    for Vdc in Varr:
        if Vdc > 0:
            print ("Warning: positive bias is not allowed. Setting DC voltage to 0.")
            Vdc = 0

        pau.write(f':sour:volt {Vdc}')
        time.sleep(0.01)
        Ipau, stat_pau, Vpau = pau.query(":READ?").split(',')

        Vpau = float(Vpau)
        Ipau = float(Ipau[:-1])
        Vpau_arr.append(Vdc)
        Ipau_arr.append(Ipau)

        if Ntimes and Iteration > 0:
            capacitance_values = []
            r_values = []

            for _ in range(Iteration):
                res = lcr.query('meas:trig?')
                C0, R0 = res.split(',')
                try:
                    C0 = float(C0)
                    R0 = float(R0)
                except:
                    break

                capacitance_values.append(C0)
                r_values.append(R0)
                time.sleep(0.05)  # Pauses for N seconds between iterations        

            Cavg = np.mean(capacitance_values)
            Ravg = np.mean(r_values)
            CV_arr.append(Cavg)
            RV_arr.append(Ravg)
        
        else:
            print("Invalid input.")

        print(round(Vdc, 1), Vpau, Ipau, C0, R0)

    t1 = time.time()
    print(f"* Bias sweep of {npts} samples between {V0} and {V1}")
    print(f"   * Return sweep: {return_sweep}")
    print(f"   * Elapsed time = {t1-t0} s")
    pau.write(":sour:volt 0")
    pau.write(":sour:volt:stat off")
    pau.close()
    lcr.write(":MEAS:BIAS OFF")
    lcr.write(":MEAS:V-BIAS 0V")
    lcr.close()

    opath = os.path.join(opathroot, Nmeas, f"{date}_{sensorname}")
    mkdir(opath)
    fname = f'CV_LCR+PAU_{sensorname}_{date}_{freq}Hz_pad{Npad}'
    ofname = os.path.join(opath, fname)

    i = 0
    while os.path.isfile(ofname+'.txt'):
        fname = f'CV_LCR+PAU_{sensorname}_{date}_{freq}Hz_pad{Npad}_{i}'
        ofname = os.path.join(opath, fname)
        i += 1

    header = 'Vpau(V)\tC(F)\tR(Ohm)\tIpau(A)'

    np.savetxt(ofname+'.txt', np.array([Vpau_arr, CV_arr, RV_arr, Ipau_arr]).T, header=header)
    plot_cv(ofname+'.txt', freq) 
    plt.savefig(ofname+'.png')


def plot_cv(fname, freq=None):
    try:
        V, C, R = np.genfromtxt(fname).T
    except:
        V, C, R, I = np.genfromtxt(fname).T
    fig, ax1 = plt.subplots()

    if (V[1] < 0):
        V = -1 * V
    
    ax1.plot(V, C*1e9, 'x-', color='tab:blue', markersize=5, linewidth=0.5, label="$C$")
    ax1.set_xlabel('Bias (V)')
    ax1.set_ylabel('C (nF)', color='tab:blue')
    ax2 = ax1.twinx()
    ax2.plot(V, R, 'x-', color='tab:red')
    ax2.set_ylabel('R (Ohm)', color='tab:red')
    #ax2.set_yscale('log')
    ax3 = ax1.twinx()
    ax3.plot(V, 1/(C)**2, 'x-', color='tab:green', markersize=5, linewidth = 0.5, label="$1/C^2$")
    ax3.set_ylabel('$1/C^2 ($F$^{-2})$', color='tab:green')
    #ax3.set_yscale('log')

    fig.tight_layout()


def cvtest():
    freq = int(1e3)
    print("frequency [Hz] :", freq)

    return_sweep = True
    CVmeasurement(freq, return_sweep)
    #CVmeasurement(100, return_sweep)
    plt.show()
    return 


if __name__=='__main__':
    cvtest()

    plt.show()