import os,sys
import h5py
from pylab import *
from matplotlib.ticker import MaxNLocator, NullFormatter
from matplotlib.figure import SubplotParams

def decompose_bitfield(intarray,nbits):
    """converts a single array of unsigned ints into a 2D array
    (len(intarray) x nbits) of ones and zeros"""
    bitarray = zeros((len(intarray),nbits),dtype=int32)
    for i in range(nbits):
        bitarray[:,i] = (intarray & (1 << i)) >> i
    return bitarray

def discretise(t,y,stop_time):
    tnew = zeros((len(t),2))
    ynew = zeros((len(y),2))

    tnew[:,0] = t[:]
    tnew[:-1,1] = t[1:]
    tnew= tnew.flatten()
    tnew[-1] = stop_time

    ynew[:,0] = y[:]
    ynew[:,1] = y[:]
    ynew= ynew.flatten()[:]
    return tnew, ynew
    
def open_hdf5_file():
    try:
        assert len(sys.argv) > 1
        hdf5_filename = sys.argv[-1]
    except:
        sys.stderr.write('ERROR: No hdf5 file provided as a command line argument. Stopping.\n')
        sys.exit(1)
    if not os.path.exists(hdf5_filename):
        sys.stderr.write('ERROR: Provided hdf5 filename %s doesn\'t exist. Stopping.\n'%hdf5_filename)
        sys.exit(1)
    try:
        hdf5_file = h5py.File(hdf5_filename)
    except:
        sys.stderr.write('ERROR: Couldn\'t open %s for reading. '%hdf5_filename +
                         'Check it is a valid hdf5 file.\n')
        sys.exit(1) 
    return hdf5_file

def parse_connection_table():
    connection_table = hdf5_file['/connection table']
    # For looking up the parent of a device if you know its name:
    parent_dict = [(line['name'],line['parent']) for line in connection_table]
    # For looking up the connection of a device if you know its name:
    connection_dict = [(line['name'],line['connected to']) for line in connection_table]
    # For looking up the name of a device if you know its parent and connection:
    name_dict = [((line['parent'],line['connected to']),line['name']) for line in connection_table]
    parent_dict = dict(parent_dict)
    connection_dict = dict(connection_dict)
    name_dict = dict(name_dict)
    return parent_dict, connection_dict, name_dict
        
def get_clock(device_name):
    ancestry = [device_name]
    # Keep going up the family tree til we hit 'None'. The device whose
    # parent is 'None' is the one we're interested in. It's clock is
    # our devices clock.
    while device_name != 'None':
        device_name = parent_lookup[device_name]
        ancestry.append(device_name)
    clocking_device = ancestry[-2]
    clock_type = connection_lookup[ancestry[-3]]
    clock_type = {'fast clock':'FAST_CLOCK','slow_clock':'SLOW_CLOCK'}[clock_type]
    clock_array = hdf5_file['devices'][clocking_device][clock_type]
    return clock_array
    
def plot_ni_pcie_6363(devicename):
    clock = get_clock(device_name)
    device_group = hdf5_file['devices'][device_name]
    analog_outs = device_group['ANALOG_OUTS']
    digital_outs = device_group['DIGITAL_OUTS']
    acquisitions = device_group['ACQUISITIONS']
    analog_channels = device_group.attrs['analog_out_channels']
    analog_channels = [channel.split('/')[1] for channel in analog_channels.split(',')]
    for i, chan in enumerate(analog_channels):
        data = analog_outs[:,i]
        name = name_lookup[devicename, chan]
        t,y = discretise(clock,data,clock[-1])
        to_plot.append({'name':name, 'times':t, 'data':y,'device':devicename,'connection':chan})
    digital_bits = decompose_bitfield(digital_outs[:],32)
    for i in range(32):
        connection = (devicename,'port0/line%d'%i)
        if connection in name_lookup:
            data = digital_bits[:,i]
            t,y = discretise(clock,data,clock[-1])
            name = name_lookup[connection]
            to_plot.append({'name':name, 'times':t, 'data':y,'device':devicename,'connection':connection})

plotting_functions = {'ni_pcie_6363':plot_ni_pcie_6363}
#                      'ni_pci_6733':plot_ni_pci_6733,
#                      'novatechdds9m':plot_novatechdds9m,
#                      'pulseblaster':plot_pulseblaster} 
                      

hdf5_file = open_hdf5_file()
parent_lookup, connection_lookup, name_lookup = parse_connection_table()
to_plot = []
for device_name in hdf5_file['/devices']:
    device_prefix = '_'.join(device_name.split('_')[:-1])
    if not device_prefix == 'ni_pcie_6363':
        continue
    plotting_functions[device_prefix](device_name)

params = SubplotParams(hspace=0)
figure(subplotpars = params)
for i, line in enumerate(to_plot):
    subplot(len(to_plot),1,i+1)
    plot(line['times'],line['data'])
    gca().yaxis.set_major_locator(MaxNLocator(steps=[1,2,3,4,5,6,7,8,9,10], prune = 'both'))
    if i < len(to_plot)-1:
        gca().xaxis.set_major_formatter(NullFormatter())
    else:
        xlabel('Time (seconds)')
    ylabel(line['name'])
    NullFormatter
    
    grid(True)
show()

