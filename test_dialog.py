#!/usr/bin/env python3
import sys
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QLabel,
)
from PySide6.QtCore import Qt
import time


class TestDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Dialog")
        self.setModal(True)
        self.resize(300, 200)

        layout = QVBoxLayout(self)

        # Test combo box
        layout.addWidget(QLabel("Test ComboBox:"))
        self.combo = QComboBox()
        self.combo.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        self.combo.setMinimumContentsLength(20)

        # Add test items
        self.combo.addItem("-- Select Item --", None)
        for i in range(30):  # Similar to your 29 categories
            self.combo.addItem(f"Test Item {i+1}", i + 1)

        layout.addWidget(self.combo)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    print("Creating test dialog...")
    start = time.time()
    dialog = TestDialog()

    print("Showing dialog...")
    show_start = time.time()
    result = dialog.exec()
    elapsed = time.time() - show_start

    print(f"Dialog completed in {elapsed:.2f}s")
    print(f"Selected: {dialog.combo.currentText()}")

    sys.exit(0)
