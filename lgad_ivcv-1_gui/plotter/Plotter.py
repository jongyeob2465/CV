import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from matplotlib.offsetbox import AnchoredText
from typing import List, Dict, Any
import matplotlib as mpl


class Plotter:
    def __init__(self, experiment, base_output_dir, **kwargs):

        self.experiment = experiment
        hep.style.use(self.experiment)
        plt.ioff()  # interactive mode off; not to show figures on creation

        plt.rcParams['axes.linewidth'] = 2.0
        plt.rcParams['hatch.linewidth'] = 0.5

        self.rows = 1
        self.cols = 1

        self.fig = None
        self.axs = None
        self.current_axis = None

        self.axis_label_font_size = 15

        self.data = []
        self.data_loc = []
        self.data_kwargs: List[Dict[str, Any]] = []

        # make directory to save plots
        self.base_output_dir = base_output_dir

    def get_n_colors(self, n):
        colors = mpl.cm.tab20(range(n))
        color_list = [color for color in colors]
        return color_list

    def create_subplots(self, rows=1, cols=1, figsize=(8, 8), left=0.1, right=0.95, bottom=0.1, top=0.9,
                        hspace=0.2, wspace=0.2,
                        **gridspec_kw):
        # update self.rows and self.cols
        if rows != self.rows:
            self.rows = rows
        if cols != self.cols:
            self.cols = cols

        self.fig, self.axs = plt.subplots(self.rows,
                                          self.cols,
                                          figsize=figsize,
                                          gridspec_kw=gridspec_kw)
        plt.tight_layout()
        plt.subplots_adjust(left=left, right=right, bottom=bottom, top=top, hspace=hspace, wspace=wspace)

    def set_current_axis(self, location=(0, 0)):
        row, col = location
        if self.rows == 1 and self.cols == 1:
            self.current_axis = self.axs
        elif self.rows == 1 or self.cols == 1:
            if self.rows == 1:
                index = col
            else:
                index = row
            self.current_axis = self.axs[index]
        else:
            self.current_axis = self.axs[row][col]

    def set_axis_label_font_size(self, size):
        self.axis_label_font_size = size

    def get_current_axis(self):
        return self.current_axis

    def add_input_data(self, path, location=(0, 0), **kwargs):
        # read txt file using numpy
        input_data = np.loadtxt(path)
        self.data.append(input_data)
        self.data_loc.append(location)
        self.data_kwargs.append(kwargs)

    def do_get_renderer(self):
        for row in range(self.rows):
            for col in range(self.cols):
                self.set_current_axis((row, col))
                self.current_axis.draw(self.current_axis.figure.canvas.get_renderer())

    def set_experiment_label(self, location=(0, 0), label="", fontsize=20, pad=0):
        # needed to write label after scientific notation

        self.set_current_axis(location)
        is_data = True
        if label == "Simulation":
            is_data = False
            label = ""
        # plt.rcParams['text.usetex'] = False
        hep.cms.label(label,
                      data=is_data,
                      ax=self.current_axis,
                      rlabel='',  # remove energy
                      fontsize=fontsize,
                      loc=0,
                      pad=pad)
        # plt.rcParams['text.usetex'] = True

    def set_y_label(self, label, location=(0, 0)):
        self.set_current_axis(location)
        self.current_axis.set_ylabel(label, fontsize=self.axis_label_font_size)

    def set_x_label(self, label, location=(0, 0)):
        self.set_current_axis(location)
        self.current_axis.set_xlabel(label, fontsize=self.axis_label_font_size)

    def set_y_lim(self, y_lim, location=(0, 0)):
        self.set_current_axis(location)
        y_min, y_max = y_lim
        self.current_axis.set_ylim(ymin=y_min, ymax=y_max)

    def write_text(self, text, location=(0, 0), loc='upper left'):
        at = AnchoredText(text, loc=loc, prop=dict(size=20), frameon=False)
        at.patch.set_boxstyle("round, pad=0., rounding_size=0.2")
        self.set_current_axis(location)
        self.current_axis.add_artist(at)
        # hep.mpl_magic(self.current_axis)

    def draw(self, x_index=0, y_index=1, remove_offset=False, flip_x=False):
        for data_index, this_data in enumerate(self.data):

            if "x_index" in self.data_kwargs[data_index]:
                x_index = self.data_kwargs[data_index]["x_index"]
                self.data_kwargs[data_index].pop("x_index")
            if "y_index" in self.data_kwargs[data_index]:
                y_index = self.data_kwargs[data_index]["y_index"]
                self.data_kwargs[data_index].pop("y_index")
            x = this_data.T[x_index]
            y = this_data.T[y_index]

            if "ratio" in self.data_kwargs[data_index]:
                denominator_index = self.data_kwargs[data_index]["ratio"][0]
                nominator_index = self.data_kwargs[data_index]["ratio"][1]
                y = this_data.T[nominator_index]/this_data.T[denominator_index]
                self.data_kwargs[data_index].pop("ratio")

            if "y_scale" in self.data_kwargs[data_index]:
                y = y * self.data_kwargs[data_index]["y_scale"]
                self.data_kwargs[data_index].pop("y_scale")

            if remove_offset:
                y = y - y[0]
            if flip_x:
                x = -1. * x
            if "flip_y" in self.data_kwargs[data_index]:
                if self.data_kwargs[data_index]["flip_y"]:
                    y = -1. * y
                    self.data_kwargs[data_index].pop("flip_y")

            if "draw_half" in self.data_kwargs[data_index]:
                x = x[:len(x)//2]
                y = y[:len(y)//2]
                self.data_kwargs[data_index].pop("draw_half")
            if "draw_second_half" in self.data_kwargs[data_index]:
                x = x[len(x)//2:]
                y = y[len(y)//2:]
                self.data_kwargs[data_index].pop("draw_second_half")

            row, col = self.data_loc[data_index]
            self.set_current_axis((row, col))
            self.current_axis.errorbar(x, y,
                                       **self.data_kwargs[data_index], )

        # hep.plot.hist_legend(self.current_axis, loc='best')
        # self.current_axis.grid(axis='y')
        # self.current_axis.grid(axis='x')
        # self.current_axis.set_yscale("log")
        # hep.plot.mpl_magic(self.current_axis)

    def show_legend(self, loc='best', **kwargs):

        # loop over axes
        for row in range(self.rows):
            for col in range(self.cols):
                self.set_current_axis((row, col))
                hep.plot.hist_legend(self.current_axis, loc=loc, fontsize=15, **kwargs)

    def save_fig(self, out_name=''):
        out_file_name = out_name

        print(f"save plot... {out_file_name}")
        self.fig.savefig(self.base_output_dir + out_file_name + ".pdf")
        # self.reset()
        plt.close()
