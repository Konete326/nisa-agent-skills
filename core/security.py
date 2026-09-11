import re

class SecurityValidator:
    BLACKLISTED_PATTERNS = [
        r"\bformat\b",
        r"\bdiskpart\b",
        r"\bdel\s+.*[/\\][sS]",
        r"\brmdir\s+.*[/\\][sS]",
        r"\brm\s+-rf\b",
        r"\bdrop\s+database\b",
        r"\bshutdown\b",
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",
        r"\breg\s+delete\b",
        r"remove-item\s+.*-recurse\s+.*-force",
        r"\bvssadmin\s+delete\s+shadows\b",
        r"\bbcdedit\b"
    ]

    def __init__(self, additional_rules=None):
        rules = self.BLACKLISTED_PATTERNS + (additional_rules or [])
        self.compiled_rules = [re.compile(pattern, re.IGNORECASE) for pattern in rules]

    def is_safe(self, command_string):
        if not command_string or not command_string.strip():
            return False, "Empty command string rejected"

        clean_command = command_string.strip()
        for rule in self.compiled_rules:
            if rule.search(clean_command):
                return False, f"Command rejected: matches security blacklist rule '{rule.pattern}'"

        return True, "Valid"

    def sanitize(self, raw_input):
        if not raw_input:
            return ""
        stripped = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", raw_input)
        return stripped.strip()

security_service = SecurityValidator()
