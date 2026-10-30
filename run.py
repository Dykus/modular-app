"""Tochka vhoda"""
import sys, os, socket
sys.path.insert(0, os.path.dirname(__file__))
import config
from core.app import create_app

def find_free_port(start, tries=20):
    for p in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("", p)); return p
            except OSError:
                continue
    raise RuntimeError("No free port in %d-%d" % (start, start + tries))

if __name__ == "__main__":
    app = create_app()
    port = find_free_port(config.PORT)
    used = "" if port == config.PORT else " (port %d zanat, vzyal %d)" % (config.PORT, port)
    print("=" * 54)
    print("Modulnoe prilozhenie zapushcheno!" + used)
    print("Localno:  http://localhost:%d" % port)
    print("V seti:   http://<IP-mashiny>:%d" % port)
    print("BD:       %s" % config.DATABASE)
    print("=" * 54)
    print("Smenit port: config.py (PORT = ...)")
    print("=" * 54)
    app.run(debug=True, host=config.HOST, port=port)
