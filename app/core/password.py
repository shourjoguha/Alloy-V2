import re
from typing import Literal


class PasswordValidationError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


COMMON_PASSWORDS = {
    'password', '123456', '12345678', 'qwerty', 'abc123', 'monkey', 'master',
    'dragon', '111111', 'baseball', 'iloveyou', 'trustno1', 'sunshine',
    'princess', 'admin', 'welcome', 'shadow', 'ashley', 'football',
    'jesus', 'michael', 'ninja', 'mustang', 'password1', '123456789',
    'adobe123', 'admin123', 'letmein', 'photoshop', '123123', 'qwertyuiop',
    'passw0rd', 'password123', 'hello', 'welcome1', 'test123', 'test'
}


PasswordStrength = Literal['weak', 'medium', 'strong', 'very_strong']


def validate_password(password: str) -> None:
    if len(password) < 12:
        raise PasswordValidationError(
            f"Password must be at least 12 characters long (got {len(password)})"
        )
    
    if not re.search(r'[A-Z]', password):
        raise PasswordValidationError(
            "Password must contain at least one uppercase letter"
        )
    
    if not re.search(r'[a-z]', password):
        raise PasswordValidationError(
            "Password must contain at least one lowercase letter"
        )
    
    if not re.search(r'\d', password):
        raise PasswordValidationError(
            "Password must contain at least one digit"
        )
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        raise PasswordValidationError(
            "Password must contain at least one special character"
        )
    
    if password.lower() in COMMON_PASSWORDS:
        raise PasswordValidationError(
            "Password is too common and easily guessable"
        )


def calculate_password_strength(password: str) -> tuple[PasswordStrength, int]:
    score = 0
    
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    
    if re.search(r'[A-Z]', password):
        score += 1
    if re.search(r'[a-z]', password):
        score += 1
    if re.search(r'\d', password):
        score += 1
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        score += 1
    
    unique_chars = len(set(password))
    if unique_chars >= len(password) * 0.7:
        score += 1
    
    if password.lower() in COMMON_PASSWORDS:
        score -= 2
    
    score = max(0, min(score, 4))
    
    strength_map: dict[int, PasswordStrength] = {
        0: 'weak',
        1: 'weak',
        2: 'medium',
        3: 'strong',
        4: 'very_strong'
    }
    
    return strength_map[score], score


def is_password_strong(password: str, min_score: int = 3) -> bool:
    try:
        validate_password(password)
        strength, score = calculate_password_strength(password)
        return score >= min_score
    except PasswordValidationError:
        return False


def generate_password_suggestions(password: str) -> list[str]:
    suggestions = []
    
    if len(password) < 12:
        suggestions.append(f"Add {12 - len(password)} more characters")
    
    if not re.search(r'[A-Z]', password):
        suggestions.append("Add an uppercase letter")
    
    if not re.search(r'[a-z]', password):
        suggestions.append("Add a lowercase letter")
    
    if not re.search(r'\d', password):
        suggestions.append("Add a number")
    
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        suggestions.append("Add a special character (!@#$%^&*)")
    
    if password.lower() in COMMON_PASSWORDS:
        suggestions.append("Choose a less common password")
    
    strength, _ = calculate_password_strength(password)
    if strength == 'weak':
        suggestions.append("Consider using a passphrase for better security")
    
    return suggestions


def check_password_history(password: str, password_hashes: list[str]) -> bool:
    import bcrypt
    
    for stored_hash in password_hashes:
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return False
    return True
