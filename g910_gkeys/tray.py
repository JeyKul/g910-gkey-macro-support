from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon


def key_icon():
    icon = QIcon()
    for size in (22, 32, 48, 64, 128):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(size / 64, size / 64)
        painter.setPen(QPen(QColor('#8eabb8'), 1.5))
        painter.setBrush(QColor('#171b22'))
        painter.drawRoundedRect(QRectF(3, 3, 58, 58), 12, 12)
        painter.setPen(QPen(QColor('#00c9ed'), 3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(QRectF(12, 11, 40, 42), 7, 7)
        font = QFont('Sans Serif')
        font.setPixelSize(30)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(12, 10, 40, 42), Qt.AlignmentFlag.AlignCenter, 'G')
        painter.end()
        icon.addPixmap(pixmap)
    return icon


class TrayController(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.quitting = False
        self.explained = False
        self.tray = None
        window.setWindowIcon(key_icon())
        if not QSystemTrayIcon.isSystemTrayAvailable():
            window.statusBar().showMessage('No system tray detected. Closing the window exits normally.')
            return
        self.tray = QSystemTrayIcon(key_icon(), window)
        self.tray.setToolTip('G910 Control - configurator (driver runs separately)')
        self.menu = QMenu(window)
        self.menu.addAction('G910 Control').setEnabled(False)
        self.menu.addSeparator()
        self.menu.addAction('Open configurator', self.show_window)
        self.menu.addAction('Test playground', self.show_test)
        self.menu.addSeparator()
        self.menu.addAction('Quit configurator', self.quit)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.activated)
        window.installEventFilter(self)
        QApplication.instance().setQuitOnLastWindowClosed(False)
        self.tray.show()

    def show_window(self):
        self.window.showNormal()
        self.window.raise_()
        self.window.activateWindow()

    def show_test(self):
        self.show_window()
        self.window.open_test()

    def activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_window()

    def quit(self):
        self.show_window()
        if self.window.dirty:
            answer = QMessageBox.question(self.window, 'Unsaved changes',
                'Discard unsaved changes and quit the configurator? The keyboard driver will keep running.',
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Discard:
                return
            self.window.dirty = False
        self.quitting = True
        if self.tray is not None:
            self.tray.hide()
        self.window.close()
        QApplication.instance().quit()

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() == QEvent.Type.Close and not self.quitting:
            if QSystemTrayIcon.isSystemTrayAvailable() and self.tray.isVisible():
                event.ignore()
                self.window.hide()
                for test in self.window.tests:
                    test.hide()
                if not self.explained:
                    self.explained = True
                    self.tray.showMessage('G910 Control',
                        'Configurator is still running in the tray. Unsaved edits are retained. Use Quit configurator to exit.')
                return True
            QApplication.instance().setQuitOnLastWindowClosed(True)
        return super().eventFilter(watched, event)
