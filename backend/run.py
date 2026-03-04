import os
import sys

# Ensure the backend directory is on sys.path so local packages (core, api, mqtt, etc.)
# can be imported when running this script directly.
ROOT_DIR = os.path.dirname(__file__)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app

app = create_app()

if __name__ == '__main__':
    # 生产模式：禁用 debug 和 reloader，避免自动重启导致连接重置
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5001,
        use_reloader=True,
        threaded=True
    )