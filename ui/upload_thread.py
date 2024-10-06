from PyQt5 import QtCore
from github import Github
import os

class UploadThread(QtCore.QThread):
    progress_update = QtCore.pyqtSignal(int, str)
    finished = QtCore.pyqtSignal()

    def __init__(self, items, repo_name, commit_message, github):
        super().__init__()
        self.items = items
        self.repo_name = repo_name
        self.commit_message = commit_message
        self.github = github

    def run(self):
        try:
            repo = self.github.get_repo(self.repo_name)
            total_items = sum(self.count_files(item[0]) for item in self.items)
            processed_items = 0
            
            for full_path, _ in self.items:
                if os.path.isdir(full_path):
                    processed_items = self.upload_folder(repo, full_path, "", processed_items, total_items)
                else:
                    self.upload_file(repo, full_path, os.path.basename(full_path))
                    processed_items += 1
                    progress = int((processed_items / total_items) * 100)
                    self.progress_update.emit(progress, f"正在上传 {full_path}...")

            self.finished.emit()
        except Exception as e:
            self.progress_update.emit(0, f"上传失败: {str(e)}")

    def count_files(self, path):
        if os.path.isfile(path):
            return 1
        else:
            return sum(len(files) for _, _, files in os.walk(path))

    def upload_file(self, repo, full_path, relative_path):
        with open(full_path, 'rb') as file:
            content = file.read()
        
        try:
            contents = repo.get_contents(relative_path)
            repo.update_file(contents.path, self.commit_message, content, contents.sha)
        except:
            repo.create_file(relative_path, self.commit_message, content)

    def upload_folder(self, repo, folder_path, repo_path, processed_items, total_items):
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.join(repo_path, os.path.relpath(full_path, folder_path))
                relative_path = relative_path.replace('\\', '/')  # 确保使用正斜杠
                self.upload_file(repo, full_path, relative_path)
                processed_items += 1
                progress = int((processed_items / total_items) * 100)
                self.progress_update.emit(progress, f"正在上传 {relative_path}...")
        return processed_items