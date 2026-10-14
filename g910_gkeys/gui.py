import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

import uinput
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QTabWidget, QTableWidget,
    QVBoxLayout, QWidget)
from g910_gkeys.misc.layers import Config


class TestPad(QPlainTextEdit):
    def __init__(self, log):
        super().__init__()
        self.log = log
        self.setPlaceholderText('Click here, select your profile on the keyboard, then press a G-key.')

    def event(self, event):
        if event.type() == event.Type.ShortcutOverride:
            event.accept()
            return True
        return super().event(event)

    def record(self, event, kind):
        combo = QKeySequence(event.keyCombination()).toString()
        self.log.appendPlainText(f'{kind}: {combo} | text={event.text()!r} | repeat={event.isAutoRepeat()}')

    def keyPressEvent(self, event):
        self.record(event, 'PRESS')
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        self.record(event, 'RELEASE')
        super().keyReleaseEvent(event)


class TestWindow(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle('G910 - physical key test')
        self.resize(760, 520)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Save & Apply first. GUI tabs do not switch the hardware profile.'))
        layout.addWidget(QLabel('Commands really execute when their G-key is pressed; command output is not captured here.'))
        log = QPlainTextEdit()
        log.setReadOnly(True)
        log.document().setMaximumBlockCount(500)
        self.pad = TestPad(log)
        layout.addWidget(self.pad)
        layout.addWidget(log)
        clear = QPushButton('Clear')
        clear.clicked.connect(lambda: (self.pad.clear(), log.clear()))
        layout.addWidget(clear)


class Editor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.path = Path.home() / '.config/g910-gkeys/config.json'
        self.original = self.path.read_bytes()
        self.data = json.loads(self.original)
        self.validator = Config()
        validated = self.validator.validate_config(self.data)
        self.dirty = False
        self.tests = []
        self.rows = {}
        self.setWindowTitle('G910 Macro Configuration')
        self.resize(1000, 720)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.addWidget(QLabel(str(self.path)))
        layout.addWidget(QLabel('Shortcut syntax: ctrl+shift+F13 | Sequence: ctrl+c,ctrl+v | Lowercase modifier names.'))
        layout.addWidget(QLabel('Commands use bash. Python actions execute code. Nothing runs merely by editing a binding.'))
        tabs = QTabWidget()
        layout.addWidget(tabs)
        for bank in range(1, 4):
            for shifted in (False, True):
                profile = f'MEMORY_{bank}' + ('_MR' if shifted else '')
                table = QTableWidget(9, 3)
                table.setHorizontalHeaderLabels(['G-key', 'Action', 'Value'])
                table.setColumnWidth(0, 70)
                table.setColumnWidth(1, 180)
                table.horizontalHeader().setStretchLastSection(True)
                tabs.addTab(table, f'M{bank}' + (' + MR' if shifted else ''))
                for i in range(1, 10):
                    key = f'MACRO_{i}'
                    binding = validated['profiles'][profile][key]
                    label = QLabel(f'G{i}')
                    action = QComboBox()
                    for title, value in [('Nothing', 'nothing'), ('Type text', 'typeout'),
                        ('Key combo / sequence', 'shortcut'), ('Shell command', 'run'),
                        ('Single key / F13-F24', 'uinput'), ('Python code (advanced)', 'python')]:
                        action.addItem(title, value)
                    action.setCurrentIndex(action.findData(binding['hotkey_type']))
                    value = QPlainTextEdit()
                    value.setPlainText(binding['do'])
                    table.setCellWidget(i - 1, 0, label)
                    table.setCellWidget(i - 1, 1, action)
                    table.setCellWidget(i - 1, 2, value)
                    table.setRowHeight(i - 1, 56)
                    self.rows[profile, key] = (action, value)
                    action.currentIndexChanged.connect(self.changed)
                    value.textChanged.connect(self.changed)
        controls = QHBoxLayout()
        layout.addLayout(controls)
        preset = QComboBox()
        preset.addItems([f'F{i}' for i in range(13, 25)])
        controls.addWidget(preset)
        assign = QPushButton('Assign F-key to selected row')
        def assign_key():
            table = tabs.currentWidget()
            row = table.currentRow()
            if row < 0:
                QMessageBox.information(self, 'Select a key', 'Click the G-key row first.')
                return
            action = table.cellWidget(row, 1)
            action.setCurrentIndex(action.findData('uinput'))
            table.cellWidget(row, 2).setPlainText('KEY_' + preset.currentText())
        assign.clicked.connect(assign_key)
        controls.addWidget(assign)
        test = QPushButton('Open test window')
        test.clicked.connect(self.open_test)
        controls.addWidget(test)
        save = QPushButton('Save & Apply')
        save.clicked.connect(self.save)
        controls.addWidget(save)
        self.statusBar().showMessage('Ready. MR layers without explicit bindings display their legacy fallback.')

    def changed(self, *args):
        self.dirty = True
        self.setWindowTitle('G910 Macro Configuration *')

    def open_test(self):
        window = TestWindow(self)
        self.tests.append(window)
        window.show()
        window.pad.setFocus()

    def save(self):
        temporary = None
        try:
            if self.path.read_bytes() != self.original:
                raise ValueError('Configuration changed on disk. Close and reopen the GUI before saving.')
            data = json.loads(json.dumps(self.data))
            profiles = data.setdefault('profiles', {})
            for (profile, key), (action, value) in self.rows.items():
                kind, text = action.currentData(), value.toPlainText()
                if kind == 'uinput' and (not text.startswith('KEY_') or not hasattr(uinput, text)):
                    raise ValueError(f'{profile}/{key}: choose a valid KEY_* name, for example KEY_F13.')
                profiles.setdefault(profile, {})[key] = {'hotkey_type': kind, 'do': text}
            self.validator.validate_config(data)
            payload = (json.dumps(data, indent=4, ensure_ascii=False) + '\n').encode()
            backup = self.path.with_name(self.path.name + '.' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.bak')
            shutil.copy2(self.path, backup)
            with tempfile.NamedTemporaryFile(dir=self.path.parent, prefix='.g910-', delete=False) as f:
                temporary = f.name
                f.write(payload)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary, self.path)
            temporary = None
            self.original = payload
            self.data = data
            self.dirty = False
            self.setWindowTitle('G910 Macro Configuration')
            result = subprocess.run(['systemctl', '--user', 'reload', 'g910-gkeys.service'],
                                    capture_output=True, text=True, timeout=10)
            if result.returncode:
                QMessageBox.warning(self, 'Saved, but not applied',
                    'Configuration saved. Start the service or restart your foreground driver.\n' + result.stderr)
            else:
                self.statusBar().showMessage('Saved and reload requested. Backup: ' + backup.name)
        except Exception as error:
            QMessageBox.critical(self, 'Save / apply error', str(error))
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)

    def closeEvent(self, event):
        if self.dirty:
            answer = QMessageBox.question(self, 'Unsaved changes', 'Discard unsaved changes?',
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Discard:
                event.ignore()
                return
        event.accept()


def main():
    app = QApplication(sys.argv)
    try:
        window = Editor()
    except Exception as error:
        QMessageBox.critical(None, 'Cannot load configuration', str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
