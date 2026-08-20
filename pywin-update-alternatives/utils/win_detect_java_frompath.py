import os
import winreg


class win_detect_java_frompath:
    """Detect Java installations from Windows registry PATH entries."""

    _SYS_REG_PATH = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    _USER_REG_PATH = r'Environment'

    @classmethod
    def _get_path_from_reg(cls, hive, reg_path):
        """Read the Path value from a registry key."""
        try:
            key = winreg.OpenKey(hive, reg_path)
            value, _ = winreg.QueryValueEx(key, 'Path')
            winreg.CloseKey(key)
            return value
        except OSError:
            return ''

    @classmethod
    def get_as_user_env(cls):
        """Return the user-scope PATH string from the registry."""
        return cls._get_path_from_reg(winreg.HKEY_CURRENT_USER, cls._USER_REG_PATH)

    @classmethod
    def get_as_sys_env(cls):
        """Return the system-scope PATH string from the registry."""
        return cls._get_path_from_reg(winreg.HKEY_LOCAL_MACHINE, cls._SYS_REG_PATH)

    @classmethod
    def _filter_java_paths(cls, path_string):
        """Split a PATH string and return (jdk_paths, jre_paths) tuples."""
        entries = [e.strip() for e in path_string.split(';') if e.strip()]
        java_entries = [e for e in entries if 'java' in e.lower()]
        jdk_paths = [e for e in java_entries if 'jre' not in e.lower()]
        jre_paths = [e for e in java_entries if 'jdk' not in e.lower()]
        return jdk_paths, jre_paths

    @classmethod
    def get_detect_from_sys(cls):
        """Detect JDK/JRE entries in the system PATH registry value."""
        return cls._filter_java_paths(cls.get_as_sys_env())

    @classmethod
    def get_detect_from_user(cls):
        """Detect JDK/JRE entries in the user PATH registry value."""
        return cls._filter_java_paths(cls.get_as_user_env())