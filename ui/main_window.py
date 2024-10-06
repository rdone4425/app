from PyQt5 import QtWidgets, QtCore, QtGui
from github import Github
from github_uploader.ui.upload_thread import UploadThread
from github_uploader.ui.file_selector import FileSelector
from github_uploader.ui.repo_manager import RepoManager
from github_uploader.utils.settings import load_settings, save_settings, load_repos_cache, save_repos_cache
from github_uploader.utils.encryption import decrypt_token, encrypt_token
import os
import json
import requests

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GitHub文件上传器")
        self.setGeometry(100, 100, 800, 600)
        self.github = None
        self.file_selector = FileSelector(self)
        self.file_selector.files_selected.connect(self.add_files_to_list)
        self.repo_manager = None
        self.setup_ui()
        self.setup_status_bar()
        self.load_settings()
        self.load_repos_cache()
        self.auto_get_repos()  # 添加这行

    def setup_ui(self):
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        layout = QtWidgets.QVBoxLayout(central_widget)

        # Token 输入
        token_layout = QtWidgets.QHBoxLayout()
        token_label = QtWidgets.QLabel("GitHub Token:")
        self.token_input = QtWidgets.QLineEdit()
        self.token_input.setEchoMode(QtWidgets.QLineEdit.Password)
        self.save_token_checkbox = QtWidgets.QCheckBox("保存 Token")
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        token_layout.addWidget(self.save_token_checkbox)
        layout.addLayout(token_layout)

        # 添加搜索框
        search_layout = QtWidgets.QHBoxLayout()
        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("搜索仓库...")
        self.search_button = QtWidgets.QPushButton("搜索")
        self.search_button.clicked.connect(self.search_repos)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # 仓库列表和操作按钮
        repo_layout = QtWidgets.QHBoxLayout()
        
        self.repo_list = QtWidgets.QListWidget()
        repo_layout.addWidget(self.repo_list, 3)  # 仓库列表占据更多空间
        
        repo_buttons_layout = QtWidgets.QVBoxLayout()
        self.get_repos_button = QtWidgets.QPushButton("获取仓库列表")
        self.get_repos_button.clicked.connect(self.get_repos)
        self.create_repo_button = QtWidgets.QPushButton("新建仓库")
        self.create_repo_button.clicked.connect(self.create_repo)
        self.delete_repo_button = QtWidgets.QPushButton("删除仓库")
        self.delete_repo_button.clicked.connect(self.delete_repo)
        repo_buttons_layout.addWidget(self.get_repos_button)
        repo_buttons_layout.addWidget(self.create_repo_button)
        repo_buttons_layout.addWidget(self.delete_repo_button)
        repo_buttons_layout.addStretch(1)  # 添加弹性空间
        repo_layout.addLayout(repo_buttons_layout, 1)
        
        layout.addLayout(repo_layout)

        # 文件列表
        self.file_list = QtWidgets.QListWidget()
        self.file_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.file_list.setMaximumHeight(30)  # 设置最大高度为100像素
        layout.addWidget(self.file_list)

        # 文件操作按钮
        file_buttons_layout = QtWidgets.QHBoxLayout()
        self.choose_file_button = QtWidgets.QPushButton("选择文件")
        self.choose_file_button.clicked.connect(self.file_selector.choose_files)
        self.choose_folder_button = QtWidgets.QPushButton("选择文件夹")
        self.choose_folder_button.clicked.connect(self.file_selector.choose_folder)
        self.clear_file_list_button = QtWidgets.QPushButton("清空文件列表")
        self.clear_file_list_button.clicked.connect(self.clear_file_list)
        file_buttons_layout.addWidget(self.choose_file_button)
        file_buttons_layout.addWidget(self.choose_folder_button)
        file_buttons_layout.addWidget(self.clear_file_list_button)
        layout.addLayout(file_buttons_layout)

        # 上传按钮
        self.upload_button = QtWidgets.QPushButton("上传")
        self.upload_button.clicked.connect(self.upload)
        layout.addWidget(self.upload_button)

        # 进度条
        self.progress_bar = QtWidgets.QProgressBar()
        layout.addWidget(self.progress_bar)

    def setup_status_bar(self):
        # 创建状态栏小部件
        self.status_icon = QtWidgets.QLabel()
        self.status_message = QtWidgets.QLabel("就绪")
        self.repo_label = QtWidgets.QLabel()
        self.progress_label = QtWidgets.QLabel()

        # 设置固定宽度
        self.status_icon.setFixedWidth(20)
        self.status_message.setFixedWidth(100)
        self.repo_label.setFixedWidth(200)
        self.progress_label.setFixedWidth(100)

        # 添加小部件到状态栏
        self.statusBar().addPermanentWidget(self.status_icon)
        self.statusBar().addPermanentWidget(self.status_message)
        self.statusBar().addPermanentWidget(self.repo_label)
        self.statusBar().addPermanentWidget(self.progress_label)

        # 设置初始图标
        self.set_status_icon("ready")

    def set_status_icon(self, status):
        icon = QtGui.QIcon()
        if status == "ready":
            icon = QtGui.QIcon("path/to/ready_icon.png")
        elif status == "uploading":
            icon = QtGui.QIcon("path/to/uploading_icon.png")
        elif status == "error":
            icon = QtGui.QIcon("path/to/error_icon.png")
        self.status_icon.setPixmap(icon.pixmap(16, 16))

    def update_status(self, message, status="ready", repo="", progress=""):
        self.status_message.setText(message)
        self.set_status_icon(status)
        self.repo_label.setText(f"仓库: {repo}" if repo else "")
        self.progress_label.setText(progress)

        if status == "error":
            self.status_message.setStyleSheet("color: red;")
        else:
            self.status_message.setStyleSheet("")

    def add_files_to_list(self, files):
        for full_path, display_name in files:
            if full_path not in [self.file_list.item(i).data(QtCore.Qt.UserRole) for i in range(self.file_list.count())]:
                item = QtWidgets.QListWidgetItem(full_path)  # 使用完整路径作为显示文本
                item.setData(QtCore.Qt.UserRole, full_path)
                self.file_list.addItem(item)

    def get_repos(self):
        token = self.token_input.text()
        if not token:
            QtWidgets.QMessageBox.warning(self, "错误", "请输入GitHub Token")
            return

        self.github = Github(token)
        self.repo_manager = RepoManager(self.github, self)
        self.repo_manager.repo_deleted.connect(self.on_repo_deleted)
        self.repo_manager.repo_created.connect(self.on_repo_created)
        self.repo_manager.repos_searched.connect(self.update_repo_list)
        try:
            repos = [repo.full_name for repo in self.github.get_user().get_repos()]
            self.repo_list.clear()
            self.repo_list.addItems(repos)
            self.save_repos_cache()
            self.update_status("仓库列表已更新", "ready")
        except Exception as e:
            self.update_status(f"获取仓库列表失败", "error")
            QtWidgets.QMessageBox.warning(self, "错误", f"获取仓库列表失败: {str(e)}")

    def delete_repo(self):
        if not self.github:
            QtWidgets.QMessageBox.warning(self, "错误", "请先获取仓库列表")
            return

        if not self.repo_list.currentItem():
            QtWidgets.QMessageBox.warning(self, "错误", "请选择要删除的仓库")
            return

        repo_name = self.repo_list.currentItem().text()
        self.repo_manager.delete_repo(repo_name)

    def on_repo_deleted(self, repo_name):
        items = self.repo_list.findItems(repo_name, QtCore.Qt.MatchExactly)
        for item in items:
            self.repo_list.takeItem(self.repo_list.row(item))
        self.save_repos_cache()

    def on_repo_created(self, repo_name):
        self.repo_list.addItem(repo_name)
        self.save_repos_cache()

    def create_repo(self):
        if not self.github:
            QtWidgets.QMessageBox.warning(self, "错误", "请先获取仓库列表")
            return

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("新建仓库")
        layout = QtWidgets.QVBoxLayout(dialog)

        # 仓库名称
        name_layout = QtWidgets.QHBoxLayout()
        name_label = QtWidgets.QLabel("仓库名称:")
        name_input = QtWidgets.QLineEdit()
        name_layout.addWidget(name_label)
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)

        # 仓库描述
        description_layout = QtWidgets.QHBoxLayout()
        description_label = QtWidgets.QLabel("描述 (可选):")
        description_input = QtWidgets.QLineEdit()
        description_layout.addWidget(description_label)
        description_layout.addWidget(description_input)
        layout.addLayout(description_layout)

        # 私有仓库选项
        private_checkbox = QtWidgets.QCheckBox("私有仓库")
        layout.addWidget(private_checkbox)

        # README 文件选项
        readme_checkbox = QtWidgets.QCheckBox("初始化仓库时添加 README 文件")
        readme_checkbox.setChecked(True)  # 默认选中
        layout.addWidget(readme_checkbox)

        # .gitignore 文件选项
        gitignore_layout = QtWidgets.QHBoxLayout()
        gitignore_checkbox = QtWidgets.QCheckBox("添加 .gitignore 文件")
        gitignore_combo = QtWidgets.QComboBox()
        gitignore_combo.addItems(["None", "Python", "Node", "Java", "C++"])
        gitignore_combo.setEnabled(False)
        gitignore_checkbox.stateChanged.connect(lambda state: gitignore_combo.setEnabled(state == QtCore.Qt.Checked))
        gitignore_layout.addWidget(gitignore_checkbox)
        gitignore_layout.addWidget(gitignore_combo)
        layout.addLayout(gitignore_layout)

        # 许可证选项
        license_layout = QtWidgets.QHBoxLayout()
        license_checkbox = QtWidgets.QCheckBox("添加许可证")
        license_combo = QtWidgets.QComboBox()
        license_combo.addItems(["None", "MIT License", "Apache License 2.0", "GNU GPLv3"])
        license_combo.setEnabled(False)
        license_checkbox.stateChanged.connect(lambda state: license_combo.setEnabled(state == QtCore.Qt.Checked))
        license_layout.addWidget(license_checkbox)
        license_layout.addWidget(license_combo)
        layout.addLayout(license_layout)

        # 确认和取消按钮
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            repo_name = name_input.text().strip()
            if not repo_name:
                QtWidgets.QMessageBox.warning(self, "错误", "仓库名称不能为空")
                return

            description = description_input.text().strip()
            is_private = private_checkbox.isChecked()
            auto_init = readme_checkbox.isChecked()
            
            # 修改这里的 gitignore_template 设置
            gitignore_template = None
            if gitignore_checkbox.isChecked():
                gitignore_choice = gitignore_combo.currentText()
                if gitignore_choice != "None":
                    if gitignore_choice == "Node":
                        gitignore_template = "Node"
                    else:
                        gitignore_template = gitignore_choice

            license_template = None
            if license_checkbox.isChecked():
                license_choice = license_combo.currentText()
                if license_choice == "MIT License":
                    license_template = "mit"
                elif license_choice == "Apache License 2.0":
                    license_template = "apache-2.0"
                elif license_choice == "GNU GPLv3":
                    license_template = "gpl-3.0"

            self.repo_manager.create_repo(
                repo_name, 
                description, 
                is_private, 
                auto_init, 
                gitignore_template, 
                license_template
            )

    def upload(self):
        if not self.github:
            QtWidgets.QMessageBox.warning(self, "错误", "请先获取仓库列表")
            return

        if not self.repo_list.currentItem():
            QtWidgets.QMessageBox.warning(self, "错误", "请选择一个仓库")
            return

        if self.file_list.count() == 0:
            QtWidgets.QMessageBox.warning(self, "错误", "请选择要上传的文件或文件夹")
            return

        repo_name = self.repo_list.currentItem().text()
        items = [(self.file_list.item(i).data(QtCore.Qt.UserRole), self.file_list.item(i).text()) for i in range(self.file_list.count())]
        
        # 使用默认的提交信息
        commit_message = "Upload files via GitHub Uploader"

        self.upload_thread = UploadThread(items, repo_name, commit_message, self.github)
        self.upload_thread.progress_update.connect(self.update_progress)
        self.upload_thread.finished.connect(self.upload_finished)
        self.upload_thread.start()

        self.upload_button.setEnabled(False)
        self.update_status("正在上传...", "uploading", self.repo_list.currentItem().text())

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.update_status(message, "uploading", self.repo_list.currentItem().text(), f"{value}%")

    def upload_finished(self):
        self.upload_button.setEnabled(True)
        self.progress_bar.setValue(100)
        self.update_status("上传完成", "ready", self.repo_list.currentItem().text(), "100%")
        QtWidgets.QMessageBox.information(self, "上传完成", "文件上传成功")

    def load_settings(self):
        settings = load_settings()
        if 'token' in settings:
            self.token_input.setText(decrypt_token(settings['token']))
            self.save_token_checkbox.setChecked(True)
        if 'last_repo' in settings:
            items = self.repo_list.findItems(settings['last_repo'], QtCore.Qt.MatchExactly)
            if items:
                self.repo_list.setCurrentItem(items[0])

    def save_settings(self):
        settings = {}
        if self.save_token_checkbox.isChecked():
            settings['token'] = encrypt_token(self.token_input.text())
        if self.repo_list.currentItem():
            settings['last_repo'] = self.repo_list.currentItem().text()
        save_settings(settings)

    def load_repos_cache(self):
        repos = load_repos_cache()
        self.repo_list.clear()
        self.repo_list.addItems(repos)

    def save_repos_cache(self):
        repos = [self.repo_list.item(i).text() for i in range(self.repo_list.count())]
        save_repos_cache(repos)

    def show_about(self):
        QtWidgets.QMessageBox.about(self, "关于", "GitHub文件上传器 v1.0\n\n作者：Your Name\n\n这是一个用于上传文件到GitHub的简单工具。")

    def check_for_updates(self):
        try:
            response = requests.get("https://api.github.com/repos/yourusername/github-uploader/releases/latest")
            latest_version = response.json()["tag_name"]
            current_version = "v1.0"  # 替换为您的当前版本
            if latest_version > current_version:
                QtWidgets.QMessageBox.information(self, "更新可用", f"有新版本可用：{latest_version}\n请访问GitHub页面下载最新版本。")
            else:
                QtWidgets.QMessageBox.information(self, "无更新", "您使用的已经是最新版本。")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "检查更新失败", f"无法检查更新：{str(e)}")

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

    def clear_file_list(self):
        self.file_list.clear()

    def search_repos(self):
        query = self.search_input.text().strip()
        if not query:
            return

        # 先搜索本地缓存
        cached_repos = [self.repo_list.item(i).text() for i in range(self.repo_list.count())]
        local_results = [repo for repo in cached_repos if query.lower() in repo.lower()]

        if local_results:
            self.update_repo_list(local_results)
        else:
            # 如果本地没有结果，搜索GitHub
            if self.github and self.repo_manager:
                self.repo_manager.search_repos(query)
            else:
                QtWidgets.QMessageBox.warning(self, "错误", "请先获取仓库列表")

    def update_repo_list(self, repos):
        self.repo_list.clear()
        self.repo_list.addItems(repos)

    def auto_get_repos(self):
        if self.token_input.text():
            self.get_repos()