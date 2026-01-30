"""
自定义异常类
定义项目中使用的自定义异常
"""


class TeamManageException(Exception):
    """Team 管理系统基础异常"""
    pass


class TeamImportError(TeamManageException):
    """Team 导入异常"""
    def __init__(self, message: str, email: str = None, account_id: str = None):
        super().__init__(message)
        self.email = email
        self.account_id = account_id


class TeamSyncError(TeamManageException):
    """Team 同步异常"""
    def __init__(self, message: str, team_id: int = None):
        super().__init__(message)
        self.team_id = team_id


class RedemptionError(TeamManageException):
    """兑换异常"""
    def __init__(self, message: str, code: str = None, email: str = None):
        super().__init__(message)
        self.code = code
        self.email = email


class AuthenticationError(TeamManageException):
    """认证异常"""
    pass


class TokenDecryptError(TeamManageException):
    """Token 解密异常"""
    def __init__(self, message: str, team_id: int = None):
        super().__init__(message)
        self.team_id = team_id


class ChatGPTAPIError(TeamManageException):
    """ChatGPT API 调用异常"""
    def __init__(self, message: str, status_code: int = None, endpoint: str = None):
        super().__init__(message)
        self.status_code = status_code
        self.endpoint = endpoint
