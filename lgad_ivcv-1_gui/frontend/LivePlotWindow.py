from PyQt5.QtWidgets import QWidget, QVBoxLayout
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar


class LivePlotWindow(QWidget):
    def __init__(self, measurement, draw_extra_point=False):
        super().__init__()

        self.xs = None
        self.ys = None
        self.ys_extra = None
        self.draw_extra_point = draw_extra_point

        self._measurement = measurement
        self.x_axis_label = measurement.get_x_axis_label()
        self.y_axis_label = measurement.get_y_axis_label()

        self.axis_extra = None
        self._init_draw()  # create sub-plots and call FuncAnimation()
        self._init_ui()
        self.show()

    def __del__(self):
        plt.close()

    # override figure close event from QWidget
    def close_event(self, event):
        self.close()

    def _init_ui(self):
        vbox = QVBoxLayout()
        vbox.addWidget(self.toolbar)
        vbox.addWidget(self.canvas)
        self.setLayout(vbox)
        # self.setGeometry(400, 300, 400, 600)

    def _init_draw(self):
        # for PyQt embedding
        self.fig = plt.Figure()
        self.axis = self.fig.add_subplot()
        if self.draw_extra_point:
            self.axis_extra = self.axis.twinx()
            # self.axis_extra.clear()
            self.axis_extra.set_ylabel("Total " + self.y_axis_label)

        self.canvas = FigureCanvas(self.fig)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.axis.clear()
        self.axis.set_ylabel(self.y_axis_label)
        self.axis.set_xlabel(self.x_axis_label)


        self.ani = animation.FuncAnimation(fig=self.fig,
                                           func=self.animate,
                                           interval=10,
                                           blit=False,
                                           save_count=100)
        self.canvas.draw()

    def _before_drawing(self):
        if self._measurement.all_data_drawn():
            self.ani.event_source.stop()
            self.close()
        else:
            # expected data type is a list with two values for x and y
            # for IV length == 3, for CV length == 2
            raw_data = self._measurement.get_data_point()
            self.xs = raw_data[0]
            self.ys = raw_data[1]
            if len(raw_data) == 3 and self.draw_extra_point:
                self.ys_extra = raw_data[2]

        return self._measurement.is_return_sweep_started()

    def animate(self, event):
        return_sweep = self._before_drawing()  # update data

        self.axis.grid(True)
        if self.xs is not None and self.ys is not None:

            if return_sweep:
                self.axis.plot(self.xs, self.ys, 'ob', mfc='none')

                if self.ys_extra is not None and self.draw_extra_point:
                    self.axis_extra.plot(self.xs, self.ys_extra, 'ok', ms=2, mfc='none')
            else:
                self.axis.plot(self.xs, self.ys, 'or', mfc='none')

                if self.ys_extra is not None and self.draw_extra_point:
                    self.axis_extra.plot(self.xs, self.ys_extra, 'ok', ms=2)

            '''
            fmt_ys = 'or'
            fmt_ys_extra = 'ok'
            kwargs_ys_extra = {'ms':2}

            if return_sweep:
                fmt_ys = 'ob'
                kwargs_ys_extra = {'ms':2, 'mfc':'none'}

            self.axis.plot(self.xs, self.ys, fmt_ys, mfc='none')
            if self.ys_extra is not None and self.draw_extra_point:
                self.axis_extra.plot(self.xs, self.ys_extra, fmt_ys_extra, **kwargs_ys_extra)
            '''

    def pause(self):
        # self.ani.event_source.stop()
        self.ani.pause()

    def resume(self):
        # self.ani.event_source.start()
        self.ani.resume()

    def close(self):
        self.ani.event_source.stop()
        super().close()
