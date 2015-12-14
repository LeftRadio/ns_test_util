#!python3

import datetime
import telnetlib
from ns_interface import NS_DriverInterface


class NS_Telnet(NS_DriverInterface):
    """docstring for NS_Telnet"""

    def __init__(self, **kwargs):
        """ constructor """
        super(NS_Telnet, self).__init__()

        self.server_ip = kwargs.get('ip', '192.168.1.119')
        self.server_port = kwargs.get('port', 2323)
        self._open = False
        self.telnet = telnetlib.Telnet()

        self.readrequest_bytes = 1
        self.read_done = False

        self.write_timeout = 1000
        self.read_timeout = 1000

    def set_ip_port(self, **kwargs):
        self.server_ip = kwargs.get('ip', self.server_ip)
        self.server_port = kwargs.get('port', self.server_port)

    def connect(self):
        """ connect to server """
        # uncomment for debug messages from telnetlib
        # self.telnet.set_debuglevel(1, self.log)

        if not self.open(None):
            # get and verify descr dev string
            if 'NeilScope' in self.get_desc_str(0):
                return 0

        return 1

    # // ------------------------------------  ------------------------------------ //

    def get_num_dev(self):
        """ """
        if self.connected:
            return 1
        else:
            return 0

    def get_desc_str(self, id):
        s = 'NeilScope3 telnet'
        self.log('get desc: %s' % s)
        return s

    def get_vidpid(self, dev_id, vp = [0, 0]):
        vp[:] = [0x10c4, 0x8693]
        self.log('vid pid: 0x%X 0x%X' % (vp[0], vp[1]))
        return 0

    def open(self, handle):
        """ """
        code = 0xFF
        e = ''

        try:
            self.telnet.open(self.server_ip, self.server_port, 1)
            self._open = True
            code = 0
        except Exception as ex:
            e = '>> ' + str(ex).replace(' ', '_').upper()
            code = 0x10

        self.log('try open - %s:%s' % ( self.server_ip, self.server_port), code=code)
        return code

    def close(self):
        self.telnet.close()
        self.log('closed')
        return 0

    def flush_bufers(self, hard):
        """ """
        return 0

    def read(self, rd_buf, nb):

        status = 0x00
        dt = datetime.datetime
        start = dt.now().time().second * 1000000 + dt.now().time().microsecond

        ans = b''
        while len(ans) < nb:
            a = self.telnet.read_eager_raw()
            # if a != b'':
            ans += a

            nt = dt.now().time().second * 1000000 + dt.now().time().microsecond - start
            if nt  > self.read_timeout * 1000:
                status = 0x0d
                self.log(str(ans))
                break

        rd_buf[:] = [b for b in ans]
        self.log( 'read - [%s]' % ', '.join( [hex(b) for b in rd_buf] ) )
        return status

    def write(self, buf, nb):
        """ """
        self.log('write - [%s]' % ', '.join( [hex(b) for b in buf] ) )
        self.telnet.write( bytearray(b for b in buf) )
        return 0

    def setbr(self, br=9600):
        self.log('set baudrate - %d' % br)
        return 0

    def set_timeout(self, rt = 1000, wt = 1000):
        self.write_timeout = wt
        self.read_timeout = rt
        self.log('set timeouts: read %d, write %d' % (rt, wt))
        return 0

    def get_timeout(self):
        return (self.write_timeout, self.read_timeout)




if __name__ == '__main__':

    nstel = NS_Telnet()
    nstel.set_log(print)

    if nstel.open(None) == 0:

        nstel.setbr(921600)
        nstel.set_timeout(1000, 1000)

        nstel.write(b'HELLO!')

        rd_buf = []
        nstel.read(rd_buf, len(b'HELLO!'))
        nstel.close()
        print(rd_buf)
