#!python3

import sys
import threading
from queue import Queue
from time import sleep
from datetime import datetime
from ctypes import c_int
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, uic
from PyQt5.QtCore import QRect, QRectF, Qt, pyqtSlot
from ns_commander import NS3_Commander
from ns_anim import NS_Animate


__version__ = 2.574

# main window class
class ns_utility(QMainWindow):

    log_signal = QtCore.pyqtSignal(str, str)
    test_progress_signal = QtCore.pyqtSignal(int)
    device_ready_signal = QtCore.pyqtSignal(bool)

    # constructor
    def __init__(self):
        super().__init__()

        # Create the queue for threads
        self.nqueue = Queue()
        # init user interface
        self.initUI()

        # connect signals/slots
        self.closeButton.clicked.connect(self.CloseButtonClicked)
        self.startButton.clicked.connect(self.StartButtonClicked)
        self.test_progress_signal.connect(self.test_progress_slot)
        self.device_ready_signal.connect(self.device_ready_slot)
        self.log_signal.connect(self.qlog_message)

        # neiscope device command 'driver' object
        self.ns3 = NS3_Commander()

        # thread for comunicate neilscope device
        t = threading.Thread(target=self.ns_test_worker)
        t.daemon = True  # thread dies when main thread exits.
        t.start()

        # start animation
        self.anim.machine.start()

        # set window to center and show
        self.center()
        self.show()

        self.start_msg = [
            'Testing util build ver: %.3f' % __version__,
            'NeilScope 3',
            'The full free SW/HW project',
            'of 100Msps(2-CH) 200Msps(1-CH) digital storage',
            'Oscilloscope and Logic Analyzer modes',
            'Contributors:',
            '---',
            'Vladislav Kamenev :: LeftRadio',
            'Ildar :: Muha',
            '---',
            'Special thanks to all who supported the project all the time !!!' ]
        self.nqueue.put('start')

    # initialization UI
    def initUI(self):
        # load main ui window
        self.uic = uic.loadUi('main.ui', self)

        gr_rect = QRectF(0, 0, self.rect().width(), 20)
        self.scene = QGraphicsScene(gr_rect)
        self.scene.setBackgroundBrush(Qt.black)

        self.anim = NS_Animate(self.scene,
                               gr_rect.width(), gr_rect.height(),
                               QtGui.QColor.fromRgb(0, 32, 49))

        self.horizontalLayout_anim.addWidget(self.anim.window)

        # self.anim.start()
        self.anim.window.resize(gr_rect.width(), gr_rect.height())

    # set window to center func
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    # self logging message
    def log(self, msg, lvl='ginf'):
        self.log_signal.emit('\'GL\' ' + msg, lvl)

    # device test sequence
    def ns_test_seq(self):
        # neilscope device test sequence program, [ command function, [func args], delay sec after, log mesaage ]
        ns_test_sequence = [
            {'cmd': self.ns3.mode, 'data': 'la', 'delay': 0, 'msg': 'set mode \'LA\'...'},
            {'cmd': self.ns3.send_sw_ver, 'data': [1.1, 0x02], 'delay': 0.5, 'msg': 'send sw ver...'},
            {'cmd': self.ns3.mode, 'data': 'osc', 'delay': 0, 'msg': 'set mode \'OSC\'...'},
            {'cmd': self.ns3.send_sw_ver, 'data': [1.1, 0x02], 'delay': 0.5, 'msg': 'send sw ver...'},
            {'cmd': self.ns3.ach_state, 'data': ['AB', 'dc'], 'delay': 0, 'msg': 'set ch A/B DC input...'},
            {'cmd': self.ns3.ach_div, 'data': ['AB', '50V'], 'delay': 0.05, 'msg': 'set ch A/B 50V/div...'},
            {'cmd': self.ns3.ach_div, 'data': ['AB', '50mV'], 'delay': 0.05, 'msg': 'set ch A/B 50mV/div...'},
            {'cmd': self.ns3.sync_mode, 'data': ['off'], 'delay': 0, 'msg': 'set sync off state...'},
            {'cmd': self.ns3.sync_sourse, 'data': ['A'], 'delay': 0, 'msg': 'set sync sourse to ch A...'},
            {'cmd': self.ns3.sync_type, 'data': ['rise'], 'delay': 0, 'msg': 'set sync type \'rise\'...'},
            {'cmd': self.ns3.sweep_div, 'data': ['1uS'], 'delay': 0, 'msg': 'set sweep 1uS/div...'},
            {'cmd': self.ns3.sweep_mode, 'data': ['standart'], 'delay': 0, 'msg': 'set swep mode \'standart\'...'},
            {'cmd': self.ns3.get_data, 'data': ['A', 100, []], 'delay': 0, 'msg': 'get ch A 100 bytes data...'},
            {'cmd': self.ns3.get_data, 'data': ['B', 100, []], 'delay': 0, 'msg': 'get ch B 100 bytes data...'},
        ]

        progr_one_step = 100 / len(ns_test_sequence)
        progr = 0

        self.log('start test sequence')
        for cn in ns_test_sequence:
            self.log(cn['msg'])
            # send sequense command
            cmd_result = cn['cmd']( cn['data'] )
            # result
            if not cmd_result:
                self.log('SUCCESS\r\n')
                sleep(cn['delay'])
                progr = progr + progr_one_step
                self.test_progress_signal.emit(progr)   # emit progress signal
            else:
                self.log('FAILED\r\n', 'err')
                return False
        return True

    # device main test
    def ns_test_main(self):
        lg = self.log
        test_seq_flag = True
        self.test_progress_signal.emit(0)   # complite progress = 0%

        # set interface
        index = self.combobox_Interface.currentIndex()

        if self.chckbx_interface.checkState():
            interface_log = self.log_signal.emit
        else:
            interface_log = None

        if index == 0:
            self.log(str(self.chckbx_interface.checkState()))
            self.ns3.set_interface( interface = 'usbxpress', log = interface_log )

        elif index == 1:
            ip, port = self.lineEdit_IP_Port.text().split(':')
            self.ns3.set_interface( interface = 'telnet', ip = ip, port = int(port), log = interface_log )

        if self.nslog_chckbx.checkState():
            self.ns3.set_log(self.log_signal.emit)
        else:
            self.ns3.set_log(None)

        lg('connect to device...')
        if not self.ns3.connect():
            lg('successful connected to device, fw ver: %3.1F' %
               self.ns3.mcu_firm_ver)

            lg('get batt charge...')
            battv = [int(0)]
            if self.ns3.get_batt(battv):
                return False
            lg('batt charge: %d%s' % (battv[0], '%'))

            # start test sequence
            test_seq_flag = self.ns_test_seq()

            lg('disconnect from device...')
            if not self.ns3.disconnect():
                lg('disconnect success')
            else:
                test_seq_flag = False
                lg('FAILED', 'err')
        else:
            test_seq_flag = False
            lg('FAILED', 'err')

        # complite progress = 100%
        self.test_progress_signal.emit(100)

        lg('\r\n///{0}///{0}///'.format('-' * 20), 'end')
        if test_seq_flag:
            lg('TEST SUCCESSFUL DONE', 'end')
        else:
            lg('TEST FAILED', 'err')

    # The worker thread pulls an item from the queue and processes it
    def ns_test_worker(self):
        while True:
            item = self.nqueue.get()
            with threading.Lock():
                if item == 'start':
                    import random
                    for m in self.start_msg:
                        self.log_signal.emit(m, '')
                        sleep(random.uniform(0.15, 0.3))
                if item == 'test':
                    self.ns_test_main()
                    sleep(0.5)
                    self.device_ready_signal.emit(True)
                    self.startButton.setEnabled(True)

            self.nqueue.task_done()

    # START button click slot
    @pyqtSlot()
    def StartButtonClicked(self):
        if not self.startButton.isEnabled():
            return
        self.device_ready_signal.emit(False)
        self.startButton.setEnabled(False)

        self.nqueue.join()         # block until all tasks are done

        self.textBrowser.clear()
        self.chckbx_interface.toggled.emit(self.chckbx_interface.isChecked())
        self.nslog_chckbx.toggled.emit(self.nslog_chckbx.isChecked())

        self.nqueue.put('test')    # start ns test thread

    # device test sequence progress signal/slot
    old_progr = 0

    def test_progress_slot(self, progress):
        if (progress - self.old_progr) > 20:
            self.anim.timer.setInterval(600 - (progress * 5))
            self.old_progr = progress
        elif not progress:
            self.old_progr = progress

    # device test sequence successfull complite signal/slot
    @pyqtSlot(bool)
    def device_ready_slot(self, dev_rdy):
        self.anim.timer.setInterval(1000)
        # save log to file
        f = open('logg.txt', 'wt')
        f.write(self.textBrowser.toPlainText())
        f.close()

    # QtSlot for log masagges
    @pyqtSlot(str, str)
    def qlog_message(self, msg, lvl=''):
        txbr = self.textBrowser
        qqolor = QtGui.QColor.fromRgb

        if lvl == 'err':
            txbr.setTextColor(qqolor(255, 64, 64))
        elif lvl == 'warn':
            txbr.setTextColor(qqolor(220, 220, 140))
        elif lvl == 'ginf':
            txbr.setTextColor(qqolor(255, 255, 255))
        elif lvl == 'end':
            txbr.setTextColor(qqolor(170, 255, 0))
        elif lvl == 'inf':
            txbr.setTextColor(qqolor(119, 255, 176))
        else:
            txbr.setTextColor(qqolor(212, 224, 212))

        txbr.insertPlainText(
            '%s: %s \r\n' % (str(datetime.utcnow()).split()[1], msg))
        sb = txbr.verticalScrollBar()
        sb.setValue(sb.maximum())
        txbr.repaint()

    # EXIT button click
    @pyqtSlot()
    def CloseButtonClicked(self):
        self.close()


# program start here
if __name__ == '__main__':

    app = QApplication(sys.argv)
    QApplication.setStyle(QStyleFactory.create('Fusion'))
    ex = ns_utility()
    sys.exit(app.exec_())
