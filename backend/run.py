from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # 生产模式：禁用 debug 和 reloader，避免自动重启导致连接重置
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5001,
        use_reloader=False,
        threaded=True
    )