### Python module for the open source RPi-HAUS application ###
### HAUS ###
###### Configured to be run on Debian-Wheezy BST 2014 armv6l GNU/Linux ######
###########/dev/ttyACM*#######

import sys
import glob
import time
import json
import threading
import serial
from threading import Lock
import requests
import getpass
from contextlib import closing

class User(object):
    """
This function is the working head for Raphi. Currently processes based on regular expressesions of the
 /dev/yourarduinousbserialpathhere (from the scanportsmodule).
Returns a string with the serials that fit that specification in the form of a list of tuples (connection first, test buffer last).
The connection returns in it's open state .
    """
    _instances=[]
    serial_locks = {}
    url = "http://ec2-54-148-194-170.us-west-2.compute.amazonaws.com"  # Update this as needed
    primary_key_owners = {}  # {device_id: [(username, devicename), ...],}

    def __init__(self):
        self.send_attempt_number = 0
        ports = _serial_ports()
        if len(self._instances) < 1:
            for serial_path in ports:
                self.serial_locks[serial_path] = Lock()
        self._instances.append(self)
        self.device_locks = {}
        self.named_connections = {}
        self.controllers = {}
        self.monitors = {}
        self.device_metadata = {}
        self.serial_connections = []
        self.delimiters = {}
        self.device_meta_data_field_names = (
            'device_name',
            'device_type',
            'username',
            'timezone',
            'timestamp')

    def stream_forever(self, frequency = 'A'):
        inf = float("inf")
        monitor_threads = []
        try:
            for name, port in self.monitors:
                thread = threading.Thread(target=self.read_monitors_continuously, args = (name, port, inf, frequency))
                thread.daemon = True
                thread.start()
                monitor_thrads.append(thread)
        except:
            for thread in monitor_threads:
                thread.join()

    def pickup_conn(self):
        serial_paths = _serial_ports()
        serial_list = []
        for port in serial_paths:
            try:
                connection = serial.serial_for_url(port, timeout=5)
            except serial.SerialException:
                # the port doesn't really exist or cannot be opened, so
                #  do not add it to the list.
                continue
            serial_list.append(connection)
        self.serial_connections = serial_list
        return serial_list

    def test_ports(self):
        pass

    def read_monitors_continuously(self, name, port, timeout=30, frequency = 'A'):
        start = time.time()
        current_time = start
        while (current_time - start) < timeout:
            ### frequency logic goes here
            if frequency == 'A':
                data_dict = self.read_monitors_to_json(name, port)
                print data_dict
                self._send_to_server(data_dict)
                current_time = time.time()
            elif frequency == 'M':
                ### finds the average values if they're numbers else, take the last value ###
                ### reports the average timestamp ###
                minute_average_dict = self.log_data(60, name, port)
                print minute_average_dict
                self._send_to_server(minute_average_dict)
            elif frequency == 'H':
                ## same for hour ##
                hour_average_dict = self.log_data(3600, name, port)
                print hour_average_dict
                self._send_to_server(hour_average_dict)

    def log_data(self, name, port, seconds):
        ### Please note that the reported timestamp on averaged data is also and average value.
        logs = []
        start = time.time()
        current_time = start
        while current_time - start < seconds:
            log.append(self.read_monitors_to_json(name, port))
            current_time = time.time()
        average_data = {}
        for log in logs:
            for key, val in log['atoms'].iteritems():
                if is_number(val):
                    try:
                        average_data[key] = average_data[key] + val
                    except:
                        average_data[key] = val
                else:
                    ### If it's not a number, the last value is reported
                    average_data[key] = val
        for key, summed_data in average_data.iteritems():
            if is_number(summed_data):
                average_data[key] = summed_data / len(logs)
        return average_data

    # CMGTODO: _ensure_port_is_open should be static function, or in another class
    def _ensure_port_is_open(self, port):
        if not port.isOpen():
            port.open()
        return

    def read_monitors_to_json(self, name, port, timeout = 30):
        ### listening for 30 second timeout for testing ###
        ### if you think your monitors are running slow, check for delays in your arduino sketch ###
        start_time = time.time()
        name_time = start_time

        port_lock = self.device_locks[name]
        # CMGTODO
        # if we can't get a port_lock, it would probably be more
        #  efficient to give up on the current monitor than have
        #  everything else wait for it to become free.
        with port_lock:
            jsonmessage = self.read_raw(name, port)

        now_time = time.time()
        # print name, ' took: ', int(now_time - name_time), 'seconds'
        name_time = now_time
        return jsonmessage


    def _send_to_server(self, jsonmessage):
        self.send_attempt_number += 1
        if (self.send_attempt_number % 10):  # not zero
            return
        # PUT device_metadata['device_id'] into payload
        payload = {}
        payload['timestamp'] = jsonmessage['timestamp']
        print "The atoms thing is:"
        print type(jsonmessage['atoms']), jsonmessage['atoms']
        payload['atoms'] = jsonmessage['atoms']
        dev_id = self.device_metadata[jsonmessage['device_name']]['device_id']
        device_address = "%s/devices/%d/" % (self.url, dev_id)
        response = self.session.post(device_address, json=payload)
        print "Posted data: "
        print response.request
        print response.status_code
        if response.status_code == 500:
            import io
            with io.open('error.html', 'wb') as errorfile:
                errorfile.write(response.content)
        else:
            print response.content

    def ping_controller_atoms(self, name, port):

        self._ensure_port_is_open(port)
        # try:
        #     response = port.write('Okay')
        #     response = port.readline()
        #     print response
        #     if response[0] != 'O' or response[0] != b'#':
        #         raise Exception("Controller is not Okay")
        # except:
        #     print "Controller didn't wake up"
        #     # raise Exception("Controller didn't wake up.")
        port.write('$')
        # response = port.readline()
        # ###this is hardcoded for testing with relay ###
        # print response
        # cleanedresponse = response.rstrip()[1:-1]
        # atom_pairs = cleanedresponse.split(',')
        # atoms = {}
        # for pair in atom_pairs:
        #     try:
        #         key, val = pair.split('=')
        #         atoms[key] = val
        #     except:
        #         print "couldn't split"
        #     print atoms
        atoms = self.read_raw(name, port)['atoms']
        return atoms

    def talk_to_controller(self, state):
        """
Use method like this:
for name, port in me.controllers.iteritems():
    me.talk_to_controller(name, port, 'Relay1', '1')

Relay's must have an '@' before them.
        """
        name = state['device_name']
        port = self.named_connections[name]

        return converse_with_controller(self,
                                        name,
                                        port,
                                        state['atoms'],
                                        ping=True,
                                        sendDollar=True)
        # print name
        # print port
        # jsonmessage = None
        # start_time = time.time()

        # port_lock = self.device_locks[name]
        # with port_lock:
        #     print "has lock"
        #     print "port open"
        #     # try:
        #     #     response = port.write('Okay')
        #     #     response = port.readline()
        #     #     if response[0] != 'O' or response[0] != '#':
        #     #         raise("Controller is not Okay")
        #     # except:
        #     #     raise Exception("Controller didn't wake up.")
        #     current_state = self.ping_controller_atoms(name, port)
        #     self._ensure_port_is_open(port)
        #     atoms = state['atoms']
        #     print current_state
        #     print atoms
        #     for key, val in atoms.iteritems():
        #         if key[0] == '@':
        #             switch_name, switch_number = key.split('_')
        #             if val != current_state[key]:
        #                 print "desired = ", val, " current = ", current_state[key]
        #                 port.write(str(switch_number))

        #     port.write('$')
        #     jsonmessage = self.read_raw(name, port)

        #     # print jsonmessage


        # print 'method took :', int(time.time() - start_time), ' seconds'
        # return jsonmessage

    def converse_with_controller(self, name, port, message=None, ping=False, sendDollar=False):
        response = None

        start_time = time.time()
        port_lock = self.device_locks[name]
        with port_lock:
            if ping:
                current_state = self.ping_controller_atoms(name, port)
            self._ensure_port_is_open(port)
            if type(message) is dict:
                doComma = False
                for key, val in message.iteritems():
                    if key[0] == '@':
                        # if a key begins with '@', that is a signal
                        #  to check the val against the current_state
                        #  and ONLY send the message if they are different
                        switch_name, switch_number = key.split('_')
                        if val != current_state[key]:
                            print "desired = ", val, " current = ", message[key]
                            port.write(str(switch_number))
                    else:
                        # write the dict atoms, separated by commas
                        if doComma:
                            port.write(', ')
                        port.write(key)
                        port.write(':')
                        port.write(val)
                        doComma = True

            elif type(message) is str:
                port.write(message)
            else:
                port.write(str(message))

            if sendDollar:
                port.write('$')
            response = self.read_raw(name, port)
            # print response

        print 'method took :', int(time.time() - start_time), ' seconds'
        return response

    # CMGTODO: without memorized decorator, setup dictionary if seen before
    def _delimiter_factory(self, message, device_name):
        if device_name in self.delimiters:
            return self.delimiters[device_name]

        field_separator = {[',', ';', '\n']}
        keyval_separator = {[':', '=']}
        in_single_quote = False
        in_double_quote = False
        index = 0
        maxlen = len(message)

        while (index < maxlen) and (
              (len(field_separator) > 1) or (len(keyval_separator) > 1)):
            c = message[index]
            if (c == '"') and (not in_single_quote):
                in_double_quote = not in_double_quote
            elif (c == "'") and (not in_double_quote):
                in_single_quote = not in_single_quote
            elif in_single_quote or in_double_quote:
                # if in a quoted string, don't check for separators
                pass
            elif (c in keyval_separator):
                keyval_separator = c
            elif (c in field_separator):
                field_separator = c
            index += 1

        self.delimiters[device_name] = [field_separator, keyval_separator]
        print "In factory: {} has field_separator[{}], keyval_separator[{}]".format(
            device_name,
            field_separator,
            keyval_separator)
        print "Original message: [{}]".format(message)

        return field_separator, keyval_separator

    def _build_json(self, message, device_name):
        try:
            message = message.rstrip()
            contents = {}
            atoms = {}

            field_separator, keyval_separator =\
                self._delimiter_factory(message, device_name)

            key_val_pairs = message.split(field_separator)
            for pair in key_val_pairs:
                try:
                    pair_list = pair.split(keyval_separator)
                    key = pair_list[0].lstrip()
                    val = pair_list[1].lstrip()
                    atoms[key] = val
                except:
                    print 'got exception, pair is:', pair
                    print 'field_separator is [{}]'.format(field_separator)
                    print 'keyval_separator is [{}]'.format(keyval_separator)
                    return None

            meta_data = self.device_metadata[device_name]
            for key in self.device_meta_data_field_names:
                contents[key] = meta_data[key]
            contents['timestamp'] = time.time()
            contents['atoms'] = atoms

            return json.dumps(contents)
        except:
            raise

    def haus_api_put(self):
        pass

    def haus_api_get(self):
        pass

    # read_raw() is a method to pick up reading from the serial port at
    #  a time when we don't know where we are in the stream. The routine
   #  is able to build some atoms, but perhaps not more than that.
    # if timeout, just return

    def read_raw(self, name, port, timeout = 5):
        """ return JSON representation of parsed line from port, possibly parsed partial line """
        #### Should change empty readline to a timeout method.
        ### Method broken! Byte read in is not comparable using =.
        ### VAL acts as a token to know whether the next bytes string is a key or value in the serialized form###
        ## based on continuos bytes with no newline return##
        # The start of line for this test is the '$' for username, and the EOL is '#' #

        # We can start our data structure with any key value pair. A key value pair
        #  starts after a field_separator (comma or semi-colon), or after a new-line
        #  Apparently, there are also some scenarios where this could occur after a
        #  dollar sign. So, if you see any four of these characters, you are probably
        #  just about to start a key value pair. Well, as long as none of these
        #  characters occur in strings.
        # If the string is already read, a potentially slower but more robust
        #  way to read is to use the split and strip methods on the entire line
        key_value_start_set = {b'\n', b',', b';', b'$'}
        fieldsep = {b',', b';', b'\n', b'\r', b'#'}
        keysep = {b':', b'='}
        whitespace_set = {b' ', b'\t'}
        if self.delimiters:
            if self.delimiters[0]:
                fieldsep = self.delimiters[0] + {b'\n', b'#'}
            if self.delimiters[1]:
                keysep = self.delimiters[1]

        atoms = {}
        contents = {}
        self._ensure_port_is_open(port)

        start_time = time.time()
        current = port.read()
        while current not in key_value_start_set:
            print "Looking for key_value_start but found {}".format(current)
            current = port.read()
            print current
            if time.time() - start_time > timeout: return

        done = False
        # try:
        while not done:
            current_key = ''
            current_value = ''

            c = port.read()
            while c in whitespace_set:
                c = port.read()

            while c not in keysep:
                current_key += c
                c = port.read()

            c = port.read()
            while c in whitespace_set:
                c = port.read()

            while c not in fieldsep:
                current_value += c
                c = port.read()

            atoms[current_key] = current_value

            # either of these mark the EOL
            done = c in {b'\n', b'#', b'\r'}
        # except:
        #     print "Cannot read_raw"
        #     raise # Exception("Cannot read_raw")

        # if empty_read_count <= empty_read_limit:
        meta_data = self.device_metadata[name]

        for key in self.device_meta_data_field_names:
            contents[key] = meta_data[key]
        contents['timestamp'] = time.time()
        contents['atoms'] = atoms

        return contents

    ef _continue_adding_devices(self, virtual_connection, current_devices, num_setupdevices):
        if virtual_connection:
            return raw_input("Would you like to set up a device? (y/n)").startswith('y')
        else:
            return current_devices <= num_setupdevices

    def run_setup(self):
        num_totaldevices = len(_serial_ports())

        virtual_connection = (sys.platform.startswith('linux2') and
                              (_serial_ports()[0].startswith('/dev/ttyS')))

        if  virtual_connection:
            setup_preface = """
On a virtual machine, live ports
cannot be enumerated so plug
and play is not supported. If you
would like to run through the
device setup, you'll need to name
your devices as well as know what
port they connect on (usually
either /dev/ttyS0 or /dev/ttyS1)
"""
        else:
            setup_preface = """
There are {} ports available.
If you would like to run through the device
setup (which will require you unplugging your
devices, and naming them one by one as they
connect)
""".format(num_totaldevices)

        answer = raw_input(setup_preface + "Would you like to set up devices? (y/n)")
        if (answer.lower()[0] != 'y'):
            return None

        if virtual_connection:
            num_setupdevices = 0
        else:
            answer = raw_input('Plug all your devices in now to continue, then hit enter:')
            num_totaldevices = len(_serial_ports())
            num_setupdevices = int(raw_input('Found {} devices, how many devices do you want to name? (1-n): '.format(num_totaldevices)))

        username = raw_input("What is the account username for all your devices?: ")
        password = getpass.getpass("Enter your password: ")
        timezone = raw_input("What is your current timezone?: ")

        self.session = requests.Session()
        self.session.auth = (username, password)
        response = self.session.get('%s/devices' % self.url)
        if response.status_code == 200:
            devices = json.loads(response.content)
            print "Your known devices: %s" % \
                ", ".join([device['device_name'] for device in devices])
        else:
            print "HTTP Error retrieving devices: ", response.status_code

        if not virtual_connection:
            print "Unplug them now to continue..."
            ### Take number of devices connected initially and subtract devices to program ###
            starting = num_devices - answer
            while len(_serial_ports()) > (starting):
                time.sleep(1)

        current_devices = 1

        while self._continue_adding_devices(virtual_connection, current_devices, num_setupdevices):
            if not virtual_connection:
                current_ports = _serial_ports()
                print "Now plug in device {}...".format(current_number)
                while len(current_ports) < current_number + starting:
                    time.sleep(1)
                    current_ports = _serial_ports()

                last_port = current_ports.pop()
                if last_port in User.primary_key_owners:  # Maybe put last_port in primary_key_owners and do this automatically
                    print "A device can only have one owner, if you'd like to share data you can do so from the owner's dashboard."
                    break

            # Add logic for permissions here
            known_id = -99

            device_name = raw_input("What would you like to call device {}?: ".format(current_devices))
            device_type = raw_input("Is this device a 'controller' or a 'monitor'?: ")
            baud_rate = raw_input("The default Baud rate is 9600. Set it now if you like, else hit enter: ")
            if virtual_connection:
                last_port = raw_input("What is the path to {}? ".format(device_name))

            timestamp = 'timestamp' # CMGTODO: why is timestamp set to a literal?

            try:
                self.device_locks[device_name] = self.serial_locks[last_port]
            except KeyError:
                self.serial_locks[last_port] = Lock()
                self.device_locks[device_name] = self.serial_locks[last_port]


            metadata = {}
            device_data = []
            device_data.append(device_name)
            device_data.append(device_type)
            device_data.append(username)
            device_data.append(timezone)
            device_data.append(timestamp)
            metadata = dict(zip(self.device_meta_data_field_names, device_data))
            self.device_metadata[device_name] = metadata

            if virtual_connection:
                # pickup_conn() will return all the serial lines that can be
                #  opened, so we have to look for the one that matches the device
                #  path that the user provided
                connection_list = self.pickup_conn()
                last_device_connected = None
                for conn in connection_list:
                    if (conn.port == last_port):
                        last_device_connected = conn
                        break
            else:
                last_device_connected = self.pickup_conn()[-1]

            if not last_device_connected.isOpen():
                print "After self.pickup_conn(), the connection is not open"
                last_device_connected.open()

            # ## This is Arduino protocol ###
            last_device_connected.write('Okay')
            response = last_device_connected.readline()
            if not virtual_connection:
                # on a virtual connection, you cannot distinguish between
                #  really having a connection, or just being tied to a
                #  serial port.
                assert response == 'Okay'

            if device_type == 'monitor':
                atoms = self.read_monitors_to_json(device_name,
                                                   last_device_connected)['atoms']
                atom_identifiers = [name for name in atoms]
            else:
                atoms = self.ping_controller_atoms(device_name,
                                                   last_device_connected)
                atom_identifiers = [name for name in atoms]
            payload = {'device_name': device_name, 'device_type': device_type,
                       'atoms': atom_identifiers}
            if known_id != -99:
                payload['device_id'] = known_id
            print "made it payload"
            response = self.session.post('%s/devices' % self.url, data=payload)

            # JBB: Make this handle server errors gracefully
            if response.status_code in (201, 202):
                print "Device registered with server"
            else:
                print "Problem registering device: HTTPError ",\
                    response.status_code

            response = json.loads(response.content)
            device_id = response['id']
            if device_id in User.primary_key_owners:
                User.primary_key_owners[last_port].append((device_id, username, device_name))
            else:
                User.primary_key_owners[last_port] = [(device_id, username, device_name)]

            self.device_metadata[device_name]['device_id'] = device_id

            if baud_rate != '':
                try:
                    last_device_connected.baud_rate = int(baud_rate)
                except:
                    raise Exception('Could not set that baud rate, check your input and try again.')

            if device_type == 'controller':
                self.controllers[device_name] = last_device_connected
            elif device_type == 'monitor':
                self.monitors[device_name] = last_device_connected

            self.named_connections[device_name] = last_device_connected
            current_number += 1

        current_connections = self.named_connections
        return current_connections


def _serial_ports():
    """Lists serial ports
    :raises EnvironmentError:
    On unsupported or unknown platforms
    :returns:
    A list of available serial ports
    """
    if sys.platform.startswith('win'):
        ports = ['COM' + str(i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ### The second is for xbee port ###
        ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
        if len(ports) == 0:
            # might be on ubuntu with virtual connections, so do a glob.glob
            #  that will still be len() == 0 on non-virtual connections
            # How to detect if in a VM? It may be that /dev/vboxusb only
            #  exists on VM's, but have to check with a native Ubuntu (ie, Pi)

            if len(glob.glob('/dev/vboxusb*')) > 0:
                ports = glob.glob('/dev/ttyS*')
    elif sys.platform.startswith('darwin'):
        ### the second glob is for the xbee
        ports = glob.glob('/dev/tty.usbmodem*') + glob.glob('/dev/tty.usbserial*')
    else:
        raise EnvironmentError('Unsupported platform')
    return ports


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False
