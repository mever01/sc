"""
Точка входа для запуска сценария регистрации LC Waikiki.
Запуск: python main.py [run|check|balance]
Или через консольную команду: sc [run|check|balance]
"""
import sys
from src.cli import main

if __name__ == "__main__":
    # Если запущен без аргументов через python main.py, по умолчанию передаем 'run' для совместимости
    if len(sys.argv) == 1:
        sys.exit(main(["run"]))
    sys.exit(main())
