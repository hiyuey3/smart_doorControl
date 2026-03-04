# 智慧校园门禁系统

这是一个用于校园门禁管理的全栈示例工程，包含后端服务、微信小程序客户端和 ESP32 示例代码。

主要目录结构：

- `backend/`：Flask 后端服务、数据库初始化和管理界面
- `miniprogram-1/`：微信小程序前端代码
- `esp32s3/`：ESP32 示范固件与引脚定义

快速上手：

1. 后端（开发环境）

   - 创建虚拟环境并安装依赖：

     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     pip install -r backend/requirements.txt
     ```

   - 初始化数据库（示例）：

     ```bash
     cd backend
     python init_db.py
     ```

   - 启动开发服务器：

     ```bash
     python run.py
     ```

2. 小程序

   - 使用微信开发者工具打开 `miniprogram-1/` 目录进行预览与调试。

3. ESP32

   - 使用 Arduino/ESP-IDF 将 `esp32s3/esp32s3.ino` 烧录到设备，按文件顶部注释配置引脚。

安全与隐私注意事项：

- 仓库中可能包含示例配置文件，请勿将真实的 API 密钥或敏感凭据提交到公开仓库。

如需我继续：我可以添加更详细的使用说明、License 或示例配置文件。
