from PyQt5 import QtWidgets, QtCore
import os

class FileSelector(QtCore.QObject):
    files_selected = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

    def choose_files(self):
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self.parent(), "选择文件")
        if files:
            self.files_selected.emit([(file, file) for file in files])  # 使用完整路径作为显示名称

    def choose_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self.parent(), "选择文件夹")
        if folder:
            self.files_selected.emit([(folder, folder)])  # 使用完整路径作为显示名称

    def get_files_from_folder(self, folder):
        files = []
        for root, _, filenames in os.walk(folder):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                relative_path = os.path.relpath(full_path, folder)
                files.append((full_path, relative_path))
        return files