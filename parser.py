import re

# Ignore these prefixes when deobfuscating (standard Java and common libraries)
IGNORED_PREFIXES = (
    "java.", "javax.", "sun.", "com.sun.", "jdk.", "org.bukkit.", "net.minecraft.",
    "String", "Integer", "Boolean", "Double", "Float", "Long", "Short", "Byte", "Void"
)

def parse_map_file(path):
    """
    Parses the mapping file and returns a dictionary mapping obfuscated names to original names.
    """
    mapping = {}
    with open(path, "r", encoding="utf-8") as f:
        current_class_obf = None
        current_class_orig = None
        for line in f:
            line = line.rstrip()
            # Class mapping
            if '->' in line and line.strip().endswith(':'):
                orig, obf = map(str.strip, line[:-1].split('->'))
                mapping[obf] = orig
                current_class_obf = obf
                current_class_orig = orig
            # Field/method mapping
            elif '->' in line and not line.strip().endswith(':'):
                parts = line.strip().split('->')
                left = parts[0].strip()
                right = parts[1].strip()
                # Field/method without space (e.g. E)
                if current_class_obf and right:
                    mapping[f"{current_class_obf}.{right}"] = f"{current_class_orig}.{left.split()[-1]}"
    return mapping

def deobfuscate_stacktrace(text, mapping):
    """
    Replaces obfuscated names in the stacktrace with their original names using the mapping.
    """
    # Regex to find words like itemsadder.m.a, itemsadder.m.a.e, etc.
    pattern = re.compile(r'([a-zA-Z_][\w\.]*\w)')

    def replace_match(match):
        word = match.group(1)
        # Ignore standard classes/methods
        if any(word.startswith(prefix) for prefix in IGNORED_PREFIXES):
            return word
        # Try to find the longest matching mapping
        parts = word.split('.')
        for i in range(len(parts), 0, -1):
            candidate = '.'.join(parts[:i])
            if candidate in mapping:
                return mapping[candidate] + word[len(candidate):]
        return word

    lines = []
    for line in text.splitlines():
        if '.' in line:
            new_line = pattern.sub(replace_match, line)
            lines.append(new_line)
        else:
            lines.append(line)
    return '\n'.join(lines)
