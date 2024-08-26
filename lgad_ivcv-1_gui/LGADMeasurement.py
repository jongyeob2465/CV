from PyQt5.QtWidgets import QDialog
from frontend.LGADMeasurement_GUI import *

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon

import pyvisa
from enum import Enum

from frontend.IVMeasurementGUI import IVMeasurementGUI
from frontend.CVMeasurementGUI import CVMeasurementGUI
from frontend.SwitchMatrixGUI import SwitchMatrixGUI


class MeasurementType(Enum):
    IV = 0
    CV = 1
    CF = 2


def get_list_of_resources():
    rm = pyvisa.ResourceManager()
    rlist = rm.list_resources()

    return rlist


class LGADMeasurement(QDialog):
    def __init__(self):
        super().__init__()
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.setWindowTitle("LGAD Measurements")

        # connect function for tab change
        self.ui.tabWidget.currentChanged.connect(self._current_tab_changed)

        # TODO check if switch is available
        self.ui.comboBoxSwitch.setEnabled(True)
        # TODO request available switches and show them in the combo box
        self.sw_gui = SwitchMatrixGUI(self.ui.comboBoxSwitch, self.ui.labelSwitchMatrix)

        # initialize GUI for each experiment
        self.iv_gui = IVMeasurementGUI(self.ui.comboBoxSMU, self.ui.comboBoxPAU,
                                       self.ui.lineEditSensorName,
                                       self.ui.comboBoxPadNumber_IV,
                                       self.ui.lineEditInitialVoltage, self.ui.lineEditFinalVoltage,
                                       self.ui.lineEditVoltageStep, self.ui.lineEditCurrentCompliance,
                                       self.ui.checkBoxReturnSweep, self.ui.checkBoxLivePlot,
                                       self.ui.pushButtonStartMeasurement, self.ui.labelStatus)

        self.cv_gui = CVMeasurementGUI(self.ui.comboBoxLCR, self.ui.comboBoxPAU_CV,
                                       self.ui.lineEditSensorName_CV,
                                       self.ui.comboBoxPadNumber_CV,
                                       self.ui.lineEditInitialVoltage_CV, self.ui.lineEditFinalVoltage_CV,
                                       self.ui.lineEditVoltageStep_CV, self.ui.lineEditFrequency_CV,
                                       self.ui.lineEditLevAC,
                                       self.ui.checkBoxReturnSweep_CV, self.ui.checkBoxLivePlot_CV,
                                       self.ui.pushButtonStartMeasurement_CV, self.ui.labelStatus)

        # default measurement
        self.measurement_type = MeasurementType.IV
        # self.resource_list = get_list_of_resources()  # TODO use map_idn_address
        self._set_connected_resource_map()
        self._init_gui_options(MeasurementType.IV)  # set default options
        self._init_gui_options(MeasurementType.CV)
        self.ui.tabWidget.setCurrentIndex(0)

        self.show()

    def _set_connected_resource_map(self):

        rm = pyvisa.ResourceManager()
        visa_resource_names = list(rm.list_resources())
        visa_resource_names[:] = [device_name 
                for device_name in visa_resource_names if not 'ASRL' in device_name]

        self.device_dict = dict()
        for visa_resource_name in visa_resource_names:
            inst = rm.open_resource(visa_resource_name)
            if ('USB' in visa_resource_name) or ('usb' in visa_resource_name):
                inst.read_termination = '\n'
                inst.write_termination = '\n'

            idn = inst.query("*IDN?")  # identification query
            idn = " ".join(idn.split(",")[1:-2]).lstrip()
            print(idn, "mapped to", "VISA resource name,", visa_resource_name)
            self.device_dict[idn] = visa_resource_name
            inst.close()
        print(len(self.device_dict), "devices connected")

    def _init_gui_options(self, measurement_type):

        if measurement_type == MeasurementType.IV:
            self.iv_gui.set(self.device_dict, "FBK", 0, -250, 1,
                            1e-5, True, True)

        elif measurement_type == MeasurementType.CV:
            self.cv_gui.set(self.device_dict, "FBK", 0, -60, 1,
                            1000, 0.1, True, True)
        else:
            print("Unknown measurement type")

    # show options in GUI
    def _current_tab_changed(self):
        current_index = self.ui.tabWidget.currentIndex()
        if current_index == 0:
            self.measurement_type = MeasurementType.IV
            self.ui.labelStatus.setText("IV measurement selected")
        elif current_index == 1:
            self.measurement_type = MeasurementType.CV
            self.ui.labelStatus.setText("CV measurement selected")
        elif current_index == 2:
            self.measurement_type = MeasurementType.CF
            self.ui.labelStatus.setText("CF measurement selected")
        else:
            self.measurement_type = MeasurementType.IV
            print("invalid measurement index, set IV measurement")
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon('images/KCMS.jpeg'))
    w = LGADMeasurement()
    w.show()
    sys.exit(app.exec_())
