import argparse
from Plotter import Plotter

parser = argparse.ArgumentParser(description='I-V and C-V plotter.')
parser.add_argument('sensor_name',
                    help='measured sensor_name. used to determine directory and input file name')
parser.add_argument('measurement_date', help='YYYY-MM-DD')
parser.add_argument('pad_name', default='0')
parser.add_argument('measurement_version', default='0')
parser.add_argument('measurement_descr', default='',
                    help='used to determine data file name.')

args = parser.parse_args()

measurement_type = 'I-V_test'
base_input_dir = f'C:/LGAD_test/{measurement_type}/'

# determine directory name and file name
sensor_name = args.sensor_name  # sensor name will be printed in plot
measurement_description = args.measurement_descr  # explain measurement condition
date = args.measurement_date

# determine file name
if measurement_description == '':
    measurement_name = f'{sensor_name}'
else:
    measurement_name = f'{sensor_name}_{measurement_description}'
pad_name = args.pad_name
version = args.measurement_version  # pair file_name_postfix and pad_name

input_dir = base_input_dir + sensor_name + '/'
input_txt_file_name = f'IV_SMU+PAU_{measurement_name}_{date}_pad{pad_name}_v{version}.txt'

plotter = Plotter('CMS', input_dir)

colors = plotter.get_n_colors(6)
kwargs = {"linewidth": 2, "draw_half": True, "y_scale": 1e3}  # common arguments

# options
# draw all data in the current directory
# parse the file name and extract parameters
# draw total/pad/both current

plotter.add_input_data(input_dir + input_txt_file_name,
                       label=f'Pad {pad_name}',
                       y_index=3,
                       color=colors[0],
                       linestyle='--', flip_y=True, **kwargs)
# total current
plotter.add_input_data(input_dir + input_txt_file_name,
                       label='Total',
                       y_index=2,
                       color=colors[0],
                       flip_y=True, **kwargs)

plotter.create_subplots(rows=1, cols=1, figsize=(15, 10), left=0.15)
plotter.draw(remove_offset=False, flip_x=True)

# plotter.do_get_renderer()
plotter.set_experiment_label(location=(0, 0), label=sensor_name, fontsize=20)
plotter.get_current_axis().set_yscale('log')
plotter.show_legend(loc='best', ncol=2)

plotter.set_axis_label_font_size(20)
plotter.set_y_lim((1e-9, 0.9))
plotter.set_current_axis()
plotter.current_axis.grid(axis='y')
plotter.current_axis.grid(axis='x')
plotter.set_y_label("Current [mA]")
plotter.set_x_label("Bias voltage [V]")

plotter.save_fig(out_name=f'IV_{measurement_name}_{date}_pad{pad_name}_v{version}')
