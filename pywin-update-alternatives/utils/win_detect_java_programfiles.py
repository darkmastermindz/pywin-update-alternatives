import os


class win_detect_java_programfiles:
    """Detect Java installations from common Program Files directories."""

    _SEARCH_ROOTS = [
        os.environ.get('ProgramFiles', r'C:\Program Files'),
        os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
        os.environ.get('ProgramW6432', r'C:\Program Files'),
    ]

    _JAVA_VENDORS = ['Java', 'Eclipse Adoptium', 'Eclipse Foundation',
                     'Microsoft', 'Amazon Corretto', 'BellSoft', 'Azul']

    @classmethod
    def _scan_root(cls, root):
        """Return all java.exe-containing subdirectories under a root path."""
        results = []
        if not root or not os.path.isdir(root):
            return results
        for vendor in cls._JAVA_VENDORS:
            vendor_dir = os.path.join(root, vendor)
            if not os.path.isdir(vendor_dir):
                continue
            for entry in os.scandir(vendor_dir):
                if not entry.is_dir():
                    continue
                bin_path = os.path.join(entry.path, 'bin')
                if os.path.isfile(os.path.join(bin_path, 'java.exe')):
                    results.append(entry.path)
        return results

    @classmethod
    def get_detect(cls):
        """Return (jdk_paths, jre_paths) found under Program Files."""
        all_paths = []
        seen = set()
        for root in cls._SEARCH_ROOTS:
            for p in cls._scan_root(root):
                norm = os.path.normcase(p)
                if norm not in seen:
                    seen.add(norm)
                    all_paths.append(p)

        jre_paths = [p for p in all_paths if 'jre' in p.lower()]
        jdk_paths = [p for p in all_paths if p not in jre_paths]
        return jdk_paths, jre_paths
