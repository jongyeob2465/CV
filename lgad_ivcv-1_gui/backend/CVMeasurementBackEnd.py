from drivers.Keithley6487 import Keithley6487
from drivers.WayneKerr4300 import WayneKerr4300

import os
import sys
import signal
import numpy as np
import time
from util import make_unique_name
from util import BaseThread
from backend.MeasurementBackEnd import MeasurementBackend
import matplotlib.pyplot as plt


CURRENT_COMPLIANCE = 10e-6


class CVMeasurementBackend(MeasurementBackend):
    def __init__(self, pau_visa_resource_name=None, lcr_visa_resource_name=None, sensor_name=None):
        super(CVMeasurementBackend, self).__init__()
        self.pau = Keithley6487()
        self.lcr = WayneKerr4300()

        self.sensor_name = sensor_name
        self.lcr_visa_resource_name = lcr_visa_resource_name
        self.pau_visa_resource_name = pau_visa_resource_name
        self.initial_voltage = 0
        self.final_voltage = -60
        self.right_end_voltage_for_steep_curve = -40  # -15, -40 (according to gain layer design)
        self.left_end_voltage_for_steep_curve = -50  # -25, -50
        self.voltage_step = 1 
        self.data_points = -1
        self.ac_level = 0.1
        self.frequency = 1000
        self.pad_number = 1
        self.return_sweep = True
        self.live_plot = True

        self.x_axis_label = 'Bias Voltage (V)'
        self.y_axis_label = 'Capacitance (F)'

        self.out_txt_header = 'Vpau(V)\tC(F)\tR(Ohm)\tIpau(A)'
        self.base_path += r'\C-V_test'

    def initialize_measurement(self, lcr_visa_resource_name, pau_visa_resource_name, sensor_name):

        self.sensor_name = sensor_name
        self.lcr_visa_resource_name = lcr_visa_resource_name
        self.pau_visa_resource_name = pau_visa_resource_name
        self.data_points = -1

        self.measurement_arr.clear()
        self.output_arr.clear()

        self._make_out_dir()

        self.lcr.open(self.lcr_visa_resource_name)
        self.lcr.initialize()
        self.lcr.set_dc_voltage(0)

        self.pau.open(self.pau_visa_resource_name)
        self.pau.initialize_full()

        # self.lcr.get_idn()
        # self.pau.get_idn()
        self.resources_closed = False

    def set_measurement_options(self, initial_voltage, final_voltage, voltage_step,
                                ac_level, frequency, return_sweep, pad_number, live_plot):

        self.initial_voltage = initial_voltage
        self.final_voltage = final_voltage
        self.voltage_step = voltage_step
        self.ac_level = ac_level
        self.frequency = frequency
        self.return_sweep = return_sweep
        self.live_plot = live_plot
        self.pad_number = pad_number

    def _safe_escaper(self):
        print("User interrupt... Turning off the output ...")
        self.pau.set_voltage(0)
        self.pau.set_output('OFF')
        self.pau.close()
        self.lcr.set_output('OFF')
        self.lcr.set_dc_voltage(0)
        self.lcr.close()
        self.resources_closed = True
        print("WARNING: Please make sure the output is turned off!")
        # exit(1)

    def _make_voltage_array(self, initial_voltage, final_voltage, initial_call=True):
        # left_end_voltage, right_end_voltage
        voltage_step = self.voltage_step 
        decreasing_order = True
        if initial_voltage > final_voltage:
            left_end_voltage = final_voltage
            right_end_voltage = initial_voltage
            voltage_step = voltage_step * -1
        else:
            left_end_voltage = initial_voltage
            right_end_voltage = final_voltage
            decreasing_order = False

        self.voltage_array = np.arange(initial_voltage, final_voltage, voltage_step)
        if self.voltage_array[-1] != final_voltage:
            self.voltage_array = np.append(self.voltage_array, [final_voltage])

        self._add_voltage_array_for_steep_curve(right_end_voltage, left_end_voltage, decreasing_order)

        if initial_call and self.return_sweep:
            self.voltage_array = np.concatenate([self.voltage_array, self.voltage_array[::-1]]) 
            self.data_index_to_draw = 0

        self.n_measurement_points = len(self.voltage_array)
        self.n_data_drawn = 0

    def _add_voltage_array_for_steep_curve(self, right_end_voltage, left_end_voltage, decreasing_order=True):
        
        # make array for steep curve region using np.union1d(x, y)
        if self.right_end_voltage_for_steep_curve is not None and self.left_end_voltage_for_steep_curve is not None:
            # check if the range for steep region is inside the original range
            if left_end_voltage < self.left_end_voltage_for_steep_curve and right_end_voltage > self.right_end_voltage_for_steep_curve:
                voltage_step_for_steep_curve = np.arange(
                        self.left_end_voltage_for_steep_curve, 
                        self.right_end_voltage_for_steep_curve, 
                        self.voltage_step/2.)

                if decreasing_order: 
                    # arrange decreading order
                    self.voltage_array = np.union1d(self.voltage_array, voltage_step_for_steep_curve)[::-1]
                else:
                    # arrange increasing order
                    self.voltage_array = np.union1d(self.voltage_array, voltage_step_for_steep_curve)

    def _update_measurement_array(self, voltage, index, is_forced_return=False):

        if voltage > 0:
            print("Warning: positive bias is not allowed. Set DC voltage to 0.")
            voltage = 0
        self.pau.set_voltage(voltage)
        try:
            current_pau, stat_pau, voltage_pau = self.pau.read().split(',')
        except Exception as exception:
            print(type(exception).__name__)
            sys.exit(0)

        voltage_pau = float(voltage_pau)
        current_pau = float(current_pau[:-1])

        res = self.lcr.read_lcr()
        capacitance, resistance = self.lcr.read_lcr().split(',')
        try:
            capacitance = float(capacitance)
            resistance = float(resistance)
        except Exception as exception:
            print("error in _measure()", type(exception).__name__)

        # print(voltage_pau, capacitance, resistance, current_pau)
        self.measurement_arr.append([voltage_pau, capacitance, resistance, current_pau])
        self.output_arr.append([voltage_pau, capacitance])
        self.set_status_str(index, is_forced_return)

    def start_measurement(self):
        self.pau.set_current_limit(CURRENT_COMPLIANCE)
        # signal.signal(signal.SIGINT, self._safe_escaper)

        self._make_voltage_array(self.initial_voltage, self.final_voltage)

        self.pau.set_voltage(0)
        self.pau.set_output('ON')
        self.lcr.set_output('ON')
        self.lcr.set_level(self.ac_level)
        self.lcr.set_freq(self.frequency)
        time.sleep(1)

        self.event.clear()
        # do measurement in a thread, when finished save_results method called as callback
        self.measurement_thread = BaseThread(target=self._measure,
                                             callback=self.save_results)
        self.measurement_thread.start()

    def stop_measurement(self):
        self.event.set()
        # self.measurement_thread.join()

    def save_cv_plot(self, out_file_name):
        measurement_arr_trans = np.array(self.measurement_arr).T
        v = measurement_arr_trans[0]
        c = measurement_arr_trans[1]
        r = measurement_arr_trans[2]
        # i = measurement_arr_trans[3]
        fig = plt.Figure()
        ax = fig.add_subplot()

        if v[1] < 0:
            v = -1 * v

        ax.plot(v, c * 1e9, 'x-', color='tab:blue', markersize=5, linewidth=0.5, label="$C$")
        ax.set_xlabel('Bias (V)')
        ax.set_ylabel('C (nF)', color='tab:blue')

        ax2 = ax.twinx()
        ax2.plot(v, r, 'x-', color='tab:red')
        ax2.set_ylabel('R (Ohm)', color='tab:red')
        ax2.set_yscale('log')

        ax3 = ax.twinx()
        ax3.plot(v, 1 / (c) ** 2, 'x-', color='tab:green', markersize=5, linewidth=0.5, label="$1/C^2$")
        ax3.set_ylabel('$1/C^2 ($F$^{-2})$', color='tab:green')
        ax3.set_yscale('log')
        fig.tight_layout()

        fig.savefig(out_file_name)
        plt.close()

    def save_results(self):
        if self.resources_closed is False:
            # TODO use verbose level
            if (self.right_end_voltage_for_steep_curve is not None) and (self.left_end_voltage_for_steep_curve is not None):
                print(f"   * Bias sweep of {self.n_measurement_points} meas between {self.initial_voltage} "
                      f"and {self.final_voltage} "
                      f"with {self.n_measurement_points} meas "
                      f"between {self.right_end_voltage_for_steep_curve} and {self.left_end_voltage_for_steep_curve}")
            else:
                print(f"   * Bias sweep of {self.n_measurement_points} meas "
                      f"between {self.initial_voltage} and {self.final_voltage} ")
            print(f"   * Return sweep: {self.return_sweep}")

            self.pau.set_output('OFF')
            self.pau.close()
            self.lcr.set_output('OFF')
            self.lcr.set_dc_voltage(0)
            self.lcr.close()
            self.resources_closed = True

            # file_name = (f'CV_LCR+PAU_{self.sensor_name}_{self.date}_{self.initial_voltage}_{self.final_voltage}_'
            #              f'{self.frequency}Hz_pad{self.pad_number}')
            # out_file_name = os.path.join(self.out_dir_path, file_name)
            # out_file_name = make_unique_name(out_file_name)

            file_name = self.make_out_file_name()
            out_file_name = self.get_unique_file_path(file_name)

            np.savetxt(out_file_name + '.txt', self.measurement_arr, header=self.out_txt_header)
            self.save_cv_plot(out_file_name + '.png')
