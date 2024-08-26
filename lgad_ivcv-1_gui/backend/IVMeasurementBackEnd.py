from typing import Tuple, Any

from drivers.Keithley2400 import Keithley2400
from drivers.Keithley6487 import Keithley6487
import numpy as np
import time
from util import BaseThread
from backend.MeasurementBackEnd import MeasurementBackend


class IVMeasurementBackend(MeasurementBackend):
    def __init__(self, smu_visa_resource_name=None, pau_visa_resource_name=None, sensor_name=None):
        super(IVMeasurementBackend, self).__init__()
        self.smu = Keithley2400()
        self.pau = Keithley6487()

        self.sensor_name = sensor_name
        self.smu_visa_resouce_name = smu_visa_resource_name
        self.pau_visa_resouce_name = pau_visa_resource_name
        self.initial_voltage = 0
        self.final_voltage = -250
        self.voltage_step = 1  # TODO do not allow too big voltage_step such as 100 V
        self.data_points = -1
        self.pad_number = 1
        self.return_sweep = True
        self.live_plot = True
        self.current_compliance = 1e-5

        self.x_axis_label = 'Bias Voltage (V)'
        self.y_axis_label = 'Current (I)'

        self.out_txt_header = 'Vsmu(V)\tIsmu(A)\tIpau(A)'
        self.base_path += r'\I-V_test'

    def initialize_measurement(self, smu_visa_resource_name, pau_visa_resource_name, sensor_name):

        self.sensor_name = sensor_name
        self.smu_visa_resouce_name = smu_visa_resource_name
        self.pau_visa_resouce_name = pau_visa_resource_name

        self.measurement_arr.clear()
        self.output_arr.clear()
        self.data_points = -1
        self._make_out_dir()

        self.smu.open(self.smu_visa_resouce_name)
        self.smu.initialize()
        self.smu.set_voltage(0)
        self.smu.set_voltage_range(200)

        self.pau.open(self.pau_visa_resouce_name)
        self.pau.initialize()

        # self.smu.get_idn()
        # self.pau.get_idn()
        self.resources_closed = False

    def set_measurement_options(self, initial_voltage, final_voltage, voltage_step,
                                current_compliance, return_sweep, pad_number, live_plot):
        self.initial_voltage = initial_voltage
        self.final_voltage = final_voltage
        self.voltage_step = voltage_step
        self.current_compliance = current_compliance
        self.return_sweep = return_sweep
        self.live_plot = live_plot
        self.pad_number = pad_number

    def _safe_escaper(self):
        print("User interrupt...")
        self.smu.set_voltage(0)
        self.smu.set_output('off')
        self.smu.close()
        self.pau.close()
        self.resources_closed = True
        print("WARNING: Please make sure the output is turned off!")
        # exit(1)

    def _make_voltage_array(self, initial_voltage, final_voltage, initial_call=True):
        voltage_step = self.voltage_step
        if initial_voltage > final_voltage:
            voltage_step = voltage_step * -1

        self.voltage_array = np.arange(initial_voltage, final_voltage, voltage_step)
        if self.voltage_array[-1] != final_voltage:
            self.voltage_array = np.append(self.voltage_array, [final_voltage])

        # append return sweep voltages only for the initial array creation
        if initial_call and self.return_sweep:
            self.voltage_array = np.concatenate([self.voltage_array, self.voltage_array[::-1]])
            self.data_index_to_draw = 0  # index to draw of self.output_arr 

        self.n_measurement_points = len(self.voltage_array)
        self.n_data_drawn = 0

    def _update_measurement_array(self, voltage, index, is_forced_return=False):
        self.smu.set_voltage(voltage)
        voltage_smu, current_smu = self.smu.read().split(',')
        current_pau, _, _ = self.pau.read().split(',')
        voltage_smu = float(voltage_smu)
        current_smu = float(current_smu)
        current_pau = float(current_pau[:-1])
        # print(voltage, voltage_smu, current_smu, current_pau)  # TODO use verbose level

        self.measurement_arr.append([voltage, voltage_smu, current_smu, current_pau])
        self.output_arr.append([voltage, current_pau, current_smu])
        # self.output_arr.append([voltage, current_smu])
        self.set_status_str(index, is_forced_return)

    def start_measurement(self):
        self.smu.set_current_limit(self.current_compliance)
        # signal.signal(signal.SIGINT, self._safe_escaper)

        self._make_voltage_array(self.initial_voltage, self.final_voltage)

        self.smu.set_voltage(0)
        self.smu.set_output('on')
        time.sleep(1)

        self.event.clear()
        self.measurement_thread = BaseThread(target=self._measure,
                                             callback=self.save_results)
        self.measurement_thread.start()

    def stop_measurement(self):
        self.event.set()  # set internal flag as true
        # self.measurement_thread.join()

    def save_results(self):
        if self.resources_closed is False:

            self.smu.set_voltage(0)
            self.smu.set_output('off')
            self.smu.close()
            self.pau.close()
            self.resources_closed = True

            # file_name = (f'IV_SMU+PAU_{self.sensor_name}_{self.date}_{self.initial_voltage}_{self.final_voltage}'
            #              f'_pad{self.pad_number}')
            # parse sensor_name make_file_name()
            file_name = self.make_out_file_name()
            # out_file_name = os.path.join(self.out_dir_path, file_name)
            # out_file_name = make_unique_name(out_file_name)
            out_file_name = self.get_unique_file_path(file_name)

            np.savetxt(out_file_name + '.txt', self.measurement_arr, header=self.out_txt_header)
            self.save_as_plot(out_file_name + '.png')
