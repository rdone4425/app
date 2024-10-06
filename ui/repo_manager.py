from PyQt5 import QtWidgets, QtCore
from github import Github

class RepoManager(QtCore.QObject):
    repo_deleted = QtCore.pyqtSignal(str)
    repo_created = QtCore.pyqtSignal(str)
    repos_searched = QtCore.pyqtSignal(list)

    def __init__(self, github, parent=None):
        super().__init__(parent)
        self.github = github

    def delete_repo(self, repo_name):
        confirm = QtWidgets.QMessageBox.question(
            self.parent(),
            "确认删除",
            f"您确定要删除仓库 {repo_name} 吗？\n此操作不可逆！",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        
        if confirm == QtWidgets.QMessageBox.Yes:
            try:
                repo = self.github.get_repo(repo_name)
                repo.delete()
                self.repo_deleted.emit(repo_name)
                QtWidgets.QMessageBox.information(self.parent(), "成功", f"仓库 {repo_name} 已成功删除")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self.parent(), "错误", f"删除仓库失败: {str(e)}")

    def create_repo(self, repo_name, description, is_private, auto_init=True, gitignore_template=None, license_template=None):
        try:
            repo_args = {
                "name": repo_name,
                "description": description,
                "private": is_private,
                "auto_init": auto_init
            }
            if gitignore_template:
                repo_args["gitignore_template"] = gitignore_template
            if license_template:
                repo_args["license_template"] = license_template

            new_repo = self.github.get_user().create_repo(**repo_args)
            self.repo_created.emit(new_repo.full_name)
            QtWidgets.QMessageBox.information(self.parent(), "成功", f"仓库 {new_repo.full_name} 已成功创建")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.parent(), "错误", f"创建仓库失败: {str(e)}")

    def search_repos(self, query):
        try:
            repos = [repo.full_name for repo in self.github.search_repositories(query=query, user=self.github.get_user().login)]
            self.repos_searched.emit(repos)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self.parent(), "错误", f"搜索仓库失败: {str(e)}")