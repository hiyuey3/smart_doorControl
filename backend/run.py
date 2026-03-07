import os
import sys


ROOT_DIR = os.path.dirname(__file__)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app

app = create_app()

if __name__ == '__main__':

    app.run(
        debug=True,
        host='0.0.0.0',
        port=5001,
        use_reloader=True,
        threaded=True
    )