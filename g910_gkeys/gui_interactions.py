import json
import sys

from PySide6.QtCore import QEvent, QMimeData, QObject, Qt
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QMenu, QMessageBox, QPushButton)
from g910_gkeys.visual_gui import VisualEditor
from g910_gkeys.tray import TrayController

MIME = 'application/x-g910-binding'


class BindingInteractions(QObject):
    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.press = None
        self.copied = None
        self.button_keys = {button: key for key, button in window.key_buttons.items()}
        all_buttons = list(window.key_buttons.values()) + list(window.bank_buttons.values()) + [window.mr]
        for button in all_buttons:
            button.setAutoRaise(True)
            button.setStyleSheet('''
                QToolButton { background: transparent; border: none; padding: 8px; }
                QToolButton:hover, QToolButton:pressed, QToolButton:checked {
                    background: transparent; border: none;
                }
                QToolButton:focus { border-bottom: 2px solid palette(highlight); }
            ''')
        for button, key in self.button_keys.items():
            button.setAcceptDrops(True)
            button.installEventFilter(self)
            button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            button.customContextMenuRequested.connect(
                lambda point, b=button: self.context_menu(b, point))
            button.setToolTip(f'G{key}: click to edit, drag to copy, right-click for copy/paste')
        for action, value in window.rows.values():
            fields = value.parentWidget().layout()
            fields.removeWidget(value)
            line = QHBoxLayout()
            line.addWidget(value, 1)
            clear = QPushButton('Clear')
            clear.setToolTip('Clear the value, keeping the action type. Choose Do nothing to disable the binding.')
            clear.clicked.connect(lambda checked=False, editor=value: self.clear_value(editor))
            line.addWidget(clear, 0, Qt.AlignmentFlag.AlignTop)
            fields.addLayout(line)
        window.statusBar().showMessage('Drag keys to copy bindings. Right-click Copy/Paste also works between profiles. Save & Apply when ready.')

    def clear_value(self, editor):
        editor.clear()
        editor.setFocus()

    def binding(self, key):
        action, value = self.window.rows[self.window.profile(), f'MACRO_{key}']
        return {'hotkey_type': action.currentData(), 'do': value.toPlainText()}

    def paste(self, key, binding):
        if not isinstance(binding, dict):
            return
        kind, text = binding.get('hotkey_type'), binding.get('do')
        action, value = self.window.rows[self.window.profile(), f'MACRO_{key}']
        if not isinstance(kind, str) or not isinstance(text, str) or action.findData(kind) < 0:
            return
        old = self.binding(key)
        if old == binding:
            return
        if old['hotkey_type'] != 'nothing' and old['do']:
            answer = QMessageBox.question(self.window, 'Replace binding?',
                f'Replace G{key} in {self.window.profile()}? The source binding will be kept.',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        action.setCurrentIndex(action.findData(kind))
        value.setPlainText(text)
        self.window.select_key(key)
        self.window.statusBar().showMessage(f'Copied binding to G{key}. Not saved yet; use Save & Apply.')

    def context_menu(self, button, point):
        key = self.button_keys[button]
        menu = QMenu(self.window)
        copy = menu.addAction('Copy binding')
        paste = menu.addAction('Paste binding')
        paste.setEnabled(self.copied is not None)
        selected = menu.exec(button.mapToGlobal(point))
        if selected == copy:
            self.copied = dict(self.binding(key))
            self.window.statusBar().showMessage(f'Copied G{key} from {self.window.profile()}. Switch profiles and paste onto another key.')
        elif selected == paste and self.copied is not None:
            self.paste(key, self.copied)

    def internal_drag(self, event):
        return event.source() in self.button_keys and event.mimeData().hasFormat(MIME)

    def eventFilter(self, button, event):
        kind = event.type()
        if kind == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.press = (button, event.position().toPoint())
        elif kind == QEvent.Type.MouseButtonRelease:
            self.press = None
        elif kind == QEvent.Type.MouseMove and self.press is not None:
            source, origin = self.press
            if source is button and event.buttons() & Qt.MouseButton.LeftButton:
                if (event.position().toPoint() - origin).manhattanLength() >= QApplication.startDragDistance():
                    self.press = None
                    mime = QMimeData()
                    mime.setData(MIME, json.dumps(self.binding(self.button_keys[button])).encode())
                    drag = QDrag(button)
                    drag.setMimeData(mime)
                    drag.setPixmap(button.icon().pixmap(button.iconSize()))
                    drag.exec(Qt.DropAction.CopyAction)
                    button.setDown(False)
                    self.window.refresh()
                    return True
        elif kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
            if self.internal_drag(event):
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
            else:
                event.ignore()
            return True
        elif kind == QEvent.Type.Drop:
            if self.internal_drag(event):
                try:
                    binding = json.loads(bytes(event.mimeData().data(MIME)))
                except (ValueError, UnicodeError):
                    event.ignore()
                    return True
                self.paste(self.button_keys[button], binding)
                event.setDropAction(Qt.DropAction.CopyAction)
                event.accept()
            else:
                event.ignore()
            return True
        return super().eventFilter(button, event)


def main():
    app = QApplication(sys.argv)
    try:
        window = VisualEditor()
        window.binding_interactions = BindingInteractions(window)
        window.tray_controller = TrayController(window)
    except Exception as error:
        QMessageBox.critical(None, 'Cannot open configurator', str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
