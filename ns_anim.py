#!python3
import sys
from PyQt5 import QtGui
from PyQt5.QtCore import (QAbstractTransition, QEasingCurve, QEvent,
        QParallelAnimationGroup, QPropertyAnimation, qrand, QRect,
        QSequentialAnimationGroup, qsrand, QState, QStateMachine, Qt, QTime,
        QTimer)
from PyQt5.QtWidgets import (QApplication, QGraphicsScene, QGraphicsView,
        QGraphicsWidget)


# 
class StateSwitchEvent(QEvent):
    StateSwitchType = QEvent.User + 256

    def __init__(self, rand=0):
        super(StateSwitchEvent, self).__init__(StateSwitchEvent.StateSwitchType)

        self.m_rand = rand

    def rand(self):
        return self.m_rand

# 
class QGraphicsRectWidget(QGraphicsWidget):
    def __init__(self, color):
        super(QGraphicsRectWidget, self).__init__()
        self.color = color

    def paint(self, painter, option, widget):
        painter.fillRect(self.rect(), self.color)

# 
class StateSwitchTransition(QAbstractTransition):
    def __init__(self, rand):
        super(StateSwitchTransition, self).__init__()
        self.m_rand = rand

    def eventTest(self, event):
        return (event.type() == StateSwitchEvent.StateSwitchType and
                event.rand() == self.m_rand)

    def onTransition(self, event):
        pass

# 
class StateSwitcher(QState):
    def __init__(self, machine):
        super(StateSwitcher, self).__init__(machine)
        
        self.m_stateCount = 0
        self.m_lastIndex = 0

    def onEntry(self, event):
        n = qrand() % self.m_stateCount + 1
        while n == self.m_lastIndex:
            n = qrand() % self.m_stateCount + 1

        self.m_lastIndex = n
        self.machine().postEvent(StateSwitchEvent(n))

    def onExit(self, event):
        pass

    def addState(self, state, animation):
        self.m_stateCount += 1
        trans = StateSwitchTransition(self.m_stateCount)
        trans.setTargetState(state)
        self.addTransition(trans)
        trans.addAnimation(animation)


# 
class ns_animate(object):
    def __init__(self, scene, x_max, y_max, back_color):
                
        scene = QGraphicsScene(0, 0, x_max, y_max)
        scene.setBackgroundBrush(back_color)

        color = [Qt.green, Qt.lightGray, Qt.darkYellow, QtGui.QColor.fromRgb(255, 85, 0)]
        self.anim_butt = [ QGraphicsRectWidget(color[j]) for j in range(4) ]
        for j in range(4):
            scene.addItem(self.anim_butt[j])
        
        self.window = QGraphicsView(scene)
        self.window.setFrameStyle(0)
        self.window.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.window.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.window.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.machine = QStateMachine()

        self.group = QState()
        self.timer = QTimer()
        self.timer.setInterval(1250)
        self.timer.setSingleShot(True)
        self.group.entered.connect(self.timer.start)
                
        # set states positions
        anim_state_rects = [ [QRect(x_max*xp/6, y_max*yp/4, 8, 8) for xp in range(7)] for yp in range(4) ]         
        self.states = [ self.createGeometryState(
                                self.anim_butt[0], anim_state_rects[0][j], self.anim_butt[1], anim_state_rects[1][j],
                                self.anim_butt[2], anim_state_rects[2][j], self.anim_butt[3], anim_state_rects[3][j],
                                self.group
                            ) for j in range(7) ]                

        self.group.setInitialState(self.states[0])


        self.animationGroup = QParallelAnimationGroup()
        self.anim = QPropertyAnimation(self.anim_butt[3], 'geometry')
        self.anim.setDuration(1250)
        self.anim.setEasingCurve(QEasingCurve.InBack)
        self.animationGroup.addAnimation(self.anim)

        self.subGroup = QSequentialAnimationGroup(self.animationGroup)
        self.subGroup.addPause(100)
        self.anim = QPropertyAnimation(self.anim_butt[2], 'geometry')
        self.anim.setDuration(1000)
        self.anim.setEasingCurve(QEasingCurve.OutElastic)
        self.subGroup.addAnimation(self.anim)

        self.subGroup = QSequentialAnimationGroup(self.animationGroup)
        self.subGroup.addPause(500)
        self.anim = QPropertyAnimation(self.anim_butt[1], 'geometry')
        self.anim.setDuration(500)
        self.anim.setEasingCurve(QEasingCurve.OutElastic)
        self.subGroup.addAnimation(self.anim)

        self.subGroup = QSequentialAnimationGroup(self.animationGroup)
        self.subGroup.addPause(750)
        self.anim = QPropertyAnimation(self.anim_butt[0], 'geometry')
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutElastic)
        self.subGroup.addAnimation(self.anim)

        self.stateSwitcher = StateSwitcher(self.machine)                       
        self.group.addTransition(self.timer.timeout, self.stateSwitcher)
        for j in range(7):
            self.stateSwitcher.addState(self.states[j], self.animationGroup)

        self.machine.addState(self.group)
        self.machine.setInitialState(self.group)
        self.machine.start()

    # 
    def createGeometryState(self, w1, rect1, w2, rect2, w3, rect3, w4, rect4, parent):
        result = QState(parent)

        result.assignProperty(w1, 'geometry', rect1)
        result.assignProperty(w1, 'geometry', rect1)
        result.assignProperty(w2, 'geometry', rect2)
        result.assignProperty(w3, 'geometry', rect3)
        result.assignProperty(w4, 'geometry', rect4)
        
        return result

    
        
    