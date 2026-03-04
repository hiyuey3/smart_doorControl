#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>          // MQTT 客户端库
#include <ArduinoJson.h>           // JSON 解析库
#include <time.h>
#include "esp_camera.h"            // OV2640 摄像头驱动
#include "esp_http_server.h"       // HTTP 服务器

// 芯片模型定义
#define CAMERA_MODEL_ESP32S3_EYE
#include "camera_pins.h"           // 摄像头引脚配置（由 camera_pins.h 提供）

// ===== 系统配置区 =====
// 启动按钮（GPIO0），按住 12 秒触发 SmartConfig WiFi 配置
#define BOOT_BUTTON_PIN 0

// MQTT 消息队列服务器配置
const char* mqtt_server = "mqtt.5i03.cn";
const int mqtt_port = 1883;

// UART 串口配置（与 STM32 MCU 通信）
// STM32 负责继电器控制、指纹识别、查询设备状态等
#define LED_BUILT_IN 2              // 内置 LED（GPIO2，用于状态指示）
#define STM_RX_PIN 21               // UART RX（接收来自 STM32 的数据）
#define STM_TX_PIN 42               // UART TX（发送指令给 STM32）
HardwareSerial SerialSTM(1);        // 使用 UART1 通道与 STM32 通信

// ===== 全局变量 =====
String mqtt_client_id;             // MQTT 客户端 ID（基于 MAC 地址）
String topic_sub;                  // MQTT 下行主题（接收指令）
String topic_pub;                  // MQTT 上行主题（发送消息）
WiFiClient espClient;              // WiFi 客户端
PubSubClient mqttClient(espClient); // MQTT 客户端

httpd_handle_t stream_httpd = NULL; // HTTP 服务器句柄（视频流服务）
bool is_camera_active = false;      // 摄像头是否已初始化
unsigned long heartbeat_count = 0;  // 心跳计数器
volatile int active_viewers = 0;    // 当前连接的视频流客户端数


// ===== WiFi 网络初始化 =====
/**
 * WiFi 网络初始化函数
 * 
 * 功能流程：
 * 1. 配置 WiFi 为 Station 模式（连接到现有 WiFi）
 * 2. 尝试连接预配置的 WiFi（10 秒超时）
 * 3. 如果连接失败，启动 SmartConfig 模式（手机扫码配置）
 * 4. 同步系统时间（从网络时间服务器）
 * 
 * SmartConfig 原理：
 * - 用户在微信小程序中扫码或长按 BOOT 按钮，设备进入 SmartConfig 模式
 * - 手机发送 WiFi 密码，ESP32 接收并连接
 * - 连接成功后自动退出 SmartConfig 模式
 */
void framework_network_init() {
  Serial.println("\nSTEP 2: Network Init");
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);

  // 配置 WiFi 为 Station 模式（连接模式，不是 AP 模式）
  WiFi.mode(WIFI_STA);
  WiFi.begin();  // 连接上次保存的 WiFi

  // 等待连接（最多 20 次 x 500ms = 10 秒）
  Serial.print("Connecting WiFi ");
  int timeout = 20;
  while (WiFi.status() != WL_CONNECTED && timeout > 0) {
    delay(500);
    Serial.print(".");
    timeout--;
  }

  // 如果连接失败，启动 SmartConfig 模式
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nSmartConfig Mode...");
    WiFi.beginSmartConfig();
    
    // 等待 SmartConfig 完成（用户通过扫码配置）
    while (!WiFi.smartConfigDone()) {
      delay(500);
      Serial.print(".");
    }
  }

  Serial.println("\nWiFi Connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());  // 显示获得的 IP 地址
  
  // NTP 时间同步
  // 原因：ESP32 没有 RTC，系统时间需要从网络同步
  // 用途：时间戳用于日志记录、心跳消息时间戳
  configTime(8 * 3600, 0, "ntp.aliyun.com", "pool.ntp.org");
  Serial.println("Syncing time with NTP...");
}


// ===== 摄像头管理 =====
/**
 * 摄像头电源管理函数
 * 
 * 功能：初始化 OV2640 摄像头模块
 * 参数：enable - true 启动摄像头，false 关闭（暂未实现关闭逻辑）
 * 返回：ESP_OK 表示成功，其他表示失败
 * 
 * 关键参数说明：
 * - xclk_freq_hz：时钟频率（降频到 10MHz 提升信号抗干扰能力）
 * - frame_size：分辨率（VGA = 640x480）
 * - jpeg_quality：JPEG 压缩质量（20 = 低质量，节省内存和带宽）
 * - fb_count：帧缓冲数量（2 = 双缓冲，提高稳定性）
 * - fb_location：帧缓冲位置（PSRAM = 使用外部 RAM）
 */
esp_err_t manage_camera_power(bool enable) {
  if (enable && !is_camera_active) {
    camera_config_t config;
    
    // 摄像头数据线引脚配置（8 位并行数据线）
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    
    // 摄像头控制线引脚配置
    config.pin_xclk = XCLK_GPIO_NUM;    // 时钟信号
    config.pin_pclk = PCLK_GPIO_NUM;    // 像素时钟
    config.pin_vsync = VSYNC_GPIO_NUM;  // 垂直同步信号
    config.pin_href = HREF_GPIO_NUM;    // 水平同步信号
    config.pin_sccb_sda = SIOD_GPIO_NUM; // I2C 数据线
    config.pin_sccb_scl = SIOC_GPIO_NUM; // I2C 时钟线
    config.pin_pwdn = PWDN_GPIO_NUM;    // 电源下拉（通常未使用）
    config.pin_reset = RESET_GPIO_NUM;  // 复位引脚
    
    // 摄像头工作参数
    config.xclk_freq_hz = 10000000;      // 降频到 10MHz（默认 20MHz，降频提升稳定性）
    config.frame_size = FRAMESIZE_VGA;   // 分辨率：640x480
    config.pixel_format = PIXFORMAT_JPEG; // 格式：JPEG 压缩（节省带宽）
    config.grab_mode = CAMERA_GRAB_LATEST; // 获取模式：始终获取最新帧（不累积）
    config.fb_location = CAMERA_FB_IN_PSRAM; // 帧缓冲位置：外部 PSRAM 内存
    config.jpeg_quality = 20;             // JPEG 质量：20（较低质量，加快处理）
    config.fb_count = 2;                  // 帧缓冲数量：2（双缓冲）

    // 初始化摄像头
    esp_err_t err = esp_camera_init(&config);
    if (err == ESP_OK) {
      is_camera_active = true;
      sensor_t* s = esp_camera_sensor_get();
      s->set_vflip(s, 1);  // 垂直翻转（根据安装方向调整）
    }
    return err;
  }
  return ESP_OK;
}


// ===== UART 串口通信协议 =====
/**
 * 向 STM32 发送十六进制指令
 * 
 * 协议格式：| 0xAA | 0x55 | CMD | LEN | DATA | CHECKSUM |
 * 
 * 示例：开锁指令
 *   Frame = [0xAA, 0x55, 0x01, 0x01, 0x01, sum]
 *   其中 sum = (0x01 + 0x01 + 0x01) & 0xFF
 * 
 * 参数：
 *   cmd：命令编码（0x01=开锁，0x04=报警，0x05=查询状态）
 *   data：数据字节
 */
void send_hex_to_stm32(uint8_t cmd, uint8_t data) {
  uint8_t frame[6] = { 
    0xAA,                               // 帧头 1
    0x55,                               // 帧头 2
    cmd,                                // 命令
    0x01,                               // 数据长度（固定 1 字节）
    data,                               // 数据
    (uint8_t)((cmd + 0x01 + data) & 0xFF)  // 校验和
  };
  SerialSTM.write(frame, 6);
  Serial.printf("UART TX: 0x%02X\n", cmd);
}

/**
 * 业务指令路由器
 * 
 * 功能：解析来自后端（通过 MQTT）的 JSON 指令，执行相应的硬件操作
 * 
 * 支持的命令：
 * - open_door：开锁（发送 0x01 指令给 STM32）
 * - alarm：报警（发送 0x04 指令）
 * - query_status：查询设备状态（发送 0x05 指令）
 * - reboot：重启 ESP32
 * - led_control：LED 测试开关
 * 
 * 示例输入：
 *   {"cmd": "open_door"}
 */
void business_command_router(String json_msg) {
  JsonDocument doc;
  
  // JSON 解析（如果失败则返回）
  if (deserializeJson(doc, json_msg)) return;

  const char* cmd = doc["cmd"];
  if (!cmd) return;

  // 命令分发
  if (strcmp(cmd, "open_door") == 0) 
    send_hex_to_stm32(0x01, 0x01);  // 开锁
  else if (strcmp(cmd, "alarm") == 0) 
    send_hex_to_stm32(0x04, 0x01);  // 报警
  else if (strcmp(cmd, "query_status") == 0) 
    send_hex_to_stm32(0x05, 0x00);  // 查询状态
  else if (strcmp(cmd, "reboot") == 0) 
    ESP.restart();                   // 重启
  else if (strcmp(cmd, "led_control") == 0) {
    // LED 测试命令（用于调试）
    static bool led_state = false;
    led_state = !led_state;
    digitalWrite(LED_BUILT_IN, led_state ? HIGH : LOW);
    Serial.printf("LED %s\n", led_state ? "ON" : "OFF");
  }
}

/**
 * UART 监听任务
 * 
 * 功能：持续监听来自 STM32 的数据，解析并处理
 * 
 * 状态机：
 * - state=0：等待帧头 0xAA
 * - state=1：等待帧头 0x55
 * - state=2：读取命令
 * - state=3：读取数据长度
 * - state=4：读取数据
 * - state=5：验证校验和，如果正确则上报 MQTT
 */
void business_uart_listen() {
  while (SerialSTM.available()) {
    static uint8_t state = 0, rx_cmd, rx_len, rx_data;
    uint8_t b = SerialSTM.read();
    
    switch (state) {
      case 0: 
        // 等待帧头 0xAA
        if (b == 0xAA) state = 1; 
        break;
        
      case 1: 
        // 等待帧头 0x55
        if (b == 0x55) state = 2; 
        else state = 0;  // 失败则重新开始
        break;
        
      case 2: 
        // 读取命令
        rx_cmd = b; 
        state = 3; 
        break;
        
      case 3: 
        // 读取数据长度
        rx_len = b; 
        state = 4; 
        break;
        
      case 4: 
        // 读取数据
        rx_data = b; 
        state = 5; 
        break;
        
      case 5:
        // 验证校验和并处理
        if (b == ((rx_cmd + rx_len + rx_data) & 0xFF)) {
          // 校验正确，上报到后端
          String payload = "{\"type\":\"hw_report\",\"mac\":\"" + WiFi.macAddress() + 
                         "\",\"cmd\":" + String(rx_cmd) + ",\"data\":" + String(rx_data) + "}";
          if (mqttClient.connected()) {
            mqttClient.publish(topic_pub.c_str(), payload.c_str());
            Serial.printf("UART RX OK, published to MQTT: %s\n", payload.c_str());
          }
        }
        state = 0;  // 重置状态机
        break;
    }
  }
}


// ===== MQTT 消息队列处理 =====
/**
 * MQTT 后台任务
 * 
 * 功能：在后台线程中持续维护 MQTT 连接
 * 
 * 工作流程：
 * 1. 检查 WiFi 连接状态
 * 2. 如果 MQTT 未连接，则尝试连接
 * 3. 连接成功后订阅下行主题（接收指令）
 * 4. 定期处理 MQTT 消息
 * 5. 发送 Last Will Testament（设备离线时的遗言消息）
 * 
 * 参数：pv - FreeRTOS 任务参数（未使用）
 */
void mqtt_task(void* pv) {
  for (;;) {
    if (WiFi.status() == WL_CONNECTED) {
      if (!mqttClient.connected()) {
        // 构建 MQTT 客户端信息
        String mac = WiFi.macAddress();
        mac.replace(":", "");  // 移除 MAC 地址中的冒号
        
        String lwt_topic = "/iot/device/" + mac + "/status";
        String local_ip = WiFi.localIP().toString();
        String lwt_payload = "{\"status\":\"offline\",\"ip_address\":\"" + local_ip + "\"}";

        // 尝试连接 MQTT Broker
        if (mqttClient.connect(mqtt_client_id.c_str(), lwt_topic.c_str(), 1, true, lwt_payload.c_str())) {
          Serial.println("MQTT Connected");
          
          // 发布上线消息
          String online_payload = "{\"status\":\"online\",\"ip_address\":\"" + local_ip + "\"}";
          mqttClient.publish(lwt_topic.c_str(), online_payload.c_str(), true);
          
          // 订阅下行主题（接收来自后端的指令）
          mqttClient.subscribe(topic_sub.c_str());
        } else {
          // 连接失败，5 秒后重试
          vTaskDelay(5000 / portTICK_PERIOD_MS);
        }
      } else {
        // 已连接，定期处理消息
        mqttClient.loop();
      }
    }
    vTaskDelay(50 / portTICK_PERIOD_MS);
  }
}


// ===== 本地 HTTP 视频流服务 =====
/**
 * HTTP 流处理函数
 * 
 * 功能：提供 Motion JPEG 视频流服务
 * URL：http://{ESP32_IP}:81/stream
 * 格式：multipart/x-mixed-replace（浏览器标准流格式）
 * 
 * 为什么需要本地流服务？
 * 1. 快速性：局域网内获取快照延迟低（< 100ms）
 * 2. 备选方案：当后端代理超时时的快速降级
 * 3. 直连访问：无需经过后端，减少网络开销
 */
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[Stream] ERROR: Failed to get frame");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  // 设置 HTTP 响应头：Multipart JPEG 格式
  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  
  // 记录连接数
  active_viewers++;
  Serial.printf("[Stream] Client connected. Active viewers: %d\n", active_viewers);
  
  // 循环发送帧，直到客户端断开或 WiFi 断连
  while (WiFi.isConnected()) {
    // 获取最新摄像头帧
    camera_fb_t *frame = esp_camera_fb_get();
    if (!frame) {
      Serial.println("[Stream] Failed to get frame during stream");
      break;
    }

    // 构建帧头
    size_t hlen = snprintf((char *)fb->buf, 64,
                          "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                          frame->len);
    
    // 发送帧头、帧数据、帧尾
    if (httpd_resp_send_chunk(req, (const char *)fb->buf, hlen) != ESP_OK ||
        httpd_resp_send_chunk(req, (const char *)frame->buf, frame->len) != ESP_OK ||
        httpd_resp_send_chunk(req, "\r\n--frame\r\n", 10) != ESP_OK) {
      esp_camera_fb_return(frame);
      break;  // 发送失败，断开连接
    }
    
    esp_camera_fb_return(frame);
    delay(20);  // 给系统一点喘息时间（约 50ms 的帧间隔，20fps）
  }
  
  // 记录断开连接
  active_viewers--;
  Serial.printf("[Stream] Client disconnected. Active viewers: %d\n", active_viewers);

  esp_camera_fb_return(fb);
  return ESP_OK;
}

/**
 * 启动 HTTP 服务器
 * 
 * 功能：在 GPIO 81 端口启动本地 HTTP 服务
 * 注册路由：GET /stream → 返回 Motion JPEG 流
 */
void start_httpd() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;   // 监听端口
  config.ctrl_port = 8000;   // 控制端口
  
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    // 注册 /stream 路由
    httpd_uri_t uri_handler = { 
      .uri = "/stream", 
      .method = HTTP_GET, 
      .handler = stream_handler, 
      .user_ctx = NULL 
    };
    
    if (httpd_register_uri_handler(stream_httpd, &uri_handler) == ESP_OK) {
      Serial.println("[Stream] Local HTTP server started on port 81");
      Serial.println("[Stream] URL: http://<IP>:81/stream");
    }
  }
}


// ===== 主程序 =====
/**
 * Arduino setup() 函数
 * 
 * 初始化顺序很关键，因为涉及电压和内存管理：
 * 1. 初始化摄像头（防止电压瞬降）
 * 2. 等待 2 秒稳定
 * 3. 初始化 WiFi
 * 4. 配置 MQTT
 * 5. 启动后台任务
 * 6. 启动 HTTP 服务
 */
void setup() {
  Serial.begin(115200);
  SerialSTM.begin(115200, SERIAL_8N1, STM_RX_PIN, STM_TX_PIN);

  pinMode(LED_BUILT_IN, OUTPUT);
  digitalWrite(LED_BUILT_IN, LOW);

  // 步骤 1：初始化摄像头
  Serial.println("\nSTEP 1: Initializing camera...");
  esp_err_t camera_init_result = manage_camera_power(true);
  if (camera_init_result == ESP_OK) {
    Serial.println("[Camera] Initialized successfully!");
  } else {
    Serial.printf("[Camera] FAILED (error: 0x%x)\n", camera_init_result);
  }

  // 延时 2 秒，等待电压和内存状态稳定
  delay(2000); 

  // 步骤 2：初始化网络
  framework_network_init();

  // 构建 MQTT 主题
  String raw_mac = WiFi.macAddress();
  String mac = raw_mac;
  mac.replace(":", "");
  mqtt_client_id = "Device_" + mac;
  topic_sub = "/iot/device/" + mac + "/down";   // 下行（接收指令）
  topic_pub = "/iot/device/" + mac + "/up";     // 上行（发送数据）

  Serial.println("\nSTEP 3: MQTT & HTTP Stream Config");
  Serial.print("MAC: "); Serial.println(raw_mac);
  
  // 配置 MQTT 客户端
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback([](char* t, byte* p, unsigned int l) {
    // MQTT 消息回调：处理来自后端的指令
    String m = ""; 
    for (int i = 0; i < l; i++) m += (char)p[i];
    Serial.printf("MQTT RX: %s\n", m.c_str());
    business_command_router(m);  // 路由到具体的业务处理
  });

  // 创建 MQTT 后台任务（优先级 1，核心 0）
  xTaskCreateUniversal(mqtt_task, "mqtt", 8192, NULL, 1, NULL, 0);
  
  // 启动本地 HTTP 视频流服务
  start_httpd();
  
  Serial.println("System initialized successfully.");
}

/**
 * Arduino loop() 函数
 * 
 * 主循环：持续监听 UART、发送心跳
 */
void loop() {
  // 监听 UART 来自 STM32 的数据
  business_uart_listen();

  // 发送心跳消息
  static unsigned long last_h = 0;
  if (millis() - last_h > 15000) {  // 每 15 秒发送一次心跳
    if (mqttClient.connected()) {
      StaticJsonDocument<256> doc;
      doc["type"] = "heartbeat";
      doc["uptime"] = millis() / 1000;      // 设备运行时长（秒）
      doc["count"] = ++heartbeat_count;     // 心跳计数
      doc["ip_address"] = WiFi.localIP().toString();
      
      String payload;
      serializeJson(doc, payload);
      mqttClient.publish(topic_pub.c_str(), payload.c_str());
    }
    last_h = millis();
  }
}


// ------------------- 摄像头初始化 -------------------
esp_err_t manage_camera_power(bool enable) {
  if (enable && !is_camera_active) {
    camera_config_t config;
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sccb_sda = SIOD_GPIO_NUM;
    config.pin_sccb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    
    // 👇 极其关键的稳定性降级参数
    config.xclk_freq_hz = 10000000;      // 降频到 10MHz，极大提升信号抗干扰能力
    config.frame_size = FRAMESIZE_VGA;   // 640x480 分辨率
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 20;            // 画质调低（数字越大质量越低），减小 DMA 压力
    config.fb_count = 2;                 // 开启双缓冲

    esp_err_t err = esp_camera_init(&config);
    if (err == ESP_OK) {
      is_camera_active = true;
      sensor_t* s = esp_camera_sensor_get();
      s->set_vflip(s, 1); // 垂直翻转，视你的摄像头安装方向而定
    }
    return err;
  }
  return ESP_OK;
}

// ------------------- 串口指令路由 -------------------
void send_hex_to_stm32(uint8_t cmd, uint8_t data) {
  uint8_t frame[6] = { 0xAA, 0x55, cmd, 0x01, data, (uint8_t)((cmd + 0x01 + data) & 0xFF) };
  SerialSTM.write(frame, 6);
  Serial.printf("UART TX: 0x%02X\n", cmd);
}

void business_command_router(String json_msg) {
  JsonDocument doc;
  if (deserializeJson(doc, json_msg)) return;

  const char* cmd = doc["cmd"];
  if (!cmd) return;

  if (strcmp(cmd, "open_door") == 0) send_hex_to_stm32(0x01, 0x01);
  else if (strcmp(cmd, "alarm") == 0) send_hex_to_stm32(0x04, 0x01);
  else if (strcmp(cmd, "query_status") == 0) send_hex_to_stm32(0x05, 0x00);
  else if (strcmp(cmd, "reboot") == 0) ESP.restart();
  else if (strcmp(cmd, "led_control") == 0) {
    static bool led_state = false;
    led_state = !led_state;
    digitalWrite(LED_BUILT_IN, led_state ? HIGH : LOW);
    Serial.printf("Test Case: LED %s\n", led_state ? "ON" : "OFF");
  }
}

void business_uart_listen() {
  while (SerialSTM.available()) {
    static uint8_t state = 0, rx_cmd, rx_len, rx_data;
    uint8_t b = SerialSTM.read();
    switch (state) {
      case 0: if (b == 0xAA) state = 1; break;
      case 1: if (b == 0x55) state = 2; else state = 0; break;
      case 2: rx_cmd = b; state = 3; break;
      case 3: rx_len = b; state = 4; break;
      case 4: rx_data = b; state = 5; break;
      case 5:
        if (b == ((rx_cmd + rx_len + rx_data) & 0xFF)) {
          String payload = "{\"type\":\"hw_report\",\"mac\":\"" + WiFi.macAddress() + "\",\"cmd\":" + String(rx_cmd) + ",\"data\":" + String(rx_data) + "}";
          if (mqttClient.connected()) {
            mqttClient.publish(topic_pub.c_str(), payload.c_str());
          }
        }
        state = 0;
        break;
    }
  }
}

// ------------------- MQTT 任务 -------------------
void mqtt_task(void* pv) {
  for (;;) {
    if (WiFi.status() == WL_CONNECTED) {
      if (!mqttClient.connected()) {
        String mac = WiFi.macAddress();
        mac.replace(":", "");
        String lwt_topic = "/iot/device/" + mac + "/status";
        String local_ip = WiFi.localIP().toString();
        String lwt_payload = "{\"status\":\"offline\",\"ip_address\":\"" + local_ip + "\"}";

        if (mqttClient.connect(mqtt_client_id.c_str(), lwt_topic.c_str(), 1, true, lwt_payload.c_str())) {
          Serial.println("MQTT Connected");
          String online_payload = "{\"status\":\"online\",\"ip_address\":\"" + local_ip + "\"}";
          mqttClient.publish(lwt_topic.c_str(), online_payload.c_str(), true);
          mqttClient.subscribe(topic_sub.c_str());
        } else {
          vTaskDelay(5000 / portTICK_PERIOD_MS);
        }
      } else {
        mqttClient.loop();
      }
    }
    vTaskDelay(50 / portTICK_PERIOD_MS);
  }
}

// ------------------- 本地局域网视频流服务 -------------------
static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[Stream] ERROR: Failed to get frame");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");
  
  active_viewers++;
  Serial.printf("[Stream] Client connected. Active viewers: %d\n", active_viewers);
  
  while (WiFi.isConnected()) {
    camera_fb_t *frame = esp_camera_fb_get();
    if (!frame) {
      Serial.println("[Stream] Failed to get frame during stream");
      break;
    }

    size_t hlen = snprintf((char *)fb->buf, 64,
                          "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                          frame->len);
    
    if (httpd_resp_send_chunk(req, (const char *)fb->buf, hlen) != ESP_OK ||
        httpd_resp_send_chunk(req, (const char *)frame->buf, frame->len) != ESP_OK ||
        httpd_resp_send_chunk(req, "\r\n--frame\r\n", 10) != ESP_OK) {
      esp_camera_fb_return(frame);
      break;
    }
    
    esp_camera_fb_return(frame);
    delay(20); // 给系统一点喘息时间
  }
  
  active_viewers--;
  Serial.printf("[Stream] Client disconnected. Active viewers: %d\n", active_viewers);

  esp_camera_fb_return(fb);
  return ESP_OK;
}

void start_httpd() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;
  config.ctrl_port = 8000;
  
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_uri_t uri_handler = { .uri = "/stream", .method = HTTP_GET, .handler = stream_handler, .user_ctx = NULL };
    if (httpd_register_uri_handler(stream_httpd, &uri_handler) == ESP_OK) {
      Serial.println("[Stream] Local HTTP server started on port 81");
      Serial.println("[Stream] You can view it at: http://<IP>:81/stream");
    }
  }
}

// ------------------- 主流程 -------------------
void setup() {
  Serial.begin(115200);
  SerialSTM.begin(115200, SERIAL_8N1, STM_RX_PIN, STM_TX_PIN);

  pinMode(LED_BUILT_IN, OUTPUT);
  digitalWrite(LED_BUILT_IN, LOW);

  // 1. 优先初始化摄像头（错峰启动，防止电压瞬降）
  Serial.println("\nSTEP 1: Initializing camera...");
  esp_err_t camera_init_result = manage_camera_power(true);
  if (camera_init_result == ESP_OK) {
    Serial.println("[Camera] Initialized successfully!");
  } else {
    Serial.printf("[Camera] FAILED to initialize (error: 0x%x)\n", camera_init_result);
  }

  // 延时2秒，等待主板电压与内存状态平稳
  delay(2000); 

  // 2. 初始化网络
  framework_network_init();

  String raw_mac = WiFi.macAddress();
  String mac = raw_mac;
  mac.replace(":", "");
  mqtt_client_id = "Device_" + mac;
  topic_sub = "/iot/device/" + mac + "/down";
  topic_pub = "/iot/device/" + mac + "/up";

  Serial.println("\nSTEP 3: MQTT & HTTP Stream Config");
  Serial.print("MAC: "); Serial.println(raw_mac);
  
  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback([](char* t, byte* p, unsigned int l) {
    String m = ""; for (int i = 0; i < l; i++) m += (char)p[i];
    Serial.printf("MQTT RX: %s\n", m.c_str());
    business_command_router(m);
  });

  xTaskCreateUniversal(mqtt_task, "mqtt", 8192, NULL, 1, NULL, 0);
  
  // 3. 启动本地流媒体服务器
  start_httpd();
  
  Serial.println("System Running stably.");
}

void loop() {
  business_uart_listen();

  // 简单心跳
  static unsigned long last_h = 0;
  if (millis() - last_h > 15000) {
    if (mqttClient.connected()) {
      StaticJsonDocument<256> doc;
      doc["type"] = "heartbeat";
      doc["uptime"] = millis() / 1000;
      doc["count"] = ++heartbeat_count;
      doc["ip_address"] = WiFi.localIP().toString();
      
      String payload;
      serializeJson(doc, payload);
      mqttClient.publish(topic_pub.c_str(), payload.c_str());
    }
    last_h = millis();
  }
}