#include <WiFi.h>
#include <WiFiClient.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <time.h>
#include "esp_camera.h"
#include "esp_http_server.h"

#define CAMERA_MODEL_ESP32S3_EYE
#include "camera_pins.h"

// Config
#define BOOT_BUTTON_PIN 0
const char* mqtt_server = "mqtt.5i03.cn";
const int mqtt_port = 1883;

#define BACKEND_HOST "dev.api.5i03.cn"
#define BACKEND_PORT 80
#define UPLOAD_ENDPOINT "/api/device/upload_snapshot"

#define DEVICE_SECRET "device_secret_key_v1"
#define UPLOAD_INTERVAL_MS 1000  // 1秒上传一次
// 已经测试没有占用好的接口
#define LED_BUILT_IN 2// 已经测试没有占用好的接口，不要动
#define STM_RX_PIN 21   // 已经测试没有占用好的接口不要动
#define STM_TX_PIN 4  
HardwareSerial SerialSTM(1);

// Globals
String mqtt_client_id, topic_sub, topic_pub;
WiFiClient espClient;
PubSubClient mqttClient(espClient);

struct FrameUploadState {
  unsigned long last_upload_time = 0;
  int consecutive_failures = 0;
  bool is_uploading = false;
  unsigned long total_uploads = 0;
  unsigned long total_bytes = 0;
};
FrameUploadState frame_upload_state;

httpd_handle_t stream_httpd = NULL;
bool is_camera_active = false;
unsigned long heartbeat_count = 0;
volatile int active_viewers = 0;

// Init Network
void framework_network_init() {
  Serial.println("\nSTEP 1: Network Init");
  pinMode(BOOT_BUTTON_PIN, INPUT_PULLUP);

  WiFi.mode(WIFI_STA);
  WiFi.begin();

  Serial.print("Connecting WiFi ");
  int timeout = 20;
  while (WiFi.status() != WL_CONNECTED && timeout > 0) {
    delay(500);
    Serial.print(".");
    timeout--;
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
  
  // NTP Time Sync
  configTime(8 * 3600, 0, "ntp.aliyun.com", "pool.ntp.org");
  Serial.println("Syncing time with NTP...");
  struct tm timeinfo;
  if (getLocalTime(&timeinfo, 10000)) {
    Serial.println("Time synced successfully");
  } else {
    Serial.println("Failed to sync time, will retry later");
  }
}

// Camera Power Management
esp_err_t manage_camera_power(bool enable, bool forced = false) {
  if (!enable && is_camera_active) {
    if (active_viewers > 0 && !forced) return ESP_FAIL;
    esp_camera_deinit();
    is_camera_active = false;
    return ESP_OK;
  }

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
    config.xclk_freq_hz = 20000000;
    config.frame_size = FRAMESIZE_VGA;
    config.pixel_format = PIXFORMAT_JPEG;
    config.grab_mode = CAMERA_GRAB_LATEST;
    config.fb_location = CAMERA_FB_IN_PSRAM;
    config.jpeg_quality = 12;
    config.fb_count = 2;

    esp_err_t err = esp_camera_init(&config);
    if (err == ESP_OK) {
      is_camera_active = true;
      sensor_t* s = esp_camera_sensor_get();
      s->set_vflip(s, 1);
    }
    return err;
  }
  return ESP_OK;
}

// UART TX
void send_hex_to_stm32(uint8_t cmd, uint8_t data) {
  uint8_t frame[6] = { 0xAA, 0x55, cmd, 0x01, data, (uint8_t)((cmd + 0x01 + data) & 0xFF) };
  SerialSTM.write(frame, 6);
  Serial.printf("UART TX: 0x%02X\n", cmd);
}

// MQTT to UART Router
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

// UART RX
void business_uart_listen() {
  while (SerialSTM.available()) {
    static uint8_t state = 0, rx_cmd, rx_len, rx_data;
    uint8_t b = SerialSTM.read();
    switch (state) {
      case 0:
        if (b == 0xAA) state = 1;
        break;
      case 1:
        if (b == 0x55) state = 2;
        else state = 0;
        break;
      case 2:
        rx_cmd = b;
        state = 3;
        break;
      case 3:
        rx_len = b;
        state = 4;
        break;
      case 4:
        rx_data = b;
        state = 5;
        break;
      case 5:
        if (b == ((rx_cmd + rx_len + rx_data) & 0xFF)) {
          String payload = "{\"type\":\"hw_report\",\"mac\":\"" + WiFi.macAddress() + "\",\"cmd\":" + String(rx_cmd) + ",\"data\":" + String(rx_data) + "}";
          if (mqttClient.connected()) {
            mqttClient.publish(topic_pub.c_str(), payload.c_str());
            Serial.printf("UART RX: CMD=0x%02X\n", rx_cmd);
          }
        }
        state = 0;
        break;
    }
  }
}

// MQTT Task
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

// HTTP Upload Task
void poll_frame_upload() {
  // 检查前置条件
  if (!is_camera_active) return;  // 相机未初始化
  if (WiFi.status() != WL_CONNECTED) return;  // WiFi未连接
  
  unsigned long now = millis();
  if (now - frame_upload_state.last_upload_time < UPLOAD_INTERVAL_MS || frame_upload_state.is_uploading) return;

  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("[Upload] ERROR: Failed to capture frame");
    return;
  }

  frame_upload_state.is_uploading = true;
  String url = "http://" + String(BACKEND_HOST) + ":" + String(BACKEND_PORT) + UPLOAD_ENDPOINT;

  HTTPClient http;
  http.begin(url);
  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-Device-MAC", WiFi.macAddress());  // 格式：AA:BB:CC:DD:EE:FF
  http.addHeader("X-Device-Secret", DEVICE_SECRET);
  http.setTimeout(5000);  // 设置5秒超时

  Serial.printf("[Upload] Uploading %d bytes to %s\n", fb->len, url.c_str());
  int http_code = http.POST(fb->buf, fb->len);
  if (http_code == 200) {
    frame_upload_state.consecutive_failures = 0;  // 重置失败计数
    frame_upload_state.total_uploads++;
    frame_upload_state.total_bytes += fb->len;
    Serial.printf("[Upload] OK: Snapshot uploaded (%d bytes, total: %lu, avg: %.1f KB)\n", 
                  fb->len, frame_upload_state.total_uploads, 
                  (float)frame_upload_state.total_bytes / frame_upload_state.total_uploads / 1024);
  } else if (http_code > 0) {
    frame_upload_state.consecutive_failures++;
    Serial.printf("[Upload] FAIL: HTTP %d, body: %s, failures: %d\n", 
                  http_code, http.getString().c_str(), frame_upload_state.consecutive_failures);
  } else {
    frame_upload_state.consecutive_failures++;
    Serial.printf("[Upload] ERROR: Connection failed (code: %d), failures: %d\n", 
                  http_code, frame_upload_state.consecutive_failures);
  }

  esp_camera_fb_return(fb);
  http.end();
  frame_upload_state.is_uploading = false;
  frame_upload_state.last_upload_time = millis();
}

void setup() {
  Serial.begin(115200);
  SerialSTM.begin(115200, SERIAL_8N1, STM_RX_PIN, STM_TX_PIN);

  // Init LED for testing
  pinMode(LED_BUILT_IN, OUTPUT);
  digitalWrite(LED_BUILT_IN, LOW);

  framework_network_init();

  String raw_mac = WiFi.macAddress();
  String mac = raw_mac;
  mac.replace(":", "");
  mqtt_client_id = "Device_" + mac;
  topic_sub = "/iot/device/" + mac + "/down";
  topic_pub = "/iot/device/" + mac + "/up";

  Serial.println("\nSTEP 2: Config");
  Serial.print("MAC: ");
  Serial.println(raw_mac);
  Serial.print("MQTT ID: ");
  Serial.println(mqtt_client_id);
  Serial.print("SUB: ");
  Serial.println(topic_sub);
  Serial.print("PUB: ");
  Serial.println(topic_pub);
  Serial.print("MQTT Server: ");
  Serial.print(mqtt_server);
  Serial.print(":");
  Serial.println(mqtt_port);
  Serial.print("Upload URL: ");
  Serial.println("http://" + String(BACKEND_HOST) + ":" + String(BACKEND_PORT) + UPLOAD_ENDPOINT);
  Serial.println("");

  mqttClient.setServer(mqtt_server, mqtt_port);
  mqttClient.setCallback([](char* t, byte* p, unsigned int l) {
    String m = "";
    for (int i = 0; i < l; i++) m += (char)p[i];
    Serial.printf("MQTT RX: %s\n", m.c_str());
    business_command_router(m);
  });

  xTaskCreateUniversal(mqtt_task, "mqtt", 8192, NULL, 1, NULL, 0);
  
  // 初始化相机用于快照上传
  Serial.println("Initializing camera...");
  esp_err_t camera_init_result = manage_camera_power(true);
  if (camera_init_result == ESP_OK) {
    Serial.println("[Camera] Initialized successfully, snapshot upload enabled");
  } else {
    Serial.printf("[Camera] FAILED to initialize (error: 0x%x), snapshot upload disabled\n", camera_init_result);
  }
  
  Serial.println("System Running.");
}

void loop() {
  business_uart_listen();
  poll_frame_upload();

  static unsigned long last_h = 0;
  if (millis() - last_h > 15000) {
    if (mqttClient.connected()) {
      // 构建带有时间戳的心跳消息
      StaticJsonDocument<256> doc;
      doc["type"] = "heartbeat";
      doc["uptime"] = millis() / 1000; // 设备运行时间（秒）
      doc["count"] = ++heartbeat_count;
      doc["ip_address"] = WiFi.localIP().toString();
      
      // 添加 UTC 时间戳（如果时间已同步）
      struct tm timeinfo;
      if (getLocalTime(&timeinfo, 100)) {
        char timestamp[25];
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
        doc["timestamp"] = timestamp;
      }
      
      String payload;
      serializeJson(doc, payload);
      mqttClient.publish(topic_pub.c_str(), payload.c_str());
    }
    last_h = millis();
  }
}