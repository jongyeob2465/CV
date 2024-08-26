from backend.IVMeasurementBackEnd import IVMeasurementBackend
from frontend.MeasurementGUI import MeasurementGUI

# FIXME use first time setup to set ID for devices
SMU_ID = "24"
PAU_ID = "MODEL 6487"


class IVMeasurementGUI(MeasurementGUI):

    def __init__(self, combo_box_smu, combo_box_pau,
                 line_edit_sensor_name, combo_box_pad_num,  line_edit_initial_voltage, line_edit_final_voltage,
                 line_edit_voltage_step, line_edit_current_compliance,
                 check_box_return_sweep, check_box_live_plot,
                 button_measure, label_status):

        super().__init__(line_edit_sensor_name, combo_box_pad_num, line_edit_initial_voltage, line_edit_final_voltage,
                         line_edit_voltage_step, check_box_return_sweep, check_box_live_plot,
                         button_measure, label_status)

        # Widgets
        self.combo_box_smu = combo_box_smu
        self.combo_box_pau = combo_box_pau

        self.button_measure.clicked.connect(self.control_measurement)

        # IV specific options
        self.line_edit_current_compliance = line_edit_current_compliance

        self.measurement = IVMeasurementBackend()
        self.draw_extra_point = True

    def set_combo_box_items(self, items):
        self.combo_box_smu.addItems(items)
        self.combo_box_pau.addItems(items)

    def set_current_compliance(self, current):
        self.line_edit_current_compliance.setText(str(current))

    def set(self, resource_map, sensor_name, initial_voltage, final_voltage, voltage_step,
            current_compliance, live_plot, return_sweep):

        self.resource_map = resource_map
        idn_list = [*self.resource_map.keys()]
        self.set_combo_box_items(idn_list)
        try:
            index_smu = idn_list.index(SMU_ID)
            index_pau = idn_list.index(PAU_ID)
            self.combo_box_smu.setCurrentIndex(index_smu)
            self.combo_box_pau.setCurrentIndex(index_pau)
        except ValueError as e:
            print("Check", e)

        self.set_sensor_name(sensor_name)
        self.set_initial_voltage(initial_voltage)
        self.set_final_voltage(final_voltage)
        self.set_voltage_step(voltage_step)
        self.set_current_compliance(current_compliance)
        self.set_live_plot(live_plot)
        self.set_return_sweep(return_sweep)

    def get_smu_visa_resource_name(self):
        idn = self.combo_box_smu.currentText()
        return self.resource_map[idn]

    def get_pau_visa_resource_name(self):
        idn = self.combo_box_pau.currentText()
        return self.resource_map[idn]

    def get_current_compliance(self):
        number_str = self.line_edit_current_compliance.text()
        exponent = int(number_str.split('e')[1])
        compliance = pow(10, exponent)
        return compliance

    def get(self):
        smu = self.get_smu_visa_resource_name()
        pau = self.get_pau_visa_resource_name()
        sensor_name = self.get_sensor_name()
        initial_voltage = self.get_initial_voltage()
        final_voltage = self.get_final_voltage()
        step = self.get_voltage_step()
        compliance = self.get_current_compliance()
        live_plot = self.get_live_plot()
        return_sweep = self.get_return_sweep()

        return (smu, pau, sensor_name, initial_voltage, final_voltage, step,
                compliance, return_sweep, live_plot)

    def init_measurement(self):
        self.measurement.initialize_measurement(smu_visa_resource_name=self.get_smu_visa_resource_name(), 
                pau_visa_resource_name=self.get_pau_visa_resource_name(),
                sensor_name=self.get_sensor_name())

    def set_measurement_options(self):
        self.measurement.set_measurement_options(initial_voltage=0, final_voltage=self.get_final_voltage(),
                                                 voltage_step=self.get_voltage_step(),
                                                 current_compliance=self.get_current_compliance(),
                                                 return_sweep=self.get_return_sweep(),
                                                 pad_number=self.get_pad_number(), live_plot=self.get_live_plot())
