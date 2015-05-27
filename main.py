#!python3

import sys, threading
from queue import Queue
from time import sleep
from datetime import datetime
from ctypes import c_int
from PyQt5.QtWidgets import *
from PyQt5 import QtCore, QtGui, uic
from PyQt5.QtCore import QRect, QRectF, Qt
from ns_driver import neilscope
from ns_anim import ns_animate


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
        
        # connect signals
        self.closeButton.clicked.connect(self.CloseButtonClicked)
        self.startButton.clicked.connect(self.StartButtonClicked)
        
        self.test_progress_signal.connect(self.test_progress_slot)
        self.device_ready_signal.connect(self.device_ready_slot)

        self.xplog_chckbx.toggled.connect(self.log_chckboxs_changed)
        self.nslog_chckbx.toggled.connect(self.log_chckboxs_changed)        
        self.log_signal.connect(self.qlog_message)

        # neiscope device object
        self.ns3 = neilscope()
        
        # thread for comunicate neilscope device
        t = threading.Thread(target = self.ns_test_worker)
        t.daemon = True  # thread dies when main thread exits.
        t.start()

        self.anim.machine.start()

        # set window to center and show
        self.center()
        self.show()


    # initialization UI
    def initUI(self):
        # load main ui window
        self.uic = uic.loadUi("main.ui", self)
        
        gr_rect = QRectF(0, 0, 381, 25);        
        self.scene = QGraphicsScene(gr_rect)
        self.scene.setBackgroundBrush(Qt.black)
        
        self.anim = ns_animate( self.scene,
                                gr_rect.width(), gr_rect.height(),
                                QtGui.QColor.fromRgb(0, 32, 49) )
                
        self.horizontalLayout_anim.addWidget(self.anim.window)

        # self.anim.start()
        self.anim.window.resize(gr_rect.width(), gr_rect.height())
        self.anim.window.show()


    # set window to center func
    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())



    # self logging message
    def log(self, msg, lvl = 'ginf'):
        self.log_signal.emit('\'GL\' ' + msg, lvl)

    
    # device test sequence
    def ns_test_seq(self):
        # neilscope device test sequence program, [function, [func args], delay sec after, log mesaage]
        # for single command form is - ns3.connect() ;; ns3.mode('osc') ;; ns.get_data(['A', 100])   
        ns_test_sequence = [ 
            [   self.ns3.mode,           'la',               0,      'set mode \'LA\'...'            ],
            [   self.ns3.send_sw_ver,    [1.1, 0x02],        0.5,    'send sw ver...'                ],
            [   self.ns3.mode,           'osc',              0,      'set mode \'OSC\'...'           ],
            [   self.ns3.send_sw_ver,    [1.1, 0x02],        0.5,    'send sw ver...'                ],

            [   self.ns3.ach_state,      ['AB', 'dc'],       0,      'set ch A/B DC input...'        ],
            [   self.ns3.ach_div,        ['AB', '50V'],      0.05,   'set ch A/B 50V/div...'         ],
            [   self.ns3.ach_div,        ['AB', '10mV'],     0.05,   'set ch A/B 10mV/div...'        ],
            
            [   self.ns3.sync_mode,      ['off'],            0,      'set sync off state...'         ],
            [   self.ns3.sync_sourse,    ['A'],              0,      'set sync sourse to ch A...'    ],
            [   self.ns3.sync_type,      ['rise'],           0,      'set sync type \'rise\'...'     ],
            [   self.ns3.sweep_div,      ['1uS'],            0,      'set sweep 1uS/div...'          ],
            [   self.ns3.sweep_mode,     ['standart'],       0,      'set swep mode \'standart\'...' ],

            [   self.ns3.get_data,       ['A', 50, []],      0,      'get ch A 50 bytes data...'     ],
            [   self.ns3.get_data,       ['B', 50, []],      0,      'get ch B 50 bytes data...'     ],
        ]

        progr_one_step = 100 / len(ns_test_sequence)
        progr = 0
        
        self.log('start test sequence')
        for cn in ns_test_sequence:
            self.log(cn[-1])
            # send sequense command            
            cmd_result = cn[0](cn[1])   
            if not cmd_result:
                self.log('SUCCESS\r\n')
                sleep(cn[2] + 0.1)
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

        lg('connect to device...')        
        if not self.ns3.connect():
            lg('successful connected to device, fw ver: %3.1F' % self.ns3.mcu_firm_ver)
                                
            lg('get batt charge...')
            battv = [int(0)]
            if self.ns3.get_batt(battv): return False
            lg('batt charge: %d%s' % (battv[0], '%'))

            # start test sequence
            test_seq_flag = self.ns_test_seq()
            
            lg('disconnect from device...')
            if not self.ns3.disconnect(): lg('disconnect success')
            else:
                test_seq_flag = False
                lg('FAILED', 'err')
        else:
            test_seq_flag = False
            lg('FAILED', 'err')
        
        # complite progress = 100%
        self.test_progress_signal.emit(100)

        lg('\r\n///{0}///{0}///'.format('-'*20), 'end')
        if test_seq_flag:
            lg('TEST SUCCESSFUL DONE', 'end')
        else: lg('TEST FAILED', 'err')



    # The worker thread pulls an item from the queue and processes it
    def ns_test_worker(self):
        while True:
            item = self.nqueue.get()
            with threading.Lock():
                if item == 'test':
                    self.ns_test_main()                    
                    sleep(0.5)
                    self.device_ready_signal.emit(True)
                    self.startButton.setEnabled(True)                         
            self.nqueue.task_done()


    # START button click slot
    @QtCore.pyqtSlot()
    def StartButtonClicked(self):                
        if not self.startButton.isEnabled(): return 
        self.device_ready_signal.emit(False)
        self.startButton.setEnabled(False)

        self.nqueue.join()         # block until all tasks are done 

        self.textBrowser.clear();        
        self.xplog_chckbx.toggled.emit(self.xplog_chckbx.isChecked())
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
    @QtCore.pyqtSlot(bool)
    def device_ready_slot(self, dev_rdy):
        self.anim.timer.setInterval(1000)        
        # save log to file
        f = open('logg.txt', 'wt')
        f.write(self.textBrowser.toPlainText())
        f.close()


    # QtSlot for log masagges
    @QtCore.pyqtSlot(str, str)
    def qlog_message(self, msg, lvl = 'inf'):
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
        else:
            txbr.setTextColor(qqolor(119, 255, 176))        
        
        txbr.insertPlainText('%s: %s \r\n' % (str(datetime.utcnow()).split()[1], msg))
        sb = txbr.verticalScrollBar()
        sb.setValue(sb.maximum())
        txbr.repaint()


    # logging check_box slot
    @QtCore.pyqtSlot(bool)
    def log_chckboxs_changed(self, chck):
        obj_name = self.sender().objectName()

        if obj_name == 'xplog_chckbx':            
            s_log = self.ns3.usbxpr.set_log
        elif obj_name == 'nslog_chckbx':
            s_log = self.ns3.set_log
        else:
            return
        
        if chck: s_log(self.log_signal.emit)
        else: s_log()


    # EXIT button click
    @QtCore.pyqtSlot()
    def CloseButtonClicked(self):
        self.close()

    		


# program start here
if __name__ == '__main__':

    app = QApplication(sys.argv)
    ex = ns_utility()    
    sys.exit(app.exec_())


