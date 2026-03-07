#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "esp_camera.h"
#include "esp_http_server.h"

//芯片模型定义
#define CAMERA_MODEL_ESP32S3_EYE
#include "camera_pins.h"

//引脚配置
#define BOOT_BUTTON_PIN  0    // 启动按钮（长按触发 SmartConfig）
#define LED_BUILT_IN     2    // 内置 LED（GPIO2，状态指示）
#define STM_RX_PIN       21   // UART RX：接收来自 STM32 的数据（无摄像头冲突）
#define STM_TX_PIN       42   // UART TX：发送指令给 STM32（无摄像头冲突）

//MQTT 配置
const char* mqtt_server = "mqtt.5i03.cn"; // 基于emqx的开源部署版本
const int   mqtt_port   = 1883;

//全局对象
HardwareSerial  SerialSTM(1);         // UART1 与 STM32 通信
WiFiClient      espClient;
PubSubClient    mqttClient(espClient);

//全局变量
String          mqtt_client_id;
String          topic_sub;
String          topic_pub;
httpd_handle_t  stream_httpd    = NULL;
bool            is_camera_active = false;
unsigned long   heartbeat_count  = 0;
volatile int    active_viewers   = 0;



//  摄像头初始化

/**
 * 初始化 OV2640 摄像头
 * 引脚由 camera_pins.h 中的宏定义提供
 * 降频至 10MHz 提升抗干扰能力，使用 PSRAM 双缓冲
 */
esp_err_t manage_camera_power(bool enable) {
  if (!enable || is_camera_active) return ESP_OK;

  camera_config_t config;
  config.ledc_channel  = LEDC_CHANNEL_0;
  config.ledc_timer    = LEDC_TIMER_0;
  config.pin_d0        = Y2_GPIO_NUM;
  config.pin_d1        = Y3_GPIO_NUM;
  config.pin_d2        = Y4_GPIO_NUM;
  config.pin_d3        = Y5_GPIO_NUM;
  config.pin_d4        = Y6_GPIO_NUM;
  config.pin_d5        = Y7_GPIO_NUM;
  config.pin_d6        = Y8_GPIO_NUM;
  config.pin_d7        = Y9_GPIO_NUM;
  config.pin_xclk      = XCLK_GPIO_NUM;
  config.pin_pclk      = PCLK_GPIO_NUM;
  config.pin_vsync     = VSYNC_GPIO_NUM;
  config.pin_href      = HREF_GPIO_NUM;
  config.pin_sccb_sda  = SIOD_GPIO_NUM;
  config.pin_sccb_scl  = SIOC_GPIO_NUM;
  config.pin_pwdn      = PWDN_GPIO_NUM;
  config.pin_reset     = RESET_GPIO_NUM;

  config.xclk_freq_hz  = 10000000;           // 降频 10MHz，提升稳定性
  config.frame_size    = FRAMESIZE_VGA;       // 640x480
  config.pixel_format  = PIXFORMAT_JPEG;
  config.grab_mode     = CAMERA_GRAB_LATEST;
  config.fb_location   = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality  = 20;                  // 质量适中，减轻 DMA 压力
  config.fb_count      = 2;                   // 双缓冲

  esp_err_t err = esp_camera_init(&config);
  if (err == ESP_OK) {
    is_camera_active = true;
    sensor_t* s = esp_camera_sensor_get();
    s->set_vflip(s, 1);   // 垂直翻转，根据安装方向调整
    Serial.println("[Camera] Initialized successfully!");
  } else {
    Serial.printf("[Camera] FAILED (error: 0x%x)\n", err);
  }
  return err;
}



//  WiFi 初始化

/**
 * 尝试连接上次保存的 WiFi（10 秒超时）
 * 失败后启动 SmartConfig，等待手机扫码配网
 * 连接成功后同步 NTP 时间
 */
void framework_network_init() {
  Serial.println("\nSTEP 2: Network Init");
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.begin();

  Serial.print("Connecting WiFi");
  int timeout = 20;
  while (WiFi.status() != WL_CONNECTED && timeout-- > 0) {
    delay(500);
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nSmartConfig Mode...");
    WiFi.beginSmartConfig();
    while (!WiFi.smartConfigDone()) {
      delay(500);
      Serial.print(".");
    }
  }

  Serial.println("\nWiFi Connected");
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // NTP 时间同步（UTC+8）
  configTime(8 * 3600, 0, "ntp.aliyun.com", "pool.ntp.org");
  Serial.println("NTP time syncing...");
}



//  UART 串口通信（与 STM32）

/**
 * 向 STM32 发送十六进制指令帧
 * 帧格式：| 0xAA | 0x55 | CMD | LEN(0x01) | DATA | CHECKSUM |
 * 校验和 = (CMD + LEN + DATA) & 0xFF
 */
void send_hex_to_stm32(uint8_t cmd, uint8_t data) {
  uint8_t frame[6] = {
    0xAA,
    0x55,
    cmd,
    0x01,
    data,
    (uint8_t)((cmd + 0x01 + data) & 0xFF)
  };
  SerialSTM.write(frame, 6);
  Serial.printf("[UART] TX: CMD=0x%02X DATA=0x%02X\n", cmd, data);
}

/**
 * 业务指令路由器
 * 解析 MQTT 下发的 JSON 指令，映射到对应硬件操作
 *
 * 支持指令：
 *   open_door    → 0x01：开锁
 *   alarm        → 0x04：报警
 *   query_status → 0x05：查询状态
 *   reboot       → 重启 ESP32
 *   led_control  → 切换内置 LED（调试用）
 */
void business_command_router(String json_msg) {
  JsonDocument doc;
  if (deserializeJson(doc, json_msg)) {
    Serial.println("[CMD] JSON parse failed");
    return;
  }

  const char* cmd = doc["cmd"];
  if (!cmd) return;

  if      (strcmp(cmd, "open_door")     == 0) send_hex_to_stm32(0x01, 0x01);
  else if (strcmp(cmd, "alarm")         == 0) send_hex_to_stm32(0x04, 0x01);
  else if (strcmp(cmd, "query_status")  == 0) send_hex_to_stm32(0x05, 0x00);
  else if (strcmp(cmd, "reboot")        == 0) ESP.restart();
  else if (strcmp(cmd, "led_control")   == 0) {
    static bool led_state = false;
    led_state = !led_state;
    digitalWrite(LED_BUILT_IN, led_state ? HIGH : LOW);
    Serial.printf("[CMD] LED %s\n", led_state ? "ON" : "OFF");
  } else {
    Serial.printf("[CMD] Unknown command: %s\n", cmd);
  }
}

/**
 * UART 状态机监听
 * 持续读取 STM32 发来的数据帧，校验通过后上报 MQTT
 *
 * 状态机：
 *   0 → 等待 0xAA
 *   1 → 等待 0x55
 *   2 → 读取 CMD
 *   3 → 读取 LEN
 *   4 → 读取 DATA
 *   5 → 校验 CHECKSUM，通过则发布 MQTT
 */
void business_uart_listen() {
  static uint8_t state = 0, rx_cmd = 0, rx_len = 0, rx_data = 0;

  while (SerialSTM.available()) {
    uint8_t b = SerialSTM.read();
    switch (state) {
      case 0: if (b == 0xAA) state = 1;                    break;
      case 1: state = (b == 0x55) ? 2 : 0;                 break;
      case 2: rx_cmd  = b; state = 3;                       break;
      case 3: rx_len  = b; state = 4;                       break;
      case 4: rx_data = b; state = 5;                       break;
      case 5:
        if (b == ((rx_cmd + rx_len + rx_data) & 0xFF)) {
          String payload = "{\"type\":\"hw_report\",\"mac\":\""
                         + WiFi.macAddress()
                         + "\",\"cmd\":"  + String(rx_cmd)
                         + ",\"data\":" + String(rx_data) + "}";
          if (mqttClient.connected()) {
            mqttClient.publish(topic_pub.c_str(), payload.c_str());
            Serial.printf("[UART] RX OK → MQTT: %s\n", payload.c_str());
          }
        } else {
          Serial.println("[UART] Checksum error, frame dropped");
        }
        state = 0;
        break;
    }
  }
}



//  MQTT 后台任务（运行在 Core 0）

/**
 * 维护 MQTT 长连接，断线自动重连
 * LWT（遗言）：设备掉线时自动发布 offline 消息
 */
void mqtt_task(void* pv) {
  for (;;) {
    if (WiFi.status() == WL_CONNECTED) {
      if (!mqttClient.connected()) {
        String mac = WiFi.macAddress();
        mac.replace(":", "");
        String lwt_topic   = "/iot/device/" + mac + "/status";
        String local_ip    = WiFi.localIP().toString();
        String lwt_payload = "{\"status\":\"offline\",\"ip_address\":\"" + local_ip + "\"}";

        if (mqttClient.connect(mqtt_client_id.c_str(),
                               lwt_topic.c_str(), 1, true,
                               lwt_payload.c_str())) {
          Serial.println("[MQTT] Connected");
          String online_payload = "{\"status\":\"online\",\"ip_address\":\"" + local_ip + "\"}";
          mqttClient.publish(lwt_topic.c_str(), online_payload.c_str(), true);
          mqttClient.subscribe(topic_sub.c_str());
          Serial.printf("[MQTT] Subscribed: %s\n", topic_sub.c_str());
        } else {
          Serial.printf("[MQTT] Connect failed, rc=%d, retry in 5s\n", mqttClient.state());
          vTaskDelay(5000 / portTICK_PERIOD_MS);
        }
      } else {
        mqttClient.loop();
      }
    }
    vTaskDelay(50 / portTICK_PERIOD_MS);
  }
}



//  本地 HTTP 视频流服务（端口 81）

/**
 * Motion JPEG 流处理函数
 * URL: http://<ESP32_IP>:81/stream
 * 使用双缓冲帧，约 20fps
 */
static esp_err_t stream_handler(httpd_req_t* req) {
  // 预先获取一帧用于复用帧头缓冲区
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[Stream] ERROR: Failed to get initial frame");
    httpd_resp_send_500(req);
    return ESP_FAIL;
  }

  httpd_resp_set_type(req, "multipart/x-mixed-replace;boundary=frame");

  active_viewers++;
  Serial.printf("[Stream] Client connected. Active: %d\n", active_viewers);

  while (WiFi.isConnected()) {
    camera_fb_t* frame = esp_camera_fb_get();
    if (!frame) {
      Serial.println("[Stream] Failed to capture frame");
      break;
    }

    // 构建 MIME 帧头
    size_t hlen = snprintf((char*)fb->buf, 64,
                           "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n",
                           frame->len);

    // 发送：帧头 + JPEG 数据 + 边界符
    if (httpd_resp_send_chunk(req, (const char*)fb->buf,   hlen)       != ESP_OK ||
        httpd_resp_send_chunk(req, (const char*)frame->buf, frame->len) != ESP_OK ||
        httpd_resp_send_chunk(req, "\r\n--frame\r\n",       10)         != ESP_OK) {
      esp_camera_fb_return(frame);
      break;
    }

    esp_camera_fb_return(frame);
    delay(20);  // ~50fps 上限，实际约 20fps
  }

  active_viewers--;
  Serial.printf("[Stream] Client disconnected. Active: %d\n", active_viewers);

  esp_camera_fb_return(fb);
  return ESP_OK;
}

/**
 * 启动 HTTP 服务器并注册 /stream 路由
 */
void start_httpd() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 81;
  config.ctrl_port   = 8000;

  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_uri_t uri = {
      .uri      = "/stream",
      .method   = HTTP_GET,
      .handler  = stream_handler,
      .user_ctx = NULL
    };
    if (httpd_register_uri_handler(stream_httpd, &uri) == ESP_OK) {
      Serial.println("[Stream] HTTP server started on port 81");
      Serial.print("[Stream] URL: http://");
      Serial.print(WiFi.localIP());
      Serial.println(":81/stream");
    }
  } else {
    Serial.println("[Stream] ERROR: Failed to start HTTP server");
  }
}



//  setup() - 初始化入口

void setup() {
  Serial.begin(115200);

  // 初始化 UART1 与 STM32 通信
  // RX=GPIO21, TX=GPIO42（均不与摄像头引脚冲突）
  SerialSTM.begin(115200, SERIAL_8N1, STM_RX_PIN, STM_TX_PIN);

  pinMode(LED_BUILT_IN, OUTPUT);
  digitalWrite(LED_BUILT_IN, LOW);

  // STEP 1：初始化摄像头（优先，防止后续电压瞬降）
  Serial.println("\nSTEP 1: Camera Init");
  manage_camera_power(true);

  // 等待电压与内存状态平稳
  delay(2000);

  // STEP 2：初始化 WiFi 和 NTP
  framework_network_init();

  // STEP 3：配置 MQTT
  Serial.println("\nSTEP 3: MQTT & Stream Config");
  String raw_mac = WiFi.macAddress();
  String mac = raw_mac;
  mac.replace(":", "");

  mqtt_client_id = "Device_" + mac;
  topic_sub      = "/iot/device/" + mac + "/down";
  topic_pub      = "/iot/device/" + mac + "/up";

  Serial.print("MAC: ");   Serial.println(raw_mac);
  Serial.print("SUB: ");   Serial.println(topic_sub);
  Serial.print("PUB: ");   Serial.println(topic_pub);

  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback([](char* t, byte* p, unsigned int l) {
    String msg = "";
    for (unsigned int i = 0; i < l; i++) msg += (char)p[i];
    Serial.printf("[MQTT] RX: %s\n", msg.c_str());
    business_command_router(msg);
  });

  // 在 Core 0 创建 MQTT 后台任务
  xTaskCreateUniversal(mqtt_task, "mqtt_task", 8192, NULL, 1, NULL, 0);

  // STEP 4：启动本地视频流服务
  start_httpd();

  Serial.println("System Ready");
}



//  loop() - 主循环

void loop() {
  // 持续监听 STM32 UART 数据
  business_uart_listen();

  // 每 15 秒发送一次心跳到 MQTT
  static unsigned long last_heartbeat = 0;
  if (millis() - last_heartbeat > 15000) {
    last_heartbeat = millis();
    if (mqttClient.connected()) {
      StaticJsonDocument<256> doc;
      doc["type"]       = "heartbeat";
      doc["uptime"]     = millis() / 1000;
      doc["count"]      = ++heartbeat_count;
      doc["ip_address"] = WiFi.localIP().toString();

      String payload;
      serializeJson(doc, payload);
      mqttClient.publish(topic_pub.c_str(), payload.c_str());
      Serial.printf("[Heartbeat] #%lu uptime=%lus\n",
                    heartbeat_count, millis() / 1000);
    }
  }
}
