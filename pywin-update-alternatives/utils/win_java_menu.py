import os
import winreg


class win_java_menu:
    """Interactive menu flow for managing Java PATH entries."""

    _SYS_REG_PATH = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'
    _USER_REG_PATH = r'Environment'

    # -- Registry helpers --------------------------------------------------

    @classmethod
    def _read_reg_path(cls, hive, reg_path):
        try:
            key = winreg.OpenKey(hive, reg_path)
            value, _ = winreg.QueryValueEx(key, 'Path')
            winreg.CloseKey(key)
            return value
        except OSError:
            return ''

    @classmethod
    def _write_reg_path(cls, hive, reg_path, value, access=winreg.KEY_SET_VALUE):
        key = winreg.OpenKey(hive, reg_path, 0, access)
        winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, value)
        winreg.CloseKey(key)

    # -- Menu helpers ------------------------------------------------------

    @classmethod
    def _prompt_choice(cls, options, prompt='Select an option'):
        """Display a numbered menu and return the chosen index (0-based)."""
        for idx, option in enumerate(options, start=1):
            print(f'  {idx}. {option}')
        while True:
            raw = input(f'{prompt} (1-{len(options)}): ').strip()
            if raw.isdigit():
                choice = int(raw)
                if 1 <= choice <= len(options):
                    return choice - 1
            print(f'  Invalid input. Enter a number between 1 and {len(options)}.')

    # -- Public API --------------------------------------------------------

    @classmethod
    def menu_update_java_in_path(cls, candidate_paths, scope='system'):
        """Interactively choose a Java installation to add/replace in PATH.

        Args:
            candidate_paths: List of Java root paths to present to the user.
            scope: ``'system'`` or ``'user'``.
        """
        if not candidate_paths:
            print('No Java installations available to select.')
            return

        print('\nAvailable Java installations:')
        idx = cls._prompt_choice(candidate_paths, prompt='Select installation to activate')
        selected = candidate_paths[idx]
        bin_path = os.path.join(selected, 'bin')

        if scope == 'user':
            hive = winreg.HKEY_CURRENT_USER
            reg_path = cls._USER_REG_PATH
        else:
            hive = winreg.HKEY_LOCAL_MACHINE
            reg_path = cls._SYS_REG_PATH

        current_path = cls._read_reg_path(hive, reg_path)
        entries = [e.strip() for e in current_path.split(';') if e.strip()]

        # Remove existing java bin entries (entries ending with \bin inside a java-named dir)
        def _is_java_bin(entry):
            lower = entry.lower()
            return lower.endswith('\\bin') and 'java' in lower

        entries = [e for e in entries if not _is_java_bin(e)]
        entries.insert(0, bin_path)

        new_path = ';'.join(entries)
        cls._write_reg_path(hive, reg_path, new_path)
        print(f'\nActivated: {bin_path}')
        print('Restart your terminal or log out/in for changes to take effect.')

    @classmethod
    def menu_delete_java_from_path(cls, java_entries, scope='system'):
        """Interactively choose Java PATH entries to remove.

        Args:
            java_entries: List of Java-related PATH entries currently present.
            scope: ``'system'`` or ``'user'``.
        """
        if not java_entries:
            print('No Java PATH entries found to remove.')
            return

        if scope == 'user':
            hive = winreg.HKEY_CURRENT_USER
            reg_path = cls._USER_REG_PATH
        else:
            hive = winreg.HKEY_LOCAL_MACHINE
            reg_path = cls._SYS_REG_PATH

        current_path = cls._read_reg_path(hive, reg_path)
        entries = [e.strip() for e in current_path.split(';') if e.strip()]

        print('\nJava PATH entries to remove (space-separated numbers, or "all"):')
        for idx, entry in enumerate(java_entries, start=1):
            print(f'  {idx}. {entry}')

        raw = input('Selection: ').strip().lower()
        if raw == 'all':
            to_remove = set(java_entries)
        else:
            indices = []
            for token in raw.split():
                if token.isdigit():
                    i = int(token)
                    if 1 <= i <= len(java_entries):
                        indices.append(i - 1)
            to_remove = {java_entries[i] for i in indices}

        if not to_remove:
            print('No valid selections made. No changes applied.')
            return

        entries = [e for e in entries if e not in to_remove]
        new_path = ';'.join(entries)
        cls._write_reg_path(hive, reg_path, new_path)
        print(f'\nRemoved {len(to_remove)} entry/entries from {scope} PATH.')
        print('Restart your terminal or log out/in for changes to take effect.')
