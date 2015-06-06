#!python3

from time import sleep
from crc8 import ns_crc_buf
from siusbxp import siusbxp

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
# https://github.com/LeftRadio/neil-scope3/blob/master/doc/NeilScope_v3_protocol_L.pdf
ns_command = {
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
    'trig UP':          [0x18, 0x01, 0x80],
    'trig X':           [0x19, 0x03, 0x00, 0x00, 0x00],
    'trig mask diff':   [0x20, 0x01, 0xFF],
    'trig mask cond':   [0x21, 0x01, 0xFF],
    'sweep div':        [0x25, 0x01, 0x00],
    'sweep mode':       [0x27, 0x01, 0x00],    
    'get data':         [0x30, 0x03, 0x00, 0x00, 0x00],
    'batt':             [0xA0, 0x01, 0xA0],
    'save eeprom':      [0xEE, 0x01, 0xEE],
    'bootloader':       [0xB0, 0x01, 0x0B],
    'mcu fw ver':       [0x00, 0x01, 0xFF],
    'send sw ver':      [0x01, 0x03, 0x01, 0x01, 0xFF],
}


# empty log func, used if log func not defined
def nlg(msg, err): pass

# Neil Scope class
class neilscope(object):

    def __init__(self):
        # constructor                        
        self.usbxpr = siusbxp()        
        self.vidpid = [0,0]
        self.log = nlg
        self.connected = 0
        self.mcu_firm_ver = 0.0
        self.read_data_len = 0
        self.write_respond = []


    # set log callback, log func must be of the form: ' def nlg(msg, lvl) '
    def set_log(self, log = nlg):
        self.log = log

    def lg(self, msg, lvl = 'inf'):
        self.log('\'ns\' ' + msg, lvl)


    # get and verify vid/pid
    def vid_pid(self):
        vp = self.vidpid
        return ( not self.usbxpr.get_vidpid(0, vp) and vp[0] == 0x10C4 and vp[1] == 0x8693 )


    # configurate baudrate and timeouts for work with device
    def conf_si(self, rtout, wtout, baud = 921600):
        st = self.usbxpr.setbr(baud) | self.usbxpr.set_timeout(rtout, wtout)        
        return st


    # write command to device example: [0x5B, 0x00, 0x01, 0xFF]
    def write_cmd(self, cmd):
        self.lg('try send cmd', 'warn')
        
        cm = [0x5B] + cmd                       
        cm.append(ns_crc_buf(cm))
                
        self.usbxpr.flush_bufers(0)
        if not self.usbxpr.write(cm, len(cm)):
            
            if not self.read_data_len: ln_cm = len(cm)
            else: ln_cm = self.read_data_len
            
            self.read_data_len = 0
            self.write_respond = [0 in range(ln_cm)]
            rd = self.write_respond
            
            if not self.usbxpr.read(rd, ln_cm) and not ns_crc_buf(rd):
                
                # remove 'start' and 'crc' bytes
                rd.remove(rd[-1])
                rd.remove(rd[0])
                if rd[0] == (cm[1] + 0x40) & 0xFF:  # if returned command byte = write command + 0x40
                    self.lg('cmd ack recived')
                    return 0
                else:
                    if rd[3] > 3: rd[3] = 0x7F  # if returned error code not recognize replace to 'NS3_ERROR'
                    err_msg = 'error code: %s' % ns_err_list[rd[3]]

            else:                
                err_msg = 'cmd ack error'

        else:
            err_msg = 'write cmd error'

        self.lg(err_msg, 'err')
        return 1


    # connect to device
    def connect(self):
        xpr = self.usbxpr
        log = self.lg
        # get num connected usbxpress devices, get and verify descr dev string, get and verify vid/pid
        if xpr.get_num_dev() and 'NeilScope' in xpr.get_desc_str(0) and self.vid_pid():                           
            log('device found')
            
            # NeilScope device identified OK, try open, set si_settigs and init PC mode
            if not (xpr.open(0) | self.conf_si(1000, 1000) | self.write_cmd(ns_command['connect'])):
                  log('connect OK')
                  sleep(0.1)

                  # get firmware version
                  firm_ver = [0.0]
                  if not self.get_fw_ver(firm_ver):
                      self.mcu_firm_ver = firm_ver[0]         
                  
                  # return successfull connect 
                  return 0
            else:
                xpr.close()
                log('connect fail', 'err')
        else: log('device not found', 'err')
        
        return 1


    # disconnect from device
    def disconnect(self):
        st = self.write_cmd(ns_command['disconnect'])
        
        if not st: self.lg('diconnected')                        
        else: self.lg('diconnect fail', 'err')            
        
        self.usbxpr.close()
        return st


    # set oscilloscope or logic analyzer mode
    def mode(self, mode):
        ns_command['osc la mode'][-1] = ns_mode[mode]        
        return self.write_cmd(ns_command['osc la mode'])


    # set analog channels state
    def ach_state(self, param = ['AB', 'off']):
        st = ns_ach[param[1]]       
        
        if param[0] == 'A': acm = [st, 0x03]
        elif param[0] == 'B': acm = [0x03, st]
        else: acm = [st, st]

        ns_command['analog ch set'][-2:] = acm
        return self.write_cmd(ns_command['analog ch set'])


    # set analog divider
    def ach_div(self, param = ['AB', '50V']):
        ch = param[0]
        div = param[1]
        st = ns_adiv[div]    
        
        if ch == 'A': div = [st, 0x0C]
        elif ch == 'B': div = [0x0C, st]
        else: div = [st, st]

        ns_command['analog div'][-2:] = div
        return self.write_cmd(ns_command['analog div'])


    # set syncronization mode
    def sync_mode(self, param = ['off']):
        ns_command['analog div'][-1] = ns_sync_mode[param[0]]
        return self.write_cmd(ns_command['analog div'])        


    # set syncronization sourse
    def sync_sourse(self, param = ['A']):
        ns_command['sync sourse'][-1] = ns_channels[param[0]]
        return self.write_cmd(ns_command['sync sourse'])


    # set syncronization type
    def sync_type(self, param = ['rise']):
        ns_command['sync type'][-1] = ns_sync_type[param[0]]
        return self.write_cmd(ns_command['sync type'])


    # set trigger 'UP'
    def triggUP(self, param = [0x80]):
        ns_command['trig UP'][-1] = param[0]
        return self.write_cmd(ns_command['trig UP'])


    # set trigger 'DOWN'
    def triggDOWN(self, param = [0x80]):
        ns_command['trig DOWN'][-1] = param[0]
        return self.write_cmd(ns_command['trig DOWN'])

    
    # set trigger X position
    def triggX(self, param = [0x000001]):
        ns_command['trig X'][-3] = [ param[0]>>16, param[0]>>8, param[0] ]
        return self.write_cmd(ns_command['trig X'])


    # set la trigger mask different
    def la_mask_diff(self, param = [0xFF]):
        ns_command['trig mask diff'][-1] = param[0]
        return self.write_cmd(ns_command['trig mask diff'])


    # set la trigger mask condition
    def la_mask_cond(self, param = [0xFF]):
        ns_command['trig mask cond'][-1] = param[0]
        return self.write_cmd(ns_command['trig mask cond'])


    # set sweep divider
    def sweep_div(self, param = ['1uS']):
        ns_command['sweep div'][-1] = ns_sweep_div[param[0]]
        return self.write_cmd(ns_command['sweep div'])


    # set sweep mode
    def sweep_mode(self, param = ['standart']):
        ns_command['sweep mode'][-1] = ns_sweep_mode[param[0]]
        return self.write_cmd(ns_command['sweep mode'])


    # data reques from selected channel - 'A', 'B', 'LA'
    def get_data(self, param = ['A', 100, []]):
        num = param[1]
        ns_command['get data'][-3:] = [(num>>10)&0xFF, (num>>2)&0xFF, (num<<6)&0xFF]
        self.read_data_len = num + 9
        ws = self.write_cmd(ns_command['get data'])
        if not ws:
            param[2][:] = []
            param[2].append(self.write_respond)
        return ws


    # get batt voltage level in procents
    def get_batt(self, param = [0]):
        ws = self.write_cmd(ns_command['batt'])
        if not ws: param[0] = int(self.write_respond[-1])
        return ws


    # save eeprom request
    def save_eeprom(self, param = []):
        return self.write_cmd(ns_command['save eeprom'])


    # jump to bootloader request
    def boot_jump(self, param = []):
        return self.write_cmd(ns_command['bootloader'])


    # mcu firmware version request
    def get_fw_ver(self, param = [0.0]):
        ws = self.write_cmd(ns_command['mcu fw ver'])
        if not ws:
            print('%s' % ' '.join(str(r) for r in self.write_respond))
            param[0] = float(self.write_respond[-1]) / 10
            self.mcu_firm_ver = param[0]            
        return ws


    # send software ver and id to device
    def send_sw_ver(self, param = [1.0, 0x02]):
        ns_command['send sw ver'][-3:] = [ int(param[0]), 1, param[1] ]
        return self.write_cmd(ns_command['send sw ver'])

        
