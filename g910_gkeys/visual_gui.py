import base64
import json
from pathlib import Path
import sys
import zlib

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QStackedWidget, QToolButton, QVBoxLayout, QWidget)
from g910_gkeys.gui import Editor
from g910_gkeys.misc.layers import Config

# Losslessly compressed originals supplied by the user: G1-G9, M1-M3 and MR.
ARTWORK = 'eJztWl1v2zYU/SuE+9AOmGl+SBTpeC02PeRFAYYOeykMDG4sO9pkKbDUOGnQ/75LiZIt19s6xUuM+frB1KHIS/KSPOeK0uPg0huMyWDy7n6Vkrt4XSR59sN0wCmbDkicXefzJFtCxqdyMdTTwbu302xS3C0JFM8KyL8py9vxaLTZbOhG0ny9HAnG2AiKQP27JN78lN9DMUYY4Z5PjfAg1ZQrMx2ALUIm83hRVFdwXZQPaewAIfQ6LYb8cZGk6TjLs/iiKNf5H/H4Fat+Dg43yby8GXPR4FVSxus0gWTM2ZeOMfGNxtQ32JKPizwrh4vZKkkfxq+j5GO8npXgPvLLLCteX1R3i+RzPJZ+DTZxsrwpxx/zdH5R9cO17exORrvDn1ynye3Ps/KGJHNwoEXDW4BD7hxXFbI5xN6/4ooKFYCbIy4MVb69DLnUVHl8x/kBFVpup6KuFLVYcmqYgIrtXDGqtSKNITd3pGmjwZGz1OCwaaeGrDXE2jYi1jQfMtet+r/NZ+TDdDBq/DFqHFIvm1G7biZlUoLbfs2qdD7kk1GdU91ckvmsnA2z2SoGN/1YFHFJAliblVcr+FvQenSy3Lp2e9n4+TqdFUU1F4WdBdLOid0f6/TNq51J+g7un8W82KlY7i3IXUeJxhHSo4Eg0F3ofsSZodo0MORgGfrkIBecCg6DkdTYxEHBqOdz60ef8gDGDPcl9HKLTTUADgUB2Vyjq1La81ocSUGZbmEIqRbb21A38GVrq4VVU5GAxMimJ6GDrp9CU0/5bgy7o+16q4zvy46HJHioXANnLPL1CvJWs3Kd3L+xqwNcTmCqpOBEGSqMtMuq4lNIHyCFOVPa32EE20BxO8sOl7r0YG/Y2zuTZ/vT7rGl21w2nVgWfzv4ngyuxHNphPGplJJoQY2UR1aIltTTJIt/z5NsvM4/ZfOvFOK/Y/UnkRbnXdbi/CBtHWSqhomYIZJEASwlT8JVqBX1YJlKYkTtdwpU4K7r4pFDSsEughoOBh5ldn3X9cGgsZm1XYei2oBDYWXagbZ+azdq2gtdJ6q/JlPubaG/HqNQ1Fga4bYDCnaOLx0KA5/6WjikOfU8Ue1c0yLLMwLqOehLoB1gCAcVbHovIM4M9FsCjbgmHIrq5h0KgUMCoAkHLQ8Z3phxyLUROeh6EDrouufs1D3fHeE/EIv4e2IB9mLCJ9wHPuRPJJYr0Y9YOBLLyxML2yMWhsSCxPIUYvGo1PxIxMJ7EculwadafKo9/aenYz7Vmi6NG3yqxafa83iqNf00IkCNQI04fS46pkZ4XY3wUCNQI85DI4J+GuGjRqBGnD4XHVMjRFcjBGoEasR5aITfTyOe7e0YagRqxGlohN/VCB81AjXiPDSi54tOiS86X/5F515kyw+HtviiE190vsAXFLJf8Kkw+MTg8/SDnGMGn6pL4wqDTww+zyP4VP004tm+skONQI04DY3Y/1gaNQI14jw0ot8Hk1fv8YDi5Q8o5B5rSTygwAOKJxxQgFklvSMdULzvF3w+28knBp8YfJ5G8LlH44dZHINPDD7/d8Fnz0NsjRqBGnH6XHRMjdBdjdCoEagR56ER+t9rxJc/ATO1heI='
SVGS = json.loads(zlib.decompress(base64.b64decode(ARTWORK)))
ACTIONS = [('Do nothing', 'nothing'), ('Type text', 'typeout'),
           ('Key combination / sequence', 'shortcut'), ('Shell command', 'run'),
           ('Single key / F13-F24', 'uinput'), ('Python code (advanced)', 'python')]


class VisualEditor(Editor):
    def __init__(self):
        QMainWindow.__init__(self)
        self.path = Path.home() / '.config/g910-gkeys/config.json'
        self.original = self.path.read_bytes()
        self.data = json.loads(self.original)
        self.validator = Config()
        validated = self.validator.validate_config(self.data)
        self.rows, self.pages, self.key_buttons, self.bank_buttons = {}, {}, {}, {}
        self.dirty = False
        self.tests = []
        self.bank, self.shifted, self.key = 1, False, 1
        self.setWindowTitle('G910 Control')
        self.resize(1080, 750)
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 24, 24, 18)
        header = QHBoxLayout()
        title = QLabel('G910 CONTROL')
        title.setStyleSheet('font-size: 26px; font-weight: 700;')
        header.addWidget(title)
        header.addStretch()
        self.theme = QComboBox()
        self.theme.addItems(['System', 'Dark', 'Light'])
        self.theme.currentTextChanged.connect(self.apply_theme)
        header.addWidget(self.theme)
        layout.addLayout(header)
        layout.addWidget(QLabel('YOUR KEYS. YOUR LAYERS.'))
        banks = QHBoxLayout()
        for bank in range(1, 4):
            button = self.art_button(f'M{bank}', QSize(84, 74))
            button.clicked.connect(lambda checked=False, b=bank: self.select_bank(b))
            banks.addWidget(button)
            self.bank_buttons[bank] = button
        banks.addSpacing(22)
        self.mr = self.art_button('MR', QSize(84, 74))
        self.mr.clicked.connect(self.toggle_layer)
        banks.addWidget(self.mr)
        banks.addStretch()
        self.profile_label = QLabel()
        banks.addWidget(self.profile_label)
        layout.addLayout(banks)
        layout.addWidget(QLabel('These controls choose what you edit. Use the keyboard M/MR buttons to change the active driver profile.'))
        content = QHBoxLayout()
        board = QFrame()
        grid = QGridLayout(board)
        grid.setSpacing(12)
        for i in range(1, 10):
            button = self.art_button(f'G{i}', QSize(110, 112))
            button.clicked.connect(lambda checked=False, k=i: self.select_key(k))
            grid.addWidget(button, (i - 1) // 3, (i - 1) % 3)
            self.key_buttons[i] = button
        content.addWidget(board)
        panel = QVBoxLayout()
        self.heading = QLabel()
        self.heading.setStyleSheet('font-size: 22px; font-weight: 600;')
        panel.addWidget(self.heading)
        panel.addWidget(QLabel('ACTION'))
        self.stack = QStackedWidget()
        for profile, bindings in validated['profiles'].items():
            if profile == 'MEMORY_RECORD':
                continue
            for i in range(1, 10):
                key = f'MACRO_{i}'
                binding = bindings[key]
                page = QWidget()
                fields = QVBoxLayout(page)
                fields.setContentsMargins(0, 0, 0, 0)
                action = QComboBox()
                for label, value in ACTIONS:
                    action.addItem(label, value)
                action.setCurrentIndex(action.findData(binding['hotkey_type']))
                value = QPlainTextEdit()
                value.setPlainText(binding['do'])
                value.setPlaceholderText('Text, command, KEY_F13, or ctrl+shift+F13')
                fields.addWidget(action)
                fields.addWidget(value)
                self.rows[profile, key] = action, value
                self.pages[profile, key] = self.stack.addWidget(page)
                action.currentIndexChanged.connect(self.changed)
                value.textChanged.connect(self.changed)
        panel.addWidget(self.stack)
        self.hint = QLabel('Combos: ctrl+shift+F13 | Sequences: ctrl+c,ctrl+v\nCommands use bash. Python actions execute code. Editing never executes a binding.')
        self.hint.setWordWrap(True)
        panel.addWidget(self.hint)
        presets = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.addItems([f'F{i}' for i in range(13, 25)])
        presets.addWidget(self.preset)
        assign = QPushButton('Assign F-key')
        assign.clicked.connect(self.assign_key)
        presets.addWidget(assign)
        panel.addLayout(presets)
        content.addLayout(panel, 1)
        layout.addLayout(content, 1)
        bottom = QHBoxLayout()
        test = QPushButton('Test playground')
        test.clicked.connect(self.open_test)
        bottom.addWidget(test)
        bottom.addStretch()
        save = QPushButton('Save & Apply')
        save.setDefault(True)
        save.clicked.connect(self.save)
        bottom.addWidget(save)
        layout.addLayout(bottom)
        self.statusBar().showMessage('Ready. Existing driver and configuration format retained.')
        self.apply_theme()

    def art_button(self, name, size):
        button = QToolButton()
        button.setAccessibleName(name)
        button.setToolTip(name)
        button.setCheckable(True)
        button.setIconSize(size)
        button.setMinimumSize(size.width() + 18, size.height() + 18)
        button.setProperty('artName', name)
        return button

    def select_bank(self, bank):
        self.bank = bank
        self.refresh()

    def toggle_layer(self):
        self.shifted = not self.shifted
        self.refresh()

    def select_key(self, key):
        self.key = key
        self.refresh()

    def assign_key(self):
        action, value = self.rows[self.profile(), f'MACRO_{self.key}']
        action.setCurrentIndex(action.findData('uinput'))
        value.setPlainText('KEY_' + self.preset.currentText())

    def profile(self):
        return f'MEMORY_{self.bank}' + ('_MR' if self.shifted else '')

    def apply_theme(self, *args):
        palette = QPalette(QApplication.style().standardPalette())
        mode = self.theme.currentText()
        if mode == 'System':
            palette = QPalette(QApplication.palette())
        else:
            dark = mode == 'Dark'
            colors = {
                QPalette.ColorRole.Window: '#171b22' if dark else '#f2f4f7',
                QPalette.ColorRole.WindowText: '#edf2f7' if dark else '#17212d',
                QPalette.ColorRole.Base: '#10141a' if dark else '#ffffff',
                QPalette.ColorRole.AlternateBase: '#222933' if dark else '#e7ecf1',
                QPalette.ColorRole.Text: '#edf2f7' if dark else '#17212d',
                QPalette.ColorRole.Button: '#252d38' if dark else '#e4eaf0',
                QPalette.ColorRole.ButtonText: '#edf2f7' if dark else '#17212d',
                QPalette.ColorRole.Highlight: '#00b8df' if dark else '#006e88',
                QPalette.ColorRole.HighlightedText: '#08131a' if dark else '#ffffff',
                QPalette.ColorRole.ToolTipBase: '#252d38' if dark else '#ffffff',
                QPalette.ColorRole.ToolTipText: '#edf2f7' if dark else '#17212d',
            }
            for role, color in colors.items():
                palette.setColor(role, QColor(color))
        self.setPalette(palette)
        self.refresh()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.ApplicationPaletteChange and hasattr(self, 'theme'):
            if self.theme.currentText() == 'System':
                self.apply_theme()

    def paint_icon(self, button, selected):
        color = self.palette().color(QPalette.ColorRole.Highlight if selected else QPalette.ColorRole.WindowText).name()
        svg = SVGS[button.property('artName')].replace('#000000', color)
        size = button.iconSize()
        dpr = self.devicePixelRatioF()
        pixmap = QPixmap(round(size.width() * dpr), round(size.height() * dpr))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer = QSvgRenderer(QByteArray(svg.encode()))
        renderer.render(painter)
        painter.end()
        icon = QIcon()
        for mode in (QIcon.Mode.Normal, QIcon.Mode.Active, QIcon.Mode.Selected):
            for state in (QIcon.State.On, QIcon.State.Off):
                icon.addPixmap(pixmap, mode, state)
        button.setIcon(icon)
        button.setChecked(selected)

    def refresh(self):
        self.profile_label.setText(f'Editing M{self.bank}' + (' + MR' if self.shifted else ' / Base'))
        self.heading.setText(f'G{self.key}  /  M{self.bank}' + (' + MR' if self.shifted else ''))
        self.stack.setCurrentIndex(self.pages[self.profile(), f'MACRO_{self.key}'])
        for bank, button in self.bank_buttons.items():
            self.paint_icon(button, bank == self.bank)
        self.paint_icon(self.mr, self.shifted)
        for key, button in self.key_buttons.items():
            self.paint_icon(button, key == self.key)


def main():
    app = QApplication(sys.argv)
    try:
        window = VisualEditor()
    except Exception as error:
        QMessageBox.critical(None, 'Cannot open visual configurator', str(error))
        return 1
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
