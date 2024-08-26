from drivers.gpibbase import GPIBBase
from drivers.Keithley2400 import Keithley2400
from drivers.WayneKerr4300 import WayneKerr4300
from drivers.Keithley6487 import Keithley6487
from drivers.liveplot import FuncAnimationDisposable

import os
import sys
import time
import pathlib
import threading
import numpy as np
import pyvisa
import signal
from matplotlib import animation as ani
import matplotlib as mp
import pylab as plt
from util import mkdir, getdate

mp.rcParams.update({'font.size':15})


def init(pau_addr, lcr_addr):
    global pau, lcr

    #Connect to source meters
    pau = Keithley6487()
    lcr = WayneKerr4300()
    pau.open(pau_addr)
    lcr.open(lcr_addr)

    # Initialize source meters
    pau.initialize()
    pau.set_current_range(2e-5)

    lcr.initialize()
    lcr.set_dc_voltage(0)
    lcr.write(":MEAS:FUNC2 R")    #FIXME

    # Communicate with source meters
    pau.get_idn()
    lcr.get_idn()
    return pau, lcr


def CFmeasurement(pau, lcr, vi, vf, vstep, f0, f1, lev_ac, sensorname, npad, liveplot):
    pau.set_current_limit(10e-6)
#    lcr.read_termination = '\n'     #FIXME
#    lcr.write_termination = '\n'

    # Safe escaper
    def handler(signum, frame):
        print ("User interrupt... Turning off the output ...")
        pau.set_voltage(0)
        pau.set_output('OFF')
        pau.close()
        lcr.set_output('OFF')
        lcr.set_dc_voltage(0)
        lcr.close()
        print ("WARNING: Please make sure the output is turned off!")
        exit(1)
    signal.signal(signal.SIGINT, handler)

    ## C-F
    f0 = 20
    f1 = 1e6
    npts = 101
    freqarr = 10**np.linspace(np.log10(f0), np.log10(f1), npts)

    CF_arr = []
    RF_arr = []

    ## applying bias by increasing from 0
    lcr.set_dc_voltage(0)
    lcr.set_output('ON')
    pau.set_voltage(0)
    pau.set_output('ON')
    time.sleep(1)

    for V in np.linspace(0, Vdc, int(abs(0-Vdc)+1)):
        pau.set_voltage(V)
        time.sleep(0.1)

    pau.write(f":sour:volt {Vdc}")
    time.sleep(0.1)

    f0 = float(lcr.query('meas:freq?'))

    ## frequency sweep
    f1arr = []
    for freq in freqarr:
        lcr.write(f'meas:freq {freq}')
        time.sleep(0.01)
        f1 = float(lcr.query('meas:freq?'))
        f1arr.append(f1)

        res = lcr.query('meas:trig?')
        res = res[:-1]
        C0, R0 = res.split(',')
        C0 = float(C0)
        R0 = float(R0)
        print(f1, C0, R0)
        CF_arr.append(C0)
        RF_arr.append(R0)


    pau.write("sour:volt 0")
    pau.write("sour:volt:stat off")
    lcr.write(f"meas:freq {f0}")
    lcr.write(":MEAS:BIAS OFF")
    lcr.write(":meas:V-bias 0V")
    lcr.close()
    
    opath = os.path.join(opathroot, Nmeas, f'{date}_{sensorname}')
    fname = f"CFtest_{sensorname}_{date}_{Vdc}V"
    mkdir(opath)
    i = 0
    while os.path.isfile(os.path.join(opath, fname)+'.txt'):
        fname = f"CFtest_LCR_PAU_{sensorname}_{date}_{Vdc}V_{i}"
        i+=1

    ofname = os.path.join(opath, fname)
    header = 'Freq(Hz)\tC(F)\tR(GOhm)'
    plt.savetxt(ofname+'.txt', np.array([f1arr, CF_arr, RF_arr]).T, header=header)
    
    plot_cf(ofname+'.txt', Vdc)
    plt.savefig(ofname+'.png')


def plot_cf(fname, Vdc=None):
    freq, C, R = np.genfromtxt(fname).T
    fig, ax1 = plt.subplots()
    
    ax1.semilogx(freq, C*1e9, 'x-', color='tab:blue')
    ax1.set_xlabel('Frequency (Hz)')
    ax1.set_ylabel('C (nF)', color='tab:blue')
    ax2 = ax1.twinx()
    ax2.semilogx(freq, R,'x-', color='tab:red')
    ax2.set_ylabel('R (GOhm)', color='tab:red')

    plt.title(f"Vdc = {Vdc} V")
    fig.tight_layout()
    
    return

def cftest():
    Vdc = -10
    CFmeasurement(Vdc)
    return 

if __name__=='__main__':
    cftest()

    plt.show()
    opathroot = r'C:\LGAD_test\C-F_test'
    sensorname = r'FBK_2022v1_2x2_34_T10'
    pau = rm.open_resource('GPIB0::22::INSTR')
    lcr = rm.open_resource('USB0::0x0B6A::0x5346::21436652::INSTR')
