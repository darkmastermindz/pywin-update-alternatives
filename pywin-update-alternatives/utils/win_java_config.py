import os
import winreg


class win_java_config:
    """Configure JAVA_HOME / JDK_HOME and persist/restore configuration dumps."""

    _SYS_REG_PATH = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    _USER_REG_PATH = r'Environment'

    # -- Registry helpers --------------------------------------------------

    @classmethod
    def _set_sys_env(cls, name, value):
        """Write a system environment variable via the registry."""
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            cls._SYS_REG_PATH,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)

    @classmethod
    def _set_user_env(cls, name, value):
        """Write a user environment variable via the registry."""
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            cls._USER_REG_PATH,
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, name, 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)

    @classmethod
    def _get_sys_env(cls, name):
        """Read a system environment variable from the registry."""
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cls._SYS_REG_PATH)
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except OSError:
            return ''

    @classmethod
    def _get_user_env(cls, name):
        """Read a user environment variable from the registry."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls._USER_REG_PATH)
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return value
        except OSError:
            return ''

    # -- Public API --------------------------------------------------------

    @classmethod
    def set_java_home(cls, java_home_path, scope='system'):
        """Set JAVA_HOME and JDK_HOME to *java_home_path*.

        Args:
            java_home_path: Absolute path to the JDK root directory.
            scope: ``'system'`` (requires elevation) or ``'user'``.
        """
        if scope == 'user':
            cls._set_user_env('JAVA_HOME', java_home_path)
            cls._set_user_env('JDK_HOME', java_home_path)
        else:
            cls._set_sys_env('JAVA_HOME', java_home_path)
            cls._set_sys_env('JDK_HOME', java_home_path)

    @classmethod
    def get_current_config(cls):
        """Return a dict of the current Java-related environment configuration."""
        return {
            'JAVA_HOME_sys': cls._get_sys_env('JAVA_HOME'),
            'JDK_HOME_sys': cls._get_sys_env('JDK_HOME'),
            'JAVA_HOME_user': cls._get_user_env('JAVA_HOME'),
            'JDK_HOME_user': cls._get_user_env('JDK_HOME'),
            'PATH_sys': cls._get_sys_env('Path'),
            'PATH_user': cls._get_user_env('Path'),
        }

    @classmethod
    def dump_config(cls, filepath):
        """Save the current configuration to *filepath* as JSON.

        Args:
            filepath: Destination file path for the JSON dump.
        """
        import json

        config = cls.get_current_config()
        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(config, fh, indent=2)

    @classmethod
    def load_config(cls, filepath):
        """Restore configuration from a JSON dump previously created by :meth:`dump_config`.

        Args:
            filepath: Source file path of the JSON dump.
        """
        import json

        with open(filepath, 'r', encoding='utf-8') as fh:
            config = json.load(fh)

        def _validate_path(value):
            """Ensure value is an absolute Windows path or a semicolon-separated list thereof."""
            if not isinstance(value, str):
                return False
            # For PATH-style values, validate each non-empty component
            parts = [p.strip() for p in value.split(';') if p.strip()]
            return all(os.path.isabs(p) for p in parts) if parts else False

        for var in ('JAVA_HOME', 'JDK_HOME'):
            sys_val = config.get(f'{var}_sys', '')
            user_val = config.get(f'{var}_user', '')
            if sys_val:
                if not _validate_path(sys_val):
                    raise ValueError(f'Invalid path for {var}_sys: {sys_val!r}')
                cls._set_sys_env(var, sys_val)
            if user_val:
                if not _validate_path(user_val):
                    raise ValueError(f'Invalid path for {var}_user: {user_val!r}')
                cls._set_user_env(var, user_val)

        path_sys = config.get('PATH_sys', '')
        path_user = config.get('PATH_user', '')
        if path_sys:
            if not _validate_path(path_sys):
                raise ValueError(f'Invalid value for PATH_sys: {path_sys!r}')
            cls._set_sys_env('Path', path_sys)
        if path_user:
            if not _validate_path(path_user):
                raise ValueError(f'Invalid value for PATH_user: {path_user!r}')
            cls._set_user_env('Path', path_user)
