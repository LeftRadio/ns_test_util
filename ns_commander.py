#!python3

from time import sleep
from crc8 import ns_crc_buf
from ns_siusbxp import NS_SiUSBXp
from ns_telnet import NS_Telnet


# ns device return error code
ns_err_list = {
    0x7F: 'NS3_ERROR',
    0x01: 'CRC',
    0x02: 'CMD_DATA',
    0x03: 'BUSY'
}

# channels
ns_channels = {
    'A': 0x00,
    'B': 0x01,
    'LA': 0x02,
}
# analog channel state
ns_ach = {
    'off': 0x00,
    'ac': 0x01,
    'dc': 0x02,
    'nochg': 0x03
}
# analog channel input divider
ns_adiv = {
    '10mV': 0x00, '20mV': 0x01, '50mV': 0x02, '100mV': 0x03, '200mV': 0x04, '500mV': 0x05,
    '1V': 0x06, '2V': 0x07, '5V': 0x08, '10V': 0x09, '20V': 0x0A, '50V': 0x0B,
    'nochg': 0x0C, 'auto': 0xAA
}

ns_sync_mode = {
    'off': 0x00,
    'norm': 0x01,
    'auto': 0x02,
    'singl': 0x03
}

ns_sync_type = {
    'rise': 0x00,
    'fall': 0x01,
    'in win': 0x02,
    'out win': 0x03,
    'la cond': 0x04,
    'la diff': 0x05,
    'la cond and diff': 0x06,
    'la cond or diff': 0x07
}

ns_sweep_div = {
    '250nS': 0x00, '500nS': 0x01,
    '1uS': 0x02, '2uS': 0x03, '5uS': 0x04, '10uS': 0x05, '20uS': 0x06, '50uS': 0x07, '100uS': 0x08, '200uS': 0x09, '500uS': 0x0A,
    '1mS': 0x0B, '2mS': 0x0C, '5mS': 0x0D, '10mS': 0x0E, '20mS': 0x0F, '50mS': 0x10, '100mS': 0x11, '200mS': 0x12, '500mS': 0x13,
    '1S': 0x14
}

ns_sweep_mode = {
    'standart': 0x00,
    'min max': 0x01,
    'interlive': 0x02,
    'la RLE': 0x03
}

# ns device global work mode - Oscilloscope or LogicAnalyzer
ns_mode = {
    'osc': 0x00,
    'la': 0x01
}

# ns device commands, for more details please ref to
# https://github.com/LeftRadio/neil-scope3/blob/master/.doc/NeilScope_v3_protocol_L.pdf
ns_cmd = {
    'connect':          [0x81, 0x02, 0x86, 0x93],
    'disconnect':       [0xFC, 0x02, 0x86, 0x93],
    'osc la mode':      [0x09, 0x01, 0x00],
    'analog ch set':    [0x10, 0x02, 0x00, 0x00],
    'analog div':       [0x11, 0x02, 0x0B, 0x0B],
    'analog calibrate': [0x12, 0x01, 0xFF],
    'sync mode':        [0x14, 0x01, 0x00],
    'sync sourse':      [0x15, 0x01, 0x01],
    'sync type':        [0x16, 0x01, 0x00],
    'trig UP':          [0x17, 0x01, 0x80],
    'trig DOWN':        [0x18, 0x01, 0x80],
    'trig X':           [0x19, 0x03, 0x00, 0x00, 0x00],
    'trig mask diff':   [0x20, 0x01, 0xFF],
    'trig mask cond':   [0x21, 0x01, 0xFF],
    'sweep div':        [0x25, 0x01, 0x00],
    'sweep mode':       [0x27, 0x01, 0x00],
    'get data':         [0x30, 0x04, 0x00, 0x00, 0x00, 0x00],
    'batt':             [0xA0, 0x01, 0xA0],
    'save eeprom':      [0xEE, 0x01, 0xEE],
    'bootloader':       [0xB0, 0x01, 0x0B],
    'mcu fw ver':       [0x00, 0x01, 0xFF],
    'send sw ver':      [0x01, 0x03, 0x01, 0x01, 0xFF],
}


# empty log func, used if log func not defined
# def nlg(msg, err): pass

# Neil Scope class
class NS3_Commander(object):

    def nlg(msg, err): pass

    def __init__(self):
        self.ns_interface = None
        self.vidpid = [0,0]
        self.connected = 0
        self.mcu_firm_ver = 0.0
        self.write_respond = []

    def set_log(self, log):
        if log is not None:
            self.log = log
        else:
            self.log = NS3_Commander.nlg

    def lg(self, msg, lvl = 'inf'):
        self.log('\'ns\' ' + msg, lvl)

    def set_interface(self, **kwargs):
        # get interface, default usbxpress
        interface = kwargs.get('interface', 'usbxpress')

        if 'usbxpress' in interface:
            self.ns_interface = NS_SiUSBXp()

        elif 'telnet' in interface:
            ip = kwargs.get('ip', '192.168.1.119')
            port = kwargs.get('port', 2323)

            self.ns_interface = NS_Telnet()
            self.ns_interface.set_ip_port( ip=ip, port=port )

        # set log callback, log func must be of the form: ' def nlg(msg, lvl) '
        interface_log = kwargs.get('log', None)
        # if interface_log == None:
        #     interface_log = NS3_Commander.nlg
        self.ns_interface.set_log(interface_log)

    # get and verify vid/pid
    def vid_pid(self):
        success = False
        vp = self.vidpid
        if not self.ns_interface.get_vidpid(0, vp):
            if vp[0] == 0x10C4 and vp[1] == 0x8693:
                success = True

        return success

    # configurate baudrate and timeouts for work with device
    def interface_config(self, rtout, wtout, baud = 921600):
        st = self.ns_interface.setbr(baud) | self.ns_interface.set_timeout(rtout, wtout)
        return st

    # write command to device example: [0x5B, 0x00, 0x01, 0xFF]
    def write_cmd(self, cmd, **kwargs):
        self.lg('try send cmd', 'warn')

        cm = [0x5B] + cmd
        cm.append(ns_crc_buf(cm))

        self.ns_interface.flush_bufers(0)
        if not self.ns_interface.write(cm, len(cm)):

            # if read data len not provide set to same write message len
            rlen = kwargs.get('rlen', len(cm))

            self.write_respond = [0 in range(rlen)]
            rd = self.write_respond

            if not self.ns_interface.read(rd, rlen) and not ns_crc_buf(rd):
                # remove 'start' and 'crc' bytes
                rd.remove(rd[-1])
                rd.remove(rd[0])
                if rd[0] == (cm[1] + 0x40) & 0xFF:  # if returned command byte = write command + 0x40
                    self.lg('cmd ack recived')
                    return 0
                else:
                    err_msg = 'cmd ack error'

            else:
                err_msg = 'cmd read or ack error'

        else:
            err_msg = 'write cmd error'

        self.lg(err_msg, 'err')
        return 1

    # connect to device
    def connect(self):
        """ """
        interface = self.ns_interface
        self.lg('connecting with %s' % interface.__class__.__name__)

        # get connected devices, open, verify descr dev string, verify vid/pid
        if interface is not None and not interface.connect() and self.vid_pid():
            self.lg('device found')

            # NeilScope device identified OK, try open, set si_settigs and init PC mode
            if not ( self.interface_config(5000, 5000) | self.write_cmd( ns_cmd['connect'] ) ): #ns_cmd['connect']
                  self.lg('connect OK')
                  sleep(0.5)

                  # get firmware version
                  firm_ver = [0.0]
                  if not self.get_fw_ver(firm_ver):
                      self.mcu_firm_ver = firm_ver[0]

                      # return successfull connect
                      return 0
            else:
                interface.close()
                self.lg('connect fail', 'err')
        else:
            self.lg('device not found', 'err')

        return 1

    # disconnect from device
    def disconnect(self):
        st = self.write_cmd(ns_cmd['disconnect'])

        if not st: self.lg('diconnected')
        else: self.lg('diconnect fail', 'err')

        self.ns_interface.close()
        return st

    # set oscilloscope or logic analyzer mode
    def mode(self, mode):
        ns_cmd['osc la mode'][-1] = ns_mode[mode]
        return self.write_cmd(ns_cmd['osc la mode'])

    # set analog channels state
    def ach_state(self, param = ['AB', 'off']):
        st = ns_ach[param[1]]

        if param[0] == 'A': acm = [st, 0x03]
        elif param[0] == 'B': acm = [0x03, st]
        else: acm = [st, st]

        ns_cmd['analog ch set'][-2:] = acm
        return self.write_cmd(ns_cmd['analog ch set'])

    # set analog divider
    def ach_div(self, param = ['AB', '50V']):
        ch = param[0]
        div = param[1]
        st = ns_adiv[div]

        if ch == 'A': div = [st, 0x0C]
        elif ch == 'B': div = [0x0C, st]
        else: div = [st, st]

        ns_cmd['analog div'][-2:] = div
        return self.write_cmd(ns_cmd['analog div'])

    # set syncronization mode
    def sync_mode(self, param = ['off']):
        ns_cmd['analog div'][-1] = ns_sync_mode[param[0]]
        return self.write_cmd(ns_cmd['analog div'])

    # set syncronization sourse
    def sync_sourse(self, param = ['A']):
        ns_cmd['sync sourse'][-1] = ns_channels[param[0]]
        return self.write_cmd(ns_cmd['sync sourse'])

    # set syncronization type
    def sync_type(self, param = ['rise']):
        ns_cmd['sync type'][-1] = ns_sync_type[param[0]]
        return self.write_cmd(ns_cmd['sync type'])

    # set trigger 'UP'
    def triggUP(self, param = [0x80]):
        ns_cmd['trig UP'][-1] = param[0]
        return self.write_cmd(ns_cmd['trig UP'])

    # set trigger 'DOWN'
    def triggDOWN(self, param = [0x80]):
        ns_cmd['trig DOWN'][-1] = param[0]
        return self.write_cmd(ns_cmd['trig DOWN'])

    # set trigger X position
    def triggX(self, param = [0x000001]):
        ns_cmd['trig X'][-3] = [ param[0]>>16, param[0]>>8, param[0] ]
        return self.write_cmd(ns_cmd['trig X'])

    # set la trigger mask different
    def la_mask_diff(self, param = [0xFF]):
        ns_cmd['trig mask diff'][-1] = param[0]
        return self.write_cmd(ns_cmd['trig mask diff'])

    # set la trigger mask condition
    def la_mask_cond(self, param = [0xFF]):
        ns_cmd['trig mask cond'][-1] = param[0]
        return self.write_cmd(ns_cmd['trig mask cond'])

    # set sweep divider
    def sweep_div(self, param = ['1uS']):
        ns_cmd['sweep div'][-1] = ns_sweep_div[param[0]]
        return self.write_cmd(ns_cmd['sweep div'])

    # set sweep mode
    def sweep_mode(self, param = ['standart']):
        ns_cmd['sweep mode'][-1] = ns_sweep_mode[param[0]]
        return self.write_cmd(ns_cmd['sweep mode'])

    # data reques from selected channel - 'A', 'B', 'LA'
    def get_data(self, param = ['A', 100, []]):

        num = param[1]
        ns_cmd['get data'][-4:-1] = [(num>>10)&0xFF, (num>>2)&0xFF, (num<<6)&0xFF]
        if param[0] == 'A':
            ns_cmd['get data'][-1] = 0x00
        elif param[0] == 'B':
            ns_cmd['get data'][-1] = 0x01

        ws = self.write_cmd(ns_cmd['get data'], rlen=num+9)
        if not ws:
            param[2][:] = []
            param[2].append(self.write_respond)
        return ws

    # get batt voltage level in procents
    def get_batt(self, param = [0]):
        ws = self.write_cmd(ns_cmd['batt'])
        if not ws: param[0] = int(self.write_respond[-1])
        return ws

    # save eeprom request
    def save_eeprom(self, param = []):
        return self.write_cmd(ns_cmd['save eeprom'])

    # jump to bootloader request
    def boot_jump(self, param = []):
        return self.write_cmd(ns_cmd['bootloader'])

    # mcu firmware version request
    def get_fw_ver(self, param = [0.0]):
        ws = self.write_cmd(ns_cmd['mcu fw ver'])
        if not ws:
            param[0] = float(self.write_respond[-1]) / 10
            self.mcu_firm_ver = param[0]
        return ws

    # send software ver and id to device
    def send_sw_ver(self, param = [1.0, 0x02]):
        ns_cmd['send sw ver'][-3:] = [ int(param[0]), 1, param[1] ]
        return self.write_cmd(ns_cmd['send sw ver'])


