import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from core.app import create_app
if __name__ == "__main__":
    app = create_app()
    print("=" * 40)
    print("Модульное приложение запущено!")
    print("Откройте: http://localhost:5000")
    print("=" * 40)
    app.run(debug=True, host="0.0.0.0", port=5000)
