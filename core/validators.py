import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

class ComplexPasswordValidator:
    def validate(self, password, user=None):
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                _("Пароль должен содержать хотя бы одну заглавную букву."),
                code='password_no_upper',
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                _("Пароль должен содержать хотя бы одну строчную букву."),
                code='password_no_lower',
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                _("Пароль должен содержать хотя бы одну цифру."),
                code='password_no_number',
            )
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                _("Пароль должен содержать хотя бы один специальный символ (!@#$%^&*(),.?\":{}|<>)."),
                code='password_no_special',
            )

    def get_help_text(self):
        return _(
            "Ваш пароль должен содержать как минимум одну заглавную букву, одну строчную букву, одну цифру и один специальный символ."
        )
