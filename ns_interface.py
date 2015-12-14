#!python3


class NS_DriverInterface(object):
    """docstring for NS_DriverInterface"""

    respond_codes = {
        0x00: "SUCCESS",
        0xFF: "OPERATION_ERROR",
        0x01: "SI_INVALID_HANDLE",
        0x02: "SI_READ_ERROR",
        0x03: "SI_RX_QUEUE_NOT_READY",
        0x04: "SI_WRITE_ERROR",
        0x05: "SI_RESET_ERROR",
        0x06: "SI_INVALID_PARAMETER",
        0x07: "SI_INVALID_REQUEST_LENGTH",
        0x08: "SI_DEVICE_IO_FAILED",
        0x09: "SI_INVALID_BAUDRATE",
        0x0a: "SI_FUNCTION_NOT_SUPPORTED",
        0x0b: "SI_GLOBAL_DATA_ERROR",
        0x0c: "SI_SYSTEM_ERROR_CODE",
        0x0d: "READ_TIMED_OUT",
        0x0e: "WRITE_TIMED_OUT",
        0x0f: "IO_PENDING",
        0x10: "OPEN_TIMED_OUT"
    }

    def __init__(self):
        """ constructor """
        self.code = 0x00;
        self.lg = None

    def set_log(self, log):
        """ set log callback """
        self.lg = log

    def log(self, msg, **kwargs):
        code = kwargs.get('code', self.code)

        if self.lg is not None:
            if not code: lv = 'inf'
            else: lv = 'err'
            self.lg('\'interface\' %s' % msg, lv)

    def status_code(self):
        return self.code

    def status_str(self, code=None):
        if code is None:
            code = self.code
        return '(%s)' % self.respond_codes[code].lower()

    def set_ip_port(self, **kwargs):
        pass