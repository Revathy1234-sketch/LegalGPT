from enum import Enum


class UserRole(str, Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    READER = "Reader"
