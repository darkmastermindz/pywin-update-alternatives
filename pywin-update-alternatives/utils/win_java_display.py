import subprocess


class win_java_display:
    """Display helpers for Java version information."""

    # -- ASCII table -------------------------------------------------------

    @classmethod
    def _build_table(cls, jdk_paths, jre_paths, title=''):
        """Return an ASCII table string for the given JDK and JRE path lists."""
        col_w = max(
            (len(p) for p in jdk_paths + jre_paths),
            default=20,
        )
        col_w = max(col_w, len('Path'), 20)
        type_w = 3

        sep = f"+{'-' * (type_w + 2)}+{'-' * (col_w + 2)}+"
        header = f"| {'Type':<{type_w}} | {'Path':<{col_w}} |"

        lines = []
        if title:
            lines.append(title)
        lines.append(sep)
        lines.append(header)
        lines.append(sep)

        for path in jdk_paths:
            lines.append(f"| {'JDK':<{type_w}} | {path:<{col_w}} |")
        for path in jre_paths:
            lines.append(f"| {'JRE':<{type_w}} | {path:<{col_w}} |")

        if not jdk_paths and not jre_paths:
            lines.append(f"| {'---':<{type_w}} | {'(none found)':<{col_w}} |")

        lines.append(sep)
        return '\n'.join(lines)

    @classmethod
    def table_from_sys_path(cls, jdk_paths, jre_paths):
        """Return an ASCII table of JDK/JRE entries from the system PATH."""
        return cls._build_table(jdk_paths, jre_paths, title='=== System PATH Java entries ===')

    @classmethod
    def table_from_user_path(cls, jdk_paths, jre_paths):
        """Return an ASCII table of JDK/JRE entries from the user PATH."""
        return cls._build_table(jdk_paths, jre_paths, title='=== User PATH Java entries ===')

    @classmethod
    def table_from_program_files(cls, jdk_paths, jre_paths):
        """Return an ASCII table of JDK/JRE entries detected in Program Files."""
        return cls._build_table(jdk_paths, jre_paths, title='=== Program Files Java installations ===')

    # -- java -version -----------------------------------------------------

    @classmethod
    def show_current_version(cls):
        """Return the output of ``java -version`` as a string."""
        try:
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
            )
            output = result.stderr or result.stdout
            return output.strip()
        except FileNotFoundError:
            return '(java not found on PATH)'
