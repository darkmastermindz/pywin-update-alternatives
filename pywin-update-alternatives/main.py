"""pywin-update-alternatives: Switch Java versions on Windows.

Usage:
    python main.py
"""

import sys


def _require_windows():
    if sys.platform != 'win32':
        print('This tool only runs on Windows.')
        sys.exit(1)


def main():
    _require_windows()

    from utils.win_detect_java_frompath import win_detect_java_frompath
    from utils.win_detect_java_programfiles import win_detect_java_programfiles
    from utils.win_java_config import win_java_config
    from utils.win_java_display import win_java_display
    from utils.win_java_menu import win_java_menu

    while True:
        print('\n=== pywin-update-alternatives: Java Version Manager ===')
        print('  1. Show current java -version')
        print('  2. List Java entries in system PATH')
        print('  3. List Java entries in user PATH')
        print('  4. Detect Java installations in Program Files')
        print('  5. Switch active Java (from Program Files, system scope)')
        print('  6. Switch active Java (from Program Files, user scope)')
        print('  7. Remove Java entries from system PATH')
        print('  8. Remove Java entries from user PATH')
        print('  9. Set JAVA_HOME / JDK_HOME (system scope)')
        print(' 10. Set JAVA_HOME / JDK_HOME (user scope)')
        print(' 11. Dump current config to file')
        print(' 12. Load config from file')
        print('  0. Exit')

        raw = input('\nChoice: ').strip()

        if raw == '0':
            print('Exiting.')
            break

        elif raw == '1':
            print('\n' + win_java_display.show_current_version())

        elif raw == '2':
            jdk, jre = win_detect_java_frompath.get_detect_from_sys()
            print(win_java_display.table_from_sys_path(jdk, jre))

        elif raw == '3':
            jdk, jre = win_detect_java_frompath.get_detect_from_user()
            print(win_java_display.table_from_user_path(jdk, jre))

        elif raw == '4':
            jdk, jre = win_detect_java_programfiles.get_detect()
            print(win_java_display.table_from_program_files(jdk, jre))

        elif raw in ('5', '6'):
            scope = 'system' if raw == '5' else 'user'
            jdk, jre = win_detect_java_programfiles.get_detect()
            candidates = list(dict.fromkeys(jdk + jre))
            win_java_menu.menu_update_java_in_path(candidates, scope=scope)

        elif raw == '7':
            jdk, jre = win_detect_java_frompath.get_detect_from_sys()
            all_entries = list(dict.fromkeys(jdk + jre))
            win_java_menu.menu_delete_java_from_path(all_entries, scope='system')

        elif raw == '8':
            jdk, jre = win_detect_java_frompath.get_detect_from_user()
            all_entries = list(dict.fromkeys(jdk + jre))
            win_java_menu.menu_delete_java_from_path(all_entries, scope='user')

        elif raw in ('9', '10'):
            scope = 'system' if raw == '9' else 'user'
            path = input('Enter JAVA_HOME path: ').strip()
            if path:
                win_java_config.set_java_home(path, scope=scope)
                print(f'JAVA_HOME and JDK_HOME set to: {path} ({scope})')
            else:
                print('No path entered. No changes made.')

        elif raw == '11':
            filepath = input('Enter destination file path (e.g. java_config.json): ').strip()
            if filepath:
                win_java_config.dump_config(filepath)
                print(f'Config saved to {filepath}')
            else:
                print('No path entered. No changes made.')

        elif raw == '12':
            filepath = input('Enter source file path: ').strip()
            if filepath:
                win_java_config.load_config(filepath)
                print(f'Config loaded from {filepath}')
            else:
                print('No path entered. No changes made.')

        else:
            print('Invalid choice.')


if __name__ == '__main__':
    main()
