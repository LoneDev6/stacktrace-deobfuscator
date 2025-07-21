import re

# Ignore these prefixes when deobfuscating (standard Java and common libraries)
IGNORED_PREFIXES = (
    "java.", "javax.", "sun.", "com.sun.", "jdk.", "org.bukkit.", "net.minecraft.",
    "String", "Integer", "Boolean", "Double", "Float", "Long", "Short", "Byte", "Void"
)

def parse_map_file(path):
    """
    Returns:
    - class_mapping: dict mapping obfuscated class names to original class names
    - method_ranges: dict mapping (obfuscated_class, obfuscated_method) to a list of tuples
    """
    class_mapping = {}
    method_ranges = {}

    current_class_obf = None
    current_class_orig = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip()
            # Class mapping
            if '->' in line and line.strip().endswith(':'):
                orig, obf = map(str.strip, line[:-1].split('->'))
                current_class_orig = orig
                current_class_obf = obf
                class_mapping[obf] = orig
                continue
            # Method mapping (ignore fields/variables)
            if current_class_obf and ':' in line and '->' in line:
                parts = line.strip().split(':', 2)
                if len(parts) < 3:
                    continue
                try:
                    start = int(parts[0])
                    end = int(parts[1])
                except ValueError:
                    continue
                rest = parts[2]
                # Find the obfuscated method name after '->'
                if '->' not in rest:
                    continue
                before_arrow, obf_name = rest.rsplit('->', 1)
                obf_name = obf_name.strip()
                # Get the real method name (before the parenthesis)
                real_name = before_arrow.split('(')[0].split()[-1].strip()
                # print(f"ADD: ({current_class_obf}, {obf_name}) -> {start}-{end}, {current_class_orig}.{real_name}\n")
                key = (current_class_obf, obf_name)
                value = (start, end, f"{current_class_orig}.{real_name}")
                if key not in method_ranges:
                    method_ranges[key] = []
                method_ranges[key].append(value)

    return class_mapping, method_ranges

def deobfuscate_stacktrace(text, class_mapping, method_ranges):
    output = []
    stacktrace_pattern = re.compile(r'([\w\.\$]+)\.(\w+)\(SourceFile:(\d+)\)')
    for line in text.splitlines():
        new_line = line
        offset = 0
        for match in stacktrace_pattern.finditer(line):
            clazz, method, line_number = match.groups()
            clazz = clazz.strip()
            method = method.strip()
            line_number = int(line_number)
            print(f"TRACE: ({clazz}, {method}) at {line_number}")
            candidates = []
            for (cls, meth), ranges in method_ranges.items():
                if cls == clazz and meth == method:
                    for start, end, original in ranges:
                        candidates.append((cls, meth, start, end, original))
            print(f"  Candidates: {[f'{cls} {meth} {start}-{end}' for cls, meth, start, end, _ in candidates]}")
            best_match = None
            for cls, meth, start, end, original in candidates:
                if start <= line_number <= end:
                    best_match = original
                    print(f"  MATCH: {cls}.{meth} -> {original} ({start}-{end})")
                    break
            if not best_match:
                print(f"  NO MATCH for {clazz}.{method} at {line_number}")
            if best_match:
                start_idx = match.start() + offset
                end_idx = match.start() + offset + len(f"{clazz}.{method}")
                new_line = new_line[:start_idx] + best_match + new_line[end_idx:]
                offset += len(best_match) - len(f"{clazz}.{method}")
        output.append(new_line)
    return '\n'.join(output)
