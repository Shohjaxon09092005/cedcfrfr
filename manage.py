#!/usr/bin/env python
import os
import sys


def main() -> None:
    """EduAI Django boshqaruv skripti."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eduai_backend.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Django import qilinmadi. Iltimos, virtual muhitda "
            "'pip install -r requirements.txt' buyrug'ini bajarib, qaytadan urinib ko'ring."
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

