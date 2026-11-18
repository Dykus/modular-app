"""Tochka vhoda. Rezhim servera (APP_DEBUG=0) ili razrabotki (APP_DEBUG=1)."""
import sys, os, socket
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from core.app import create_app

def _busy(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", port))
            return False
        except OSError:
            return True

def _free(start, tries=20):
    for p in range(start, start + tries):
        if not _busy(p):
            return p
    raise RuntimeError("Net svobodnogo porta v diapazone %d-%d" % (start, start + tries))

def main():
    app = create_app()
    port = config.PORT
    note = ""
    if config.DEBUG:
        if _busy(port):
            port = _free(port + 1)
            note = " (port %d zanat, vzyal %d)" % (config.PORT, port)
    else:
        if _busy(port):
            print(f"OSHIBKA: port {config.PORT} zanat. Osvobodite ego ili izmenite APP_PORT v .env")
            print("  V servernom rezhime port FIKSIROVANNYY - adres ne dolzhen ezhat'.")
            sys.exit(1)

    print("=" * 54)
    print("Modulnoe prilozhenie zapushcheno!" + note)
    print("Rezhim:   %s" % ("RAZRABOTKA (debug vklyuchen)" if config.DEBUG else "SERVER (debug vyklyuchen)"))
    print("Localno:  http://localhost:%d" % port)
    print("V seti:   http://<IP-mashiny>:%d" % port)
    print("BD:       %s" % config.DATABASE)
    print("Nastroyki: .env  (APP_PORT, APP_SECRET_KEY, APP_DEBUG)")
    print("=" * 54)

    if config.DEBUG:
        app.run(debug=True, host=config.HOST, port=port)
        return

    try:
        from waitress import serve
        print("WSGI-server: waitress, potokov 8")
        print("=" * 54)
        serve(app, host=config.HOST, port=port, threads=8)
    except ImportError:
        print("WSGI-server: vstroennyy Flask (waitress ne ustanovlen)")
        print("  Rekomenduetsya: ./venv/bin/python -m pip install waitress")
        print("=" * 54)
        app.run(debug=False, host=config.HOST, port=port, threaded=True)

if __name__ == "__main__":
    main()
