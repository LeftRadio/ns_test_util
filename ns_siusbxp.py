#!python3

from ctypes import *
from ctypes.wintypes import *


# main USBXpress class
class NS_SiUSBXp(object):

    respond_codes = {
        0x00:"SI_SUCCESS",
        0xFF:"SI_DEVICE_NOT_FOUND",
        0x01:"SI_INVALID_HANDLE",
        0x02:"SI_READ_ERROR",
        0x03:"SI_RX_QUEUE_NOT_READY",
        0x04:"SI_WRITE_ERROR",
        0x05:"SI_RESET_ERROR",
        0x06:"SI_INVALID_PARAMETER",
        0x07:"SI_INVALID_REQUEST_LENGTH",
        0x08:"SI_DEVICE_IO_FAILED",
        0x09:"SI_INVALID_BAUDRATE",
        0x0a:"SI_FUNCTION_NOT_SUPPORTED",
        0x0b:"SI_GLOBAL_DATA_ERROR",
        0x0c:"SI_SYSTEM_ERROR_CODE",
        0x0d:"SI_READ_TIMED_OUT",
        0x0e:"SI_WRITE_TIMED_OUT",
        0x0f:"SI_IO_PENDING"
    }

    def __init__(self, **kwargs):
        # constructor
        self.si_dll = windll.SiUSBxp
        self.handle = HANDLE()
        self.num_dev = 0
        self.open_dev = 0
        self.si_code = 0xFF;
        self.lg = None

    def xplg(msg, err): pass

    # set log callback, log func must be of the form: ' def nlg(msg, level) '
    def set_log(self, log):
        self.lg = log

    def log(self, msg):
        if self.lg is not None:
            if not self.si_code:
                lv = 'inf'
            else:
                lv = 'err'
            self.lg('\'si\' %s  %s' % (msg, self.si_status_str()), lv)

    def si_status_code(self):
        return self.si_code

    def si_status_str(self, si_code = None):
        if si_code == None:
            si_code = self.si_code
        return '(%s)' % NS_SiUSBXp.respond_codes[si_code].lower()

    def connect(self):
        status = 0xFF
        # get num connected usbxpress devices, verify descr dev string
        if self.get_num_dev() and 'NeilScope' in self.get_desc_str(0):
            # try open
            status = self.open(0)

        self.log(self.get_num_dev())
        self.log(self.get_desc_str(0))
        self.log(status)

        return status


    # // ------------------------------------ NS_SiUSBXp ------------------------------------ //

    def get_num_dev(self):
        # SI_STATUS SI_GetNumDevices (LPDWORD NumDevices)
        num_dev = DWORD()
        self.si_code = self.si_dll.SI_GetNumDevices(byref(num_dev))
        self.log('get num dev: %d' % num_dev.value)
        return int(num_dev.value)


    #SI_GetProductString (DWORD DeviceNum, LPVOID DeviceString, DWORD Options)
    def get_desc_str(self, dev_num, desc_str = [0]):
        s = create_string_buffer(128)
        self.si_code = self.si_dll.SI_GetProductString(dev_num, s, 1)
        s = str(s.value)
        self.log('get desc: %s' % s)
        return s


    #SI_GetProductString (DWORD DeviceNum, LPVOID DeviceString, DWORD Options)
    def get_vidpid(self, dev_id, vp = [0, 0]):
        s = [ create_string_buffer(32), create_string_buffer(32) ]
        self.si_code = self.si_dll.SI_GetProductString(dev_id, s[0], 0x03)
        self.si_code = self.si_dll.SI_GetProductString(dev_id, s[1], 0x04)
        vp[:] = [int(g.value, 16) for g in s]
        self.log('vid pid: 0x%X 0x%X' % (vp[0], vp[1]))
        return self.si_code


    # SI_Open (DWORD DeviceNum, HANDLE Handle)
    def open(self, dn):
        self.si_code = self.si_dll.SI_Open(DWORD(dn), byref(self.handle))
        self.log('open dev %d' % dn)
        return self.si_code


    # SI_Close (HANDLE Handle)
    def close(self):
        self.si_code = self.si_dll.SI_Close(self.handle)
        self.log('close dev: ')
        return self.si_code


    # SI_STATUS WINAPI SI_FlushBuffers(HANDLE cyHandle, BYTE FlushTransmit, BYTE FlushReceive)
    def flush_bufers(self, hard):
        self.si_code = self.si_dll.SI_FlushBuffers(self.handle, c_ubyte(0x01), c_ubyte(0x01))
        if hard:
            qb = c_ulong()
            qsts = c_ubyte()
            buf = c_ubyte()
            rb = c_ulong()
            while not self.si_code:
                self.si_code = self.si_dll.SI_CheckRXQueue(self.handle, byref(qb), byref(qsts))
                if not self.si_code and qsts:
                    self.si_code = self.si_dll.SI_Read(self.handle, byref(buf), c_ulong(1), byref(rb), None)
                    if not self.si_code:
                        break
                else:
                    break
        return self.si_code


    # SI_STATUS SI_Read (HANDLE Handle, LPVOID Buffer, DWORD NumBytesToRead, DWORD *NumBytesReturned, OVERLAPPED* 0 = NULL)
    def read(self, rd_buf, nb):
        buf = (c_ubyte * nb)()
        rb = c_ulong()

        self.si_code = self.si_dll.SI_Read(self.handle, byref(buf), c_ulong(nb), byref(rb), None)
        rd_buf[:] = [buf[j] for j in range(rb.value)]

        self.log('read: [ %s ] ' % ', '.join(hex(e) for e in rd_buf)) #['0x%X' % b for b in rd_buf])
        return self.si_code


    # SI_STATUS SI_Write (HANDLE Handle, LPVOID Buffer, DWORD NumBytesToWrite, DWORD *NumBytesWritten, OVERLAPPED* 0 = NULL)
    def write(self, in_buf, nb):
        wrd_nb = c_ulong()
        buf = (c_ubyte * nb)()

        for i in range(nb): buf[i] = c_ubyte(in_buf[i])
        self.si_code = self.si_dll.SI_Write(self.handle, byref(buf), c_ulong(nb), byref(wrd_nb), 0)

        self.log('write: [ %s ] ' %  ', '.join(hex(e) for e in buf)) # ['0x%X' % b for b in buf])
        return self.si_code


    #
    def setbr(self, br = 9600):
        self.si_code = self.si_dll.SI_SetBaudRate(self.handle, DWORD(br))
        self.log('set baudrate: %d ' % br)
        return self.si_code


    # SI_SetTimeouts (DWORD ReadTimeout, DWORD WriteTimeout)
    def set_timeout(self, rt = 1000, wt = 1000):
        self.si_code = self.si_dll.SI_SetTimeouts(DWORD(rt), DWORD(wt))
        self.log('set timeout rt:%d wt:%d  ' % (rt, wt))
        return self.si_code


    # SI_STATUS SI_GetTimeouts (LPDWORD ReadTimeout, LPDWORD WriteTimeout)
    def get_timeout(self):
        rt = DWORD()
        wt = DWORD()
        self.si_code = self.si_dll.SI_GetTimeouts(byref(rt), byref(wt))
        return (rt.value, wt.value)
