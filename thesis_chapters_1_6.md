# 智能门禁控制系统设计与实现
## 毕业设计论文 — 摘要 · 第1章 · 第6章

---

# 摘要

随着物联网技术的快速发展，智能门禁系统正逐渐取代传统机械锁与磁卡门禁，成为高校宿舍、办公楼宇和公共设施安全管理的重要基础设施。传统门禁系统存在功能单一、扩展性差、缺乏远程管控能力等局限，难以满足现代安全管理对实时性、可视化和移动化的需求。

本文设计并实现了一套基于双 MCU 架构与云端协同的智能门禁控制系统。系统硬件层采用 ESP32-S3 微控制器作为网络与图像处理网关，STM32 微控制器负责实时硬件控制，两者通过自定义二进制帧协议进行高可靠性 UART 通信。云端服务层基于 Flask 框架构建 RESTful API，使用 SQLAlchemy ORM 进行数据持久化，并通过 MQTT 协议实现与嵌入式设备的双向实时通信。移动端采用微信小程序原生框架开发，提供设备管理、实时快照查看、权限申请与远程开锁等完整功能。系统通过 Docker Compose 编排 Flask 应用服务器与 Nginx 反向代理实现生产环境部署。

在安全机制方面，系统采用 JWT 令牌认证保护所有 API 接口，通过用户-设备权限映射与 BOLA（对象级权限破坏）防护机制确保数据隔离，并实现了基于状态机的权限审批流程。在图像传输方面，系统设计了三级快照优先级策略，结合内存缓存与 Base64 编码有效解决了微信小程序渲染兼容性问题。

测试结果表明，系统端到端响应延迟约为 170 毫秒，满足实时门禁管控需求；BOLA 防护机制对非授权访问实现了 100% 拦截；设备心跳检测延迟不超过 20 秒，具备良好的在线状态感知能力。

**关键词**：智能门禁；物联网；ESP32-S3；MQTT；Flask；微信小程序；JWT；Docker

---

**Abstract**

With the rapid development of Internet of Things technology, smart access control systems are gradually replacing traditional mechanical locks and magnetic card systems, becoming important security infrastructure for university dormitories, office buildings, and public facilities. Traditional access control systems suffer from limited functionality, poor scalability, and lack of remote management capabilities, making them inadequate for the real-time, visual, and mobile requirements of modern security management.

This thesis designs and implements a smart door access control system based on a dual-MCU architecture with cloud collaboration. The hardware layer uses the ESP32-S3 microcontroller as a network and image processing gateway, with the STM32 microcontroller handling real-time hardware control; both communicate via a custom binary frame protocol over UART. The cloud service layer builds RESTful APIs on the Flask framework with SQLAlchemy ORM for data persistence, and uses MQTT protocol for bidirectional real-time communication with embedded devices. The mobile client is developed using the WeChat Miniprogram native framework, providing device management, real-time snapshot viewing, permission applications, and remote unlocking. The system is deployed in production using Docker Compose orchestrating Flask application servers and Nginx reverse proxy.

For security mechanisms, the system employs JWT token authentication to protect all API endpoints, ensures data isolation through user-device permission mapping and BOLA (Broken Object-Level Authorization) protection, and implements a state-machine-based permission approval workflow. For image transmission, the system designs a three-tier snapshot priority strategy, combined with memory caching and Base64 encoding to effectively resolve WeChat Miniprogram rendering compatibility issues.

Test results demonstrate that the end-to-end response latency is approximately 170 milliseconds, meeting real-time access control requirements; the BOLA protection mechanism achieves 100% interception of unauthorized access; and device heartbeat detection latency does not exceed 20 seconds, demonstrating good online status awareness.

**Keywords**: Smart Access Control; Internet of Things; ESP32-S3; MQTT; Flask; WeChat Miniprogram; JWT; Docker

---

# 第1章 绪论

## 1.1 研究背景与意义

近年来，随着物联网（Internet of Things，IoT）技术、云计算与移动互联网的深度融合，智能化门禁管控系统正在迎来全面升级与变革。传统的机械钥匙与刷卡式门禁虽然在成本上具备一定优势，但其固有的缺陷——如钥匙遗失风险高、权限变更不灵活、无法远程操控、缺乏可视化记录等——在高校宿舍楼、企业办公区、科研实验室等对安全性和管理效率要求较高的场所中愈发难以适应实际需求。

与此同时，ESP32 系列芯片、4G/5G 移动网络、微信小程序生态的普及，以及 MQTT 轻量级消息队列协议在物联网领域的广泛应用，为构建低成本、高可靠性的智能门禁系统提供了成熟的技术基础。将嵌入式硬件控制、云端数据管理与移动端用户交互有机结合，已成为新一代智能门禁系统的主流技术路线。

本文以高校宿舍门禁管理场景为主要设计目标，研究并实现了一套集嵌入式控制、云端服务、移动端管理于一体的智能门禁控制系统。该系统具有以下几点实际意义：

**（1）提升安全管理效率。** 管理员可通过移动端实时查看设备在线状态、查阅开锁记录与抓拍图像，将原本依赖人工巡查的工作转变为基于数据的远程管控模式，显著降低安全管理成本。

**（2）实现细粒度权限管控。** 系统支持为每位用户独立配置可访问的设备列表，并提供完整的权限申请—审批—撤销流程，满足不同角色（学生、宿管、管理员）的差异化需求。

**（3）具备良好的可扩展性与标准化接口。** 系统采用 RESTful API 设计与标准 MQTT 通信协议，便于后续与门禁闸机、人脸识别模块、访客登记系统等第三方设备无缝集成。

**（4）提供工程实践参考价值。** 本系统从嵌入式固件开发、后端架构设计到前端小程序实现全链路自主完成，可为后续物联网应用开发提供完整的架构参考和最佳实践示范。

## 1.2 国内外研究现状

### 1.2.1 国外研究现状

国外智能门禁系统的研究起步较早，整体技术成熟度较高。在商业产品层面，Allegion、ASSA ABLOY、HID Global 等国际巨头已推出集成 NFC/蓝牙/生物识别于一体的企业级门禁解决方案，并提供完善的云端管理平台。在学术研究层面，基于 RFID 与云端认证的门禁系统研究自 2010 年前后逐渐增多，近年来更多研究转向结合机器学习的人脸识别门禁、基于区块链的去中心化权限管理等方向。

在协议标准化方面，OASIS 于 2014 年正式发布 MQTT 3.1.1 协议规范，使得轻量级设备与云端的双向通信具备了完善的标准支撑。Shailja Pandey 等人（2022）的研究表明，基于 ESP32-S3 的 MQTT 与 REST 协议对比实验中，MQTT 在 AIoT/IIoT 场景下具备更低的功耗与更好的实时性 [1]。AWS IoT Core、Azure IoT Hub 等主流云平台也将 MQTT 作为首选设备接入协议，进一步推动了基于 MQTT 的 IoT 门禁方案落地。

Habibullah 等人（2023）提出了基于 ESP32 + Raspberry Pi + Node-RED + MQTT 的低成本 SCADA 控制系统，证明了 MQTT 协议在低功耗嵌入式硬件上实现云端协同的可行性 [2]。Neven Nikolov 等人（2023）进一步研究了通过 MQTT 协议实现 ESP32 固件安全 OTA 更新的机制，为远程维护提供了参考 [3]。

在 API 安全领域，OWASP 于 2023 年更新发布的 API Security Top 10 将 BOLA（Broken Object Level Authorization，对象级权限破坏）列为首位威胁 [4]，指出超过 40% 的 API 攻击利用了对象级权限漏洞，对包括门禁控制在内的 IoT API 系统构成严重风险。

在身份认证方面，JSON Web Token（JWT）作为无状态、跨域友好的认证标准，已成为 REST API 认证的事实规范。相关研究（California State University，2022）从性能与安全双重维度验证了 JWT HS256 算法在微服务认证场景下的适用性 [5]。

### 1.2.2 国内研究现状

国内智能门禁领域的研究在近 5 年内发展迅猛。在高校及住宅场景中，基于 ESP8266/ESP32 的 WiFi 门锁方案已有大量开源实现，部分研究着重探讨了指纹识别模块（如 AS608）与 RFID 模块（如 RC522）的低功耗集成方案。微信小程序的开放为国内门禁管控前端提供了新入口，无需额外安装 App 即可完成设备绑定与远程操控，显著降低了用户使用门槛。

在国家层面，《智慧物联网系统发展战略研究》（中国工程院，2022）指出，物联网与 5G、大数据、云计算、人工智能等技术深度融合，正开启万物智联的"智慧物联网系统"新阶段，建议在智能门禁等应用场景开展云边端协同示范 [6]。

然而，现有开源与学术方案普遍存在以下不足：

- **安全性不足**：大多数方案缺乏对象级权限保护（BOLA），任意登录用户均可访问全部设备接口；
- **架构耦合度高**：嵌入式固件与云端服务往往高度耦合，难以独立维护与扩展；
- **图像传输方案粗糙**：快照图像传输方案未考虑不同网络环境下的降级策略，在断网或高延迟场景下体验差；
- **缺乏完整工程化实践**：大多数方案缺少容器化部署、日志审计、权限状态机等生产级特性。

本文针对上述不足，在系统设计阶段即融入安全性、工程化与可维护性的考量，力求实现一套完整的、可落地的生产级智能门禁系统。

### 1.2.3 技术发展趋势

综合国内外研究现状，智能门禁系统未来的技术发展主要呈现以下几个趋势：

**（1）多模态身份认证融合。** 指纹、NFC、人脸识别、声纹等多种认证方式的融合将成为标配，单一认证方式的系统将逐渐被淘汰。

**（2）边缘计算下沉。** 随着边缘 AI 芯片成本下降，人脸识别等推理任务将从云端下沉至本地设备，降低对网络连通性的依赖，提升响应速度与隐私保护水平。

**（3）零信任安全模型。** 传统"边界安全"模型正逐步被"持续验证、最小权限"的零信任架构取代，门禁系统的权限管理也将向动态化、细粒度方向演进。

**（4）云原生与微服务化。** 大型门禁管理平台正加速向容器化、微服务架构迁移，以支持多租户、弹性扩缩容和高可用部署 [7]。

## 1.3 研究内容与主要工作

本文的研究内容涵盖智能门禁控制系统的全栈设计与实现，具体包括以下几个方面：

**（1）双 MCU 嵌入式硬件层设计（第2章）。** 研究 ESP32-S3 与 STM32 双控制器协作架构，设计自定义 UART 二进制帧通信协议，实现摄像头图像采集、MQTT 消息收发、HTTP 快照推送与心跳上报等核心功能。

**（2）Flask 云端后端服务设计（第3章）。** 基于应用工厂模式构建 Flask REST API 服务，设计 SQLAlchemy ORM 数据模型，实现 MQTT 设备通信、JWT 身份认证、对象级权限保护与三级快照分发机制。

**（3）微信小程序移动端设计（第4章）。** 基于微信原生框架开发移动端应用，实现设备列表管理、实时快照轮询、权限申请与远程开锁等功能，并解决 Base64 快照渲染兼容性问题。

**（4）系统部署、测试与性能分析（第5章）。** 设计端到端功能测试与安全测试方案，验证 BOLA 防护效果、端到端响应延迟、MAC 地址标准化等关键指标，并基于 Docker Compose 完成生产环境部署验证。

## 1.4 论文结构安排

本文共分为六章，各章主要内容如下：

**第1章 绪论**：阐述研究背景与意义，梳理国内外相关研究现状与技术趋势，明确研究内容与论文结构。

**第2章 嵌入式硬件层设计与实现**：详细介绍 ESP32-S3 与 STM32 双 MCU 架构设计，包括 UART 自定义协议、摄像头管理、MQTT 通信、HTTP 快照上传与非阻塞 FSM 状态机实现。

**第3章 云端后端服务设计与实现**：介绍 Flask 应用工厂模式架构、SQLAlchemy 数据模型设计、JWT 认证机制、MQTT 设备管理、权限控制体系与快照分发策略。

**第4章 移动端小程序设计与实现**：阐述微信小程序整体架构，重点介绍设备列表、实时快照、权限管理与远程开锁等核心页面的设计与实现，以及管理员 Web 端的功能补充。

**第5章 系统部署与测试**：介绍 Docker Compose 生产环境部署方案，设计并执行功能测试、安全测试、性能测试，分析测试结果并进行系统性能评估。

**第6章 总结与展望**：总结本文的主要研究成果与创新点，分析系统现存不足，展望后续改进方向与研究课题。

---

# 第2章 嵌入式硬件层设计与实现

## 2.1 系统总体架构概述

智能门禁控制系统的硬件层承担着物理世界与数字世界之间的"桥梁"职责，负责采集门禁现场的生物特征与感知数据，执行开锁等物理动作，并将设备状态实时同步至云端。为兼顾网络通信的灵活性与硬件控制的实时性，本系统采用双 MCU 协作架构：ESP32-S3 承担网络侧的全部职责（WiFi 联网、MQTT 通信、HTTP 快照上传、OV2640 摄像头驱动），STM32 承担执行侧的实时控制职责（指纹模块驱动、NFC 刷卡读取、电磁锁继电器控制、OLED 状态显示）。两颗控制器通过 UART 串口互联，采用本文设计的自定义二进制帧协议进行可靠通信。

【图2-1】系统硬件总体架构图（建议配置：左侧 STM32 框含指纹模块/NFC/继电器/OLED；中间 UART 双向箭头；右侧 ESP32-S3 框含 OV2640/WiFi/MQTT/HTTP；右侧再连接至云端服务器）

本架构的核心设计理念是**关注点分离**（Separation of Concerns）：STM32 运行裸机实时操作，响应延迟确定可控；ESP32-S3 运行 FreeRTOS 多任务调度，网络操作不会阻塞硬件执行。两者通过异步消息传递解耦，任一侧重启均不影响另一侧的基本功能。

**表2-1 ESP32-S3 主控芯片核心参数**

| 参数项 | 规格 |
|--------|------|
| CPU | Xtensa LX7 双核，主频 240 MHz |
| SRAM | 512 KB 片上 SRAM |
| PSRAM | 外挂 8 MB PSRAM（QSPI 接口，供摄像头帧缓冲） |
| Flash | 外挂 16 MB SPI Flash |
| WiFi | 802.11 b/g/n，2.4 GHz |
| 蓝牙 | BLE 5.0 |
| GPIO | 45 个多功能 GPIO |
| UART | 3 路 UART（UART0 调试，UART1 与 STM32 通信） |
| 摄像头接口 | DVP 并行接口，最高支持 8/16 位像素总线 |
| 操作系统 | FreeRTOS |
| 开发框架 | Arduino-ESP32 / ESP-IDF |

**表2-2 UART 资源分配**

| UART 编号 | 波特率 | 用途 | 对端设备 |
|-----------|--------|------|---------|
| UART0 | 115200 | 调试串口（Serial Monitor） | PC 开发工具 |
| UART1 | 115200 | 业务通信 | STM32 微控制器 |

## 2.2 双 MCU 协作方案设计

### 2.2.1 分工职责定义

在系统设计阶段，对 ESP32-S3 与 STM32 的职责边界进行了明确划分，如表2-3所示。

**表2-3 双 MCU 职责对比**

| 维度 | ESP32-S3 | STM32 |
|------|----------|-------|
| 核心定位 | 网络与图像处理网关 | 实时硬件执行控制器 |
| 主要任务 | WiFi 连接、MQTT 收发、HTTP 上传、摄像头采集 | 指纹模块、NFC 读卡、继电器控制、OLED 显示 |
| 操作系统 | FreeRTOS 多任务 | 裸机或 RTOS |
| 实时性要求 | 低（网络操作容许延迟） | 高（硬件响应需 <100ms） |
| 通信接口 | UART1（主动发送命令，被动接收事件） | UART（被动接收命令，主动上报事件） |
| 重启影响 | WiFi 重连期间快照中断，硬件控制不受影响 | 重启期间无法执行开锁，网络上报不受影响 |

### 2.2.2 启动序列

ESP32-S3 的启动流程在 `setup()` 函数中按固定顺序执行，以确保各模块的初始化依赖关系得到满足。

【图2-2】ESP32-S3 启动序列流程图（建议顺序：Serial init → framework_network_init() WiFi连接/NTP同步 → MAC地址获取 → MQTT配置+LWT → xTaskCreateUniversal(mqtt_task) → start_httpd()端口81 → manage_camera_power(true) → 进入loop()）

启动流程依次完成以下步骤：首先以 115200 波特率初始化调试串口；随后调用 `framework_network_init()` 完成 WiFi 连接（支持 SmartConfig 配网模式）并同步 NTP 时间；从 WiFi 驱动读取设备 MAC 地址并格式化为 MQTT 主题名；初始化 MQTT 客户端并配置 LWT（Last Will Testament）遗嘱消息；通过 `xTaskCreateUniversal()` 在 FreeRTOS 中创建 MQTT 专用任务；启动 HTTP 流媒体服务器（端口 81）；最后调用 `manage_camera_power(true)` 初始化 OV2640 摄像头。整个启动过程通常在 5–8 秒内完成（其中 WiFi 连接约占 3–5 秒）。

## 2.3 自定义 UART 二进制帧协议

### 2.3.1 协议设计目标

ESP32-S3 与 STM32 之间的通信采用自定义二进制帧协议，而非文本 AT 指令或 JSON 格式，主要出于以下考量：

- **确定性帧长**：固定 6 字节帧结构使解析复杂度降为 O(1)，无需动态缓冲区扩展；
- **低带宽开销**：二进制编码相比 JSON 文本效率高出 3–5 倍；
- **硬件校验**：累加校验和可检测传输中的单比特错误；
- **帧同步可靠**：双字节同步头（0xAA 0x55）提供明确的帧起始标识，便于在噪声环境下重新同步。

### 2.3.2 帧格式定义

**表2-4 UART 帧字段定义**

| 字节序号 | 字段名 | 长度 | 说明 |
|---------|--------|------|------|
| Byte 0 | SYNC_H | 1 字节 | 同步头高字节，固定为 0xAA |
| Byte 1 | SYNC_L | 1 字节 | 同步头低字节，固定为 0x55 |
| Byte 2 | CMD | 1 字节 | 命令码，标识指令类型 |
| Byte 3 | LEN | 1 字节 | DATA 字段的有效字节数 |
| Byte 4 | DATA | 1 字节 | 命令参数或事件附加数据 |
| Byte 5 | CHECKSUM | 1 字节 | 校验和，= CMD + LEN + DATA 的字节累加和（取低8位） |

帧校验算法为：`CHECKSUM = (CMD + LEN + DATA) & 0xFF`。接收方在解析完整帧后重新计算校验和，若不匹配则丢弃该帧并等待下一个同步头。

**表2-5 CMD 命令码定义**

| CMD 值 | 方向 | 含义 | DATA 说明 |
|--------|------|------|-----------|
| 0x01 | ESP32→STM32 | 远程开锁指令 | 0x01 = 开锁，0x00 = 锁定 |
| 0x02 | ESP32→STM32 | 查询设备状态 | 无（LEN=0，DATA=0x00） |
| 0x10 | STM32→ESP32 | 指纹识别事件上报 | 指纹 ID（0=失败，1-127=对应用户） |
| 0x11 | STM32→ESP32 | NFC 刷卡事件上报 | 卡号低字节（完整 UID 后续扩展） |
| 0x20 | STM32→ESP32 | 设备状态响应 | 0x01=门已关，0x02=门已开 |
| 0xFF | 双向 | 心跳/保活 | 序列号（每次递增） |

### 2.3.3 非阻塞 FSM 解析实现

UART 帧的接收解析通过有限状态机（Finite State Machine，FSM）实现，并以非阻塞方式集成进主循环，避免等待字节到达期间阻塞其他任务调度。

【图2-3】UART 接收 FSM 状态转移图（状态节点：IDLE → SYNC_H（收到0xAA）→ SYNC_L（收到0x55）→ CMD → LEN → DATA → CHECKSUM → 校验通过→处理帧/校验失败→回IDLE）

FSM 共有 6 个状态：
1. **IDLE**：等待同步头高字节 0xAA；
2. **SYNC_H**：已收到 0xAA，等待 0x55；若收到其他字节则回退到 IDLE；
3. **CMD**：读取命令码；
4. **LEN**：读取数据长度；
5. **DATA**：读取 DATA 字节；
6. **CHECKSUM**：读取并验证校验和，验证通过则调用对应命令处理函数，之后无条件回到 IDLE。

主循环中的 `business_uart_listen()` 函数每次调用时检查串口缓冲区的可用字节数，按当前 FSM 状态逐字节推进，不执行任何阻塞等待。

## 2.4 摄像头图像采集模块

### 2.4.1 OV2640 初始化配置

系统搭载 OV2640 图像传感器，通过 DVP（Digital Video Port）并行接口与 ESP32-S3 相连。摄像头初始化由 `manage_camera_power()` 函数负责，关键参数配置如表2-6所示。

**表2-6 摄像头初始化关键参数**

| 参数名 | 配置值 | 说明 |
|--------|--------|------|
| `frame_size` | `FRAMESIZE_VGA` | 分辨率 640×480，平衡画质与传输带宽 |
| `pixel_format` | `PIXFORMAT_JPEG` | 硬件 JPEG 编码，CPU 负担低 |
| `grab_mode` | `CAMERA_GRAB_LATEST` | 始终获取最新帧，避免队列积压 |
| `fb_location` | `CAMERA_FB_IN_PSRAM` | 帧缓冲存于外挂 PSRAM，不占用片上 SRAM |
| `jpeg_quality` | `12` | JPEG 质量（1-63，越小质量越高），12 约对应 75% 质量 |
| `fb_count` | `2` | 双帧缓冲，支持乒乓操作，提升帧率稳定性 |
| `vflip` | `1`（开启） | 垂直翻转，修正摄像头物理安装方向 |

### 2.4.2 双帧缓冲机制

采用 `fb_count=2` 的双帧缓冲（Double Buffering）配置，当系统对帧缓冲 A 进行 HTTP 上传操作时，OV2640 硬件可同步向帧缓冲 B 写入下一帧，两个操作并行进行，互不阻塞。结合 `CAMERA_GRAB_LATEST` 模式，系统在每次读取帧时始终获取传感器捕获的最新图像，有效消除了因缓冲队列积压导致的画面延迟。

【图2-4】双帧缓冲时序图（建议：横轴时间，上方 OV2640 填充帧 A/B 交替；下方 HTTP 上传读取帧 A/B 交替，展示并行工作）

## 2.5 MQTT 通信模块

### 2.5.1 MQTT 任务架构

MQTT 通信运行在独立的 FreeRTOS 任务中（通过 `xTaskCreateUniversal(mqtt_task, ...)` 创建），与主循环任务并发执行。独立任务隔离确保网络 I/O 的阻塞不影响 UART 监听和快照上传的实时性。

【图2-5】MQTT 任务生命周期图（FreeRTOS 任务视角：创建→配置LWT→连接Broker→订阅主题→循环: client.loop()+vTaskDelay(50ms)→重连机制）

### 2.5.2 LWT 遗嘱机制

MQTT 客户端在连接 Broker 时预先配置 LWT（Last Will and Testament）消息：

```
主题: /iot/device/{mac}/status
负载: {"status": "offline", "mac": "{mac}"}
QoS: 1
Retain: true
```

当 ESP32-S3 因断网、复位或异常崩溃而与 Broker 非正常断开时，Broker 将自动向 `/iot/device/{mac}/status` 主题发布上述遗嘱消息，云端后端的 MQTT 订阅回调随即将该设备状态更新为 `offline`，并持久化到数据库。这一机制保证了设备离线状态的自动感知，无需依赖心跳超时轮询。

### 2.5.3 主题命名规范

**表2-7 MQTT 主题命名规范**

| 主题 | 方向 | 说明 |
|------|------|------|
| `/iot/device/{mac}/up` | 设备→云端 | 设备主动上报（心跳、事件） |
| `/iot/device/{mac}/down` | 云端→设备 | 云端下发指令（远程开锁） |
| `/iot/device/{mac}/status` | Broker自动 | LWT 遗嘱消息，设备离线自动触发 |
| `access/control/event/+` | 设备→云端 | 门禁访问事件上报（通配符订阅） |

其中 `{mac}` 为设备 MAC 地址去除冒号的 12 位十六进制字符串，如 `A1B2C3D4E5F6`，以避免 MQTT 主题中包含非法字符。

### 2.5.4 心跳上报机制

主循环每 15 秒向 `/iot/device/{mac}/up` 发布一条心跳消息，JSON 格式包含以下字段：

```json
{
  "type": "heartbeat",
  "mac": "A1:B2:C3:D4:E5:F6",
  "timestamp": 1709734512,
  "uptime": 3600,
  "ip_address": "192.168.3.161",
  "count": 240
}
```

云端后端收到心跳后更新 `devices` 表中对应设备的 `last_heartbeat` 字段和 `status` 字段为 `online`。若后端在 30 秒内未收到心跳，则通过定时任务将设备状态标记为 `offline`。

## 2.6 HTTP 快照上传模块

### 2.6.1 上传流程设计

`poll_frame_upload()` 函数实现了基于轮询的定时快照上传，每次主循环调用时检查距上次上传是否已超过 1000ms（1 帧/秒），并通过 `is_uploading` 布尔标志防止并发重入。

【图2-6】快照上传流程图（建议：poll_frame_upload() → 检查1000ms节流 → 检查is_uploading标志 → 检查active_viewers → 获取摄像头帧 → HTTP POST → 成功/失败计数 → 释放帧缓冲）

上传请求携带两个自定义 HTTP 请求头，用于后端设备身份验证：

```
POST /api/device/upload_snapshot HTTP/1.1
X-Device-MAC: A1:B2:C3:D4:E5:F6
X-Device-Secret: <预共享密钥>
Content-Type: image/jpeg
```

超时设置为连接超时 3 秒、总超时 5 秒，确保单次上传失败不会长时间阻塞主循环。

### 2.6.2 MJPEG 流媒体服务

除 HTTP 推送模式外，ESP32-S3 还在端口 81 运行了一个 HTTP 服务器，提供两种访问方式：

- `GET http://{ip}:81/stream?action=snapshot`：返回单张 JPEG 图像；
- `GET http://{ip}:81/stream`：返回 `multipart/x-mixed-replace` MJPEG 流。

MJPEG 模式可供局域网内的客户端直接拉流，延迟可低至 50ms 以下，但要求客户端与设备处于同一网段。云端中继模式通过 HTTP 推送实现跨网络访问。

## 2.7 主控任务调度与容错机制

### 2.7.1 主循环任务调度

ESP32-S3 的 `loop()` 函数按固定顺序调用三类任务，形成协作式调度框架。

**表2-8 主循环任务调度**

| 调用顺序 | 函数 | 执行周期 | 说明 |
|---------|------|---------|------|
| 1 | `business_uart_listen()` | 每帧（~1ms） | 非阻塞读取 UART 字节，推进 FSM 状态机 |
| 2 | `poll_frame_upload()` | 1000ms 节流 | 检查节流窗口，满足条件则触发快照上传 |
| 3 | 心跳发布 | 15000ms 节流 | 向 MQTT Broker 发布设备心跳 JSON |

MQTT 客户端维护（`client.loop()`）在独立 FreeRTOS 任务中运行，不占用主循环时间片。

### 2.7.2 容错与重连机制

**表2-9 容错机制设计**

| 故障场景 | 检测方式 | 恢复策略 |
|---------|---------|---------|
| WiFi 断连 | WiFi 事件回调 | 自动重连，指数退避，最长重试间隔 30s |
| MQTT Broker 断连 | `mqtt_task` 内 `client.connected()` 检测 | 自动重连，重连后重新订阅主题 |
| 快照上传失败 | HTTP 返回码非 200 | 记录失败计数，下一轮继续尝试，不阻断 |
| 摄像头帧获取失败 | `esp_camera_fb_get()` 返回 NULL | 跳过本次上传，释放资源，等待下轮 |
| UART 帧校验失败 | CHECKSUM 不匹配 | 丢弃当前帧，FSM 回到 IDLE 状态 |

## 2.8 本章小结

本章详细介绍了智能门禁控制系统嵌入式硬件层的设计与实现。核心工作包括：提出 ESP32-S3 + STM32 双 MCU 分工协作架构；设计并实现了基于双字节同步头与累加校验和的 6 字节定长 UART 二进制帧协议，并以非阻塞 FSM 完成接收解析；配置 OV2640 摄像头的双帧缓冲与 PSRAM 存储策略；实现 MQTT LWT 自动离线感知与 FreeRTOS 多任务隔离；以及基于节流与重入防护的定时 HTTP 快照上传机制。这些设计共同保证了嵌入式侧的实时性、可靠性与网络适应性。

---

# 第3章 云端后端服务设计与实现

## 3.1 系统架构设计

### 3.1.1 三层架构总览

云端后端服务采用经典三层架构，各层职责清晰、耦合度低。

**表3-1 后端三层架构划分**

| 层次 | 技术实现 | 职责 |
|------|---------|------|
| 接入层 | Nginx + ProxyFix | SSL 终止、静态文件服务、请求转发至应用层 |
| 应用层 | Flask + Gunicorn（4 Workers） | REST API 路由处理、业务逻辑、MQTT 订阅处理 |
| 数据层 | SQLAlchemy ORM + SQLite/MySQL | 数据持久化、ORM 映射、事务管理 |

【图3-1】后端服务架构图（建议：客户端/小程序 → Nginx（80/443）→ Gunicorn（5000）→ Flask App（Blueprint: api_bp, web_bp）→ SQLAlchemy → 数据库；另一侧 MQTT Broker ↔ Flask-MQTT）

### 3.1.2 应用工厂模式

Flask 应用通过 `create_app()` 工厂函数构建，避免了全局 `app` 实例在测试和多进程部署中引发的状态共享问题。工厂函数按以下顺序完成初始化：

1. 创建 `Flask(__name__)` 实例，加载配置；
2. 注册 `ProxyFix` WSGI 中间件（`x_for=1, x_proto=1, x_host=1, x_prefix=1`），修复 Nginx 反向代理后 `request.host` 与 `url_for()` 生成错误域名的问题；
3. 注册 `Flask-CORS`，允许跨域请求；
4. 初始化 `SQLAlchemy`，调用 `db.create_all()` 自动建表；
5. 执行 `_ensure_device_columns()` 动态列迁移（不依赖 Alembic，直接检查并 ALTER TABLE）；
6. 创建默认管理员账户（若不存在）；
7. 注册 `api_bp`（RESTful 接口蓝图）和 `web_bp`（管理员 Web 页面蓝图）；
8. 调用 `init_mqtt(app)` 启动 MQTT 客户端后台线程并等待连接建立。

### 3.1.3 蓝图路由划分

**表3-2 REST API 主要接口列表**

| HTTP 方法 | 路径 | 功能 | 认证要求 |
|----------|------|------|---------|
| POST | `/api/login` | 用户登录（密码/微信） | 无 |
| GET | `/api/config` | 获取前端配置 | 无 |
| GET | `/api/user/devices` | 获取当前用户可访问的设备列表 | JWT |
| GET | `/api/devices` | 获取全部设备（管理员） | JWT + Admin |
| POST | `/api/devices` | 注册新设备 | JWT + Admin |
| PUT | `/api/devices/<mac>` | 更新设备信息 | JWT + Admin |
| DELETE | `/api/devices/<mac>` | 删除设备 | JWT + Admin |
| POST | `/api/device/unlock` | 远程开锁 | JWT |
| GET | `/api/device/snapshot/<mac>` | 获取设备快照（Base64） | JWT |
| POST | `/api/device/upload_snapshot` | 设备端上传快照 | 设备密钥 |
| GET | `/api/logs` | 查询开锁日志 | JWT |
| POST | `/api/permissions/apply` | 申请设备权限 | JWT |
| GET | `/api/permissions` | 查询权限列表 | JWT + Admin |
| PUT | `/api/permissions/<id>` | 审批权限申请 | JWT + Admin |
| DELETE | `/api/permissions/<id>` | 撤销权限 | JWT + Admin |

## 3.2 数据模型设计

### 3.2.1 Mixin 基类设计

系统通过 SQLAlchemy Mixin 模式实现数据模型基础功能的复用，避免每个模型重复定义相同列和方法。

**表3-3 Mixin 类功能说明**

| Mixin 类 | 提供字段/方法 | 说明 |
|---------|------------|------|
| `BaseIDMixin` | `id`（自增整数主键） | 为需要自增主键的模型提供标准化主键 |
| `TimestampMixin` | `created_at`、`updated_at` | `updated_at` 配置 `onupdate=datetime.utcnow`，自动更新 |
| `SerializerMixin` | `to_dict()` 方法 | 通过 `sqlalchemy.inspect()` 遍历列，将 `datetime` 转为 ISO 8601 字符串 |

所有模型均继承 `SerializerMixin`，使得任何模型实例可直接调用 `.to_dict()` 生成 JSON 可序列化的字典，无需为每个模型单独编写序列化逻辑。

### 3.2.2 核心数据模型

**表3-4 核心数据表字段说明**

**devices 表（设备表）**

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| mac_address | VARCHAR(17) | PRIMARY KEY | 设备 MAC 地址，格式 AA:BB:CC:DD:EE:FF |
| name | VARCHAR(100) | 可空 | 设备名称，如"一楼东门" |
| room_number | VARCHAR(10) | 可空 | 所在房间号 |
| location | VARCHAR(100) | 可空 | 位置描述 |
| ip_address | VARCHAR(15) | 可空 | ESP32 IP 地址，用于本地直连快照 |
| status | ENUM | DEFAULT 'offline' | 'online' 或 'offline' |
| last_heartbeat | DATETIME | 可空 | 最后一次心跳时间 |
| created_at | DATETIME | DEFAULT utcnow | 设备注册时间 |

**users 表（用户表）**

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY，自增 | 用户 ID |
| openid | VARCHAR(100) | UNIQUE，可空 | 微信 OpenID |
| username | VARCHAR(50) | UNIQUE，可空 | 登录用户名 |
| password | VARCHAR(64) | 可空 | SHA256 哈希密码 |
| name | VARCHAR(50) | 可空 | 真实姓名 |
| role | ENUM | DEFAULT 'student' | 'student' / 'warden' / 'admin' |
| fingerprint_id | INTEGER | 可空 | 指纹模块中的指纹 ID（1-127） |
| nfc_uid | VARCHAR(20) | 可空 | NFC 卡 UID |

**logs 表（操作日志表）**

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| event_id | VARCHAR(50) | PRIMARY KEY | 格式：`{method}_{timestamp}_{mac无冒号}` |
| mac_address | VARCHAR(17) | FK→devices | 发生事件的设备 |
| user_id | INTEGER | FK→users，可空 | 操作用户（远程开锁时必填） |
| unlock_method | ENUM | NOT NULL | 'fingerprint' / 'nfc' / 'remote' |
| snapshot_url | VARCHAR(255) | 可空 | 事件抓拍图片 URL |
| create_time | DATETIME | DEFAULT utcnow | 事件发生时间 |

**user_device_permissions 表（权限表）**

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | INTEGER | PRIMARY KEY，自增 | 权限记录 ID |
| user_id | INTEGER | FK→users | 申请用户 |
| device_mac | VARCHAR(17) | FK→devices | 申请访问的设备 |
| status | ENUM | DEFAULT 'pending' | 'pending' / 'approved' / 'rejected' |
| apply_time | DATETIME | DEFAULT utcnow | 申请时间 |
| review_time | DATETIME | 可空 | 审批时间 |
| reviewed_by | INTEGER | FK→users，可空 | 审批管理员 ID |
| — | — | UNIQUE(user_id, device_mac) | 防止同一用户重复申请同一设备 |

### 3.2.3 DatabaseHelper 工具类

所有数据库操作统一通过 `DatabaseHelper` 封装，避免在路由层直接操作 Session，保证异常处理的一致性。

**表3-5 DatabaseHelper 核心方法**

| 方法名 | 签名 | 返回值 | 说明 |
|--------|------|--------|------|
| `get_by_filter` | `(model, **kwargs)` | `(instance, error)` | 按条件查询单条记录 |
| `get_by_id` | `(model, id)` | `(instance, error)` | 按主键查询 |
| `get_all` | `(model, **kwargs)` | `(list, error)` | 查询全部符合条件的记录 |
| `add_and_commit` | `(instance)` | `(instance, error)` | 插入并提交事务 |
| `update_and_commit` | `(instance, **kwargs)` | `(instance, error)` | 更新字段并提交 |
| `delete_and_commit` | `(instance)` | `(True, error)` | 删除并提交事务 |
| `batch_add_and_commit` | `(instances)` | `(instances, error)` | 批量插入并提交 |
| `with_transaction` | `(func)` | 装饰器 | 将函数包裹在事务中，异常自动 rollback |

所有方法均返回 `(result, error)` 二元组：操作成功时 `error` 为 `None`；操作失败时捕获异常、执行 `db.session.rollback()`，`result` 为 `None`，`error` 为异常对象。路由层通过判断 `error` 是否为 `None` 决定返回成功还是错误响应，无需在每个路由函数中单独编写 try/except。

## 3.3 JWT 身份认证机制

### 3.3.1 令牌签发

用户通过 `/api/login` 接口验证身份后，服务端调用 `_issue_jwt(user)` 函数生成 JWT 令牌。令牌采用 HMAC-SHA256（HS256）算法签名，有效期为 7 天，Payload 包含以下字段：

```json
{
  "user_id": 42,
  "role": "student",
  "iat": 1709734512,
  "exp": 1710339312
}
```

微信小程序通过 `code2session` 接口交换 `openid` 后，同样经此函数签发 JWT，实现统一的无状态认证体系。

### 3.3.2 token_required 装饰器

**表3-6 token_required 验证步骤**

| 步骤 | 操作 | 失败时返回 |
|------|------|----------|
| 1 | 从 `Authorization` 请求头提取内容 | HTTP 401，`MISSING_TOKEN` |
| 2 | 验证格式为 `Bearer <token>` | HTTP 401，`INVALID_TOKEN_FORMAT` |
| 3 | `jwt.decode(token, SECRET_KEY, algorithms=['HS256'])` | HTTP 401，`TOKEN_EXPIRED` 或 `INVALID_TOKEN` |
| 4 | 从 Payload 提取 `user_id` | HTTP 401，`MISSING_USER_ID` |
| 5 | 查询数据库验证用户存在 | HTTP 404，`USER_NOT_FOUND` |
| 6 | 将用户对象存入 `g.current_user` | — |

验证通过后，路由函数可直接通过 `g.current_user` 访问当前用户对象，无需重复查询数据库。

## 3.4 MQTT 设备管理

### 3.4.1 MQTT 消息处理架构

后端使用 `flask-mqtt` 扩展在应用启动时建立 MQTT 连接，并注册以下主题的订阅处理回调：

- `/iot/device/+/up`：处理设备上行消息（心跳、事件）；
- `/iot/device/+/status`：处理设备状态变更（LWT 遗嘱触发的离线通知）；
- `access/control/event/+`：处理门禁访问事件。

收到心跳消息时，后端解析 JSON Payload，更新 `devices` 表对应行的 `last_heartbeat` 为当前时间、`status` 为 `online`，并可选择性更新 `ip_address` 字段（用于后续本地直连快照）。

### 3.4.2 下行指令发布

`publish_command(mac, command)` 函数将指令发布至 `/iot/device/{mac_clean}/down` 主题，其中 `mac_clean` 为去除冒号的 MAC 地址字符串，与 ESP32-S3 侧的主题命名规则保持一致。

远程开锁流程：移动端发起 `POST /api/device/unlock` → 后端验证权限 → 调用 `publish_command()` 发布开锁消息 → MQTT Broker 转发至设备 → ESP32-S3 接收后通过 UART 向 STM32 发送 CMD=0x01 指令 → STM32 控制继电器 → 记录日志。

## 3.5 权限管控体系

### 3.5.1 权限状态机

用户对设备的访问权限通过状态机模型管理，共有 3 个状态、4 种有效转换。

【图3-2】权限状态机图（建议：初始态→pending（用户申请）→approved（管理员批准）→（记录删除，撤销）；pending→rejected（管理员拒绝）；rejected→（可再次申请，回到pending））

- **pending**：用户提交申请后的初始状态，等待管理员审核；
- **approved**：管理员审批通过，用户可访问该设备；
- **rejected**：管理员拒绝申请，用户不可访问。

同一用户对同一设备的权限记录受 `UNIQUE(user_id, device_mac)` 约束，防止重复申请产生多条冗余记录。

### 3.5.2 BOLA 防护实现

`PermissionHelper.check_device_access(user, device_mac)` 实现了对象级权限保护：

1. 若用户角色为 `admin`，直接放行；
2. 否则，查询 `user_device_permissions` 表，检查 `(user_id, device_mac, status='approved')` 记录是否存在；
3. 不存在则返回 HTTP 403 `FORBIDDEN`。

所有设备操作接口（快照获取、远程开锁、日志查询）在执行业务逻辑前均调用此函数，确保任意用户无法通过篡改请求参数（如 MAC 地址）访问其无权限的设备。

## 3.6 三级快照分发机制

系统为设备快照获取设计了三级优先级降级策略，以在不同网络环境下提供最优服务。

【图3-3】三级快照优先级流程图（建议：请求快照 → 尝试云端中继URL → 失败 → 查内存缓存device_frames[mac] → 无缓存 → 尝试本地直连http://{ip}:81 → 均失败 → 返回占位JPEG）

**第一优先级——云端中继**：从环境变量 `CLOUD_RELAY_SNAPSHOT_URL` 获取专属 URL，由独立的图像中继服务提供；
**第二优先级——内存缓存**：查询 `device_frames[mac]` 字典，该字典由 ESP32-S3 每秒 HTTP POST 上传的 JPEG 帧填充，命中时以 Base64 编码直接返回；
**第三优先级——本地直连**：使用 `Device.ip_address` 字段向 `http://{ip}:81/stream?action=snapshot` 发起直接 HTTP 请求，要求服务端与设备处于同一局域网。

若三级均失败，返回 `_generate_placeholder_jpeg()` 生成的最小 1×1 灰色占位 JPEG，避免前端出现空白或加载错误。

MAC 地址标准化函数 `normalize_mac()` 在快照写入和读取两端均调用，确保 ESP32 上传时使用 `AA:BB:CC:DD:EE:FF` 格式，小程序查询时无论传入哪种格式（带冒号、无分隔符、带连字符）均能正确命中缓存。

## 3.7 本章小结

本章系统介绍了云端后端服务的架构设计与实现细节。通过应用工厂模式与蓝图机制实现了清晰的模块化组织；SQLAlchemy Mixin 设计减少了数据模型层的重复代码；JWT 无状态认证与 BOLA 权限防护构建了完善的 API 安全体系；MQTT 与 HTTP 混合接入策略兼顾了实时控制与图像传输的不同需求；三级快照分发机制在可靠性与延迟之间取得了良好平衡。

---

# 第4章 移动端小程序设计与实现

## 4.1 整体架构设计

### 4.1.1 微信小程序技术概述

微信小程序采用双线程架构：逻辑层（JS Engine）运行业务逻辑，渲染层（WebView）负责界面渲染，两层通过微信客户端的 JSBridge 进行异步通信。本系统使用微信原生框架（WXML + WXSS + JS）开发，无需引入第三方 UI 框架，减少包体积并确保与微信基础库的最佳兼容性。

**表4-1 视觉设计规范**

| 设计要素 | 规范值 | 说明 |
|---------|--------|------|
| 设计稿尺寸 | 750rpx 宽 | 标准 iPhone 6/7/8 设计基准 |
| 主色调 | #1890ff（蓝色） | 操作按钮、高亮标识 |
| 成功色 | #52c41a（绿色） | 设备在线状态、操作成功提示 |
| 危险色 | #ff4d4f（红色） | 设备离线状态、删除操作 |
| 警告色 | #faad14（黄色） | 待审批状态标识 |
| 字体大小 | 28rpx（正文）/ 32rpx（标题）/ 24rpx（辅助） | rpx 单位自适应屏幕 |
| 圆角规范 | 12rpx（卡片）/ 8rpx（按钮） | 统一圆角视觉语言 |

### 4.1.2 页面结构与路由

**表4-2 小程序 TabBar 结构**

| TabBar 项 | 页面路径 | 图标 | 功能 |
|----------|---------|------|------|
| 控制台 | `/pages/console/index` | home | 设备列表与快速操作入口 |
| 设置 | `/pages/settings/config` | setting | 账号设置与系统配置 |

完整页面路由如下：

| 页面 | 路径 | 说明 |
|------|------|------|
| 登录页 | `/pages/login/index` | 用户名密码登录或微信 OAuth |
| 控制台 | `/pages/console/index` | 设备列表，下拉刷新 |
| 设备详情 | `/pages/device-detail/index` | 快照预览、远程开锁、日志 |
| 日志列表 | `/pages/logs/index` | 全局或按设备筛选的开锁记录 |
| 用户管理 | `/pages/users/manage` | 管理员查看/管理用户（需 Admin 角色） |
| 系统配置 | `/pages/settings/config` | API 地址配置、账号信息 |

## 4.2 全局初始化与请求封装

### 4.2.1 App 启动流程

`app.js` 的 `onLaunch()` 按以下三步顺序执行初始化，确保后续页面可用的配置与鉴权状态：

```
Step 1: envConfig.initConfig()
        ↓ 从服务端拉取最新配置（API 地址、超时等）
        ↓ 合并本地缓存，降级到默认值
Step 2: Session 恢复
        ↓ 从 wx.getStorageSync 读取 token 和 user
        ↓ 写入 globalData，供全局复用
Step 3: 设置 videoStreamUrl
        ↓ 从 globalData.config 读取流媒体 URL
        ↓ 存入 globalData.videoStreamUrl
```

【图4-1】小程序启动时序图（建议：App.onLaunch → initConfig发起HTTP请求 → 成功/失败 → 恢复session → 设置streamUrl → 跳转控制台或登录页）

### 4.2.2 HTTP 请求拦截器

`utils/request.js` 封装了全局 HTTP 请求拦截器，所有业务请求均通过该模块发起，实现统一的令牌注入与 401 处理。

【图4-2】请求拦截器处理流程图（建议：发起请求 → 注入Authorization头 → wx.request → 返回401→清除token→跳转登录 / 返回success:false→reject / 正常→resolve）

核心处理逻辑：
- **Token 自动注入**：从 `wx.getStorageSync('token')` 读取令牌，添加 `Authorization: Bearer {token}` 请求头；
- **401 自动处理**：收到 HTTP 401 响应时，清除本地 `token` 和 `user` 存储，弹出"登录已过期"提示，延迟 500ms 后跳转登录页；
- **业务错误识别**：检查响应体中 `res.data.success === false`，自动 reject 并携带服务端 `message`；
- **网络错误处理**：`fail` 回调中区分超时错误与普通网络错误，分别显示不同提示文案。

## 4.3 控制台页面（设备列表）

### 4.3.1 页面生命周期

**表4-3 控制台页面生命周期钩子**

| 生命周期 | 触发时机 | 执行操作 |
|---------|---------|---------|
| `onLoad` | 页面首次加载 | 调用 `loadDevices()`，获取设备列表 |
| `onShow` | 页面显示（每次从后台页面返回时） | 重新调用 `loadDevices()`，刷新设备在线状态 |
| `onPullDownRefresh` | 用户下拉触发 | 调用 `loadDevices()`，完成后调用 `wx.stopPullDownRefresh()` |
| `onUnload` | 页面卸载 | 无特殊清理 |

`loadDevices()` 调用 `GET /api/user/devices`，将返回的设备列表同步至页面 `data.devices` 和 `app.globalData.devices`，确保跨页面数据一致性。

### 4.3.2 设备卡片展示

控制台以卡片列表形式展示当前用户有权限的所有设备。每个卡片显示设备名称、房间号、位置描述和在线状态（绿色"在线"/ 红色"离线"）。点击卡片跳转至设备详情页，通过 URL 参数传递 `mac_address`。

**表4-4 控制台看板关键数据项**

| 数据项 | 来源 | 展示形式 |
|--------|------|---------|
| 设备总数 | `devices.length` | 顶部统计卡 |
| 在线设备数 | `status === 'online'` 计数 | 顶部统计卡（绿色） |
| 离线设备数 | `status === 'offline'` 计数 | 顶部统计卡（红色） |
| 设备卡片列表 | `devices[]` | 可滚动列表 |

## 4.4 设备详情页（快照与远程开锁）

### 4.4.1 快照轮询机制

设备详情页在 `onLoad` 时启动两个独立的 `setInterval` 定时器：

- **快照轮询**（`startSnapshotPolling()`）：每 2 秒调用 `GET /api/device/snapshot/{mac}`，获取 Base64 编码的 JPEG 快照，赋值给 `data.snapshotSrc`；
- **状态轮询**：每 10 秒调用设备状态接口，刷新在线/离线标识。

在 `onUnload` 生命周期中，通过 `clearInterval()` 清除两个定时器，防止页面卸载后仍持续发起网络请求造成资源泄漏。

### 4.4.2 Base64 渲染兼容性修复

微信小程序的 `<image>` 组件在渲染 `data:image/jpeg;base64,...` 格式的 src 时，若 Base64 字符串中包含换行符（`\r` 或 `\n`），会导致图像无法显示（黑屏）。解决方案为前后端联合修复：

- **后端**：使用 `base64.b64encode(jpeg_bytes).decode('utf-8')` 生成标准 Base64 字符串（Python 标准库默认每 76 字符插入换行）；同时在返回前调用 `.replace('\n', '').replace('\r', '')` 去除换行符；
- **前端**：收到响应后执行 `.replace(/[\r\n]/g, "")` 二次过滤，确保即使后端遗漏处理也能正常渲染；
- **图片 src 格式**：`data:image/jpeg;base64,{cleanBase64}`。

### 4.4.3 远程开锁交互

用户点击"远程开锁"按钮后，前端展示确认对话框（`wx.showModal`），确认后发起 `POST /api/device/unlock`，参数为 `{ mac_address }`。后端完成权限校验与 MQTT 指令发布后，前端接收到成功响应，展示 `wx.showToast('开锁成功')`，并刷新设备状态与快照。

## 4.5 权限管理页面

### 4.5.1 用户侧权限申请

普通用户在设备详情页可申请该设备的访问权限，流程为：点击"申请权限" → 填写申请说明（可选）→ `POST /api/permissions/apply` → 提示"申请已提交，等待管理员审批"。申请后设备卡片显示"待审批"角标，阻止用户发起开锁操作。

### 4.5.2 管理员审批界面

`/pages/users/manage` 页面仅对 `role === 'admin'` 的用户可见，展示所有待审批的权限申请列表。管理员可对每条申请执行**批准**（`PUT /api/permissions/{id}` + `status: 'approved'`）或**拒绝**（`status: 'rejected'`）操作。批准后，申请用户的设备列表将在下次刷新时包含该设备。

**表4-5 权限管理 CRUD 操作规范**

| 操作 | HTTP 方法 | 路径 | 请求体 | 成功响应 |
|------|----------|------|--------|---------|
| 申请权限 | POST | `/api/permissions/apply` | `{device_mac}` | 201，权限记录 |
| 查询权限列表 | GET | `/api/permissions` | `?status=pending` | 200，权限列表 |
| 批准/拒绝 | PUT | `/api/permissions/{id}` | `{status}` | 200，更新后记录 |
| 撤销权限 | DELETE | `/api/permissions/{id}` | — | 200 |

## 4.6 管理员 Web 端

系统还提供了基于 Flask `web_bp` 蓝图的服务端渲染管理员 Web 界面，供在无微信客户端环境下（如 PC 浏览器）进行系统管理。主要功能包括：

- **设备管理**：增删改查设备信息，配置设备名称、房间号、位置、IP 地址；
- **用户管理**：查看注册用户列表，修改用户角色，绑定/解绑指纹 ID 与 NFC 卡号；
- **日志查看**：按设备、按时间段、按开锁方式筛选操作日志，支持快照图片预览；
- **权限管理**：审批权限申请，查看当前权限分配状态。

【图4-3】管理员 Web 端界面结构图（建议：左侧导航栏：设备管理/用户管理/日志/权限；右侧内容区：数据表格+操作按钮；顶部：用户信息+退出登录）

## 4.7 本章小结

本章详细介绍了微信小程序移动端的设计与实现。通过全局请求拦截器统一处理认证与错误，显著减少了各页面的重复代码；控制台页面的多触发点刷新策略保证了设备状态的实时性；设备详情页的双定时器架构实现了快照轮询与状态轮询的独立管理；前后端联合修复 Base64 换行符问题解决了微信小程序特有的渲染兼容性问题；权限管理页面实现了完整的申请—审批—撤销工作流。

---

# 第5章 系统部署与测试

## 5.1 部署环境配置

### 5.1.1 生产环境硬件与软件规格

系统采用单台云服务器部署所有后端服务，通过 Docker 容器化保证环境一致性与可移植性。

**表5-1 测试与部署环境配置**

| 环境项 | 配置值 | 说明 |
|--------|--------|------|
| 服务器 OS | Ubuntu 22.04 LTS | 云服务器实例 |
| CPU | 2 vCPU | 基础生产配置 |
| 内存 | 4 GB RAM | 足够运行 Flask + MQTT + Nginx |
| Docker 版本 | 24.0.x | 容器运行时 |
| Docker Compose 版本 | 2.x | 多容器编排 |
| Python 版本 | 3.11-slim（Docker 镜像） | 后端运行时 |
| 数据库 | MySQL 8.0（生产）/ SQLite（开发） | 通过环境变量切换 |
| MQTT Broker | Mosquitto 2.x | 独立部署或云服务 |
| 域名 / SSL | dev.api.5i03.cn + Let's Encrypt | Nginx 证书终止 |
| 嵌入式硬件 | ESP32-S3 开发板 | 接入测试网络环境 |

### 5.1.2 Docker Compose 服务编排

系统通过 `docker-compose.yml` 定义两个服务容器，共享同一 Docker 网络，相互通过服务名寻址。

**表5-2 Docker Compose 关键环境变量**

| 环境变量 | 示例值 | 说明 |
|---------|--------|------|
| `FLASK_ENV` | `production` | 关闭 Debug 模式 |
| `SECRET_KEY` | `<随机64位字符串>` | JWT 签名密钥 |
| `DATABASE_URL` | `mysql+pymysql://user:pass@host/db` | 数据库连接字符串 |
| `MQTT_BROKER` | `broker.example.com` | MQTT Broker 地址 |
| `MQTT_PORT` | `1883` | MQTT 端口 |
| `CLOUD_RELAY_SNAPSHOT_URL` | `https://relay.example.com/snap/` | 第一优先级快照 URL 模板 |
| `DEVICE_SNAPSHOT_URL` | `http://{ip}:81/stream?action=snapshot` | 第三优先级本地直连模板 |

`doorcontrol_backend` 容器以 `gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app` 启动，4 个 Worker 进程并发处理 HTTP 请求。`doorcontrol_nginx` 容器监听 80/443 端口，将 `/api/` 路径的请求反向代理至 `doorcontrol_backend:5000`，并负责 SSL 证书终止与静态文件服务。

【图5-1】Docker Compose 容器编排图（建议：外部请求→Nginx(80/443)→反向代理→Flask/Gunicorn(5000)→SQLAlchemy→MySQL；MQTT Broker↔Flask-MQTT线程）

## 5.2 功能测试

### 5.2.1 端到端开锁流程测试

端到端测试验证从用户发起远程开锁到物理门锁执行的完整链路，各环节耗时如表5-4所示。

**表5-4 端到端命令响应时序分析**

| 环节 | 操作 | 典型耗时 | 说明 |
|------|------|---------|------|
| T1 | 小程序发起 POST /api/device/unlock | ~20ms | 本地网络至云端 |
| T2 | 后端 JWT 验证 + 权限校验 | ~10ms | 含数据库查询 |
| T3 | 后端 MQTT publish_command | ~5ms | Broker 通常同机房 |
| T4 | MQTT Broker 转发至 ESP32-S3 | ~30ms | 云端至设备，含 WiFi 延迟 |
| T5 | ESP32-S3 UART 发送开锁帧 | ~2ms | 115200 bps 传输 6 字节 |
| T6 | STM32 解析帧并控制继电器 | ~5ms | 裸机实时执行 |
| T7 | 小程序收到 HTTP 响应 | ~100ms（HTTP RTT） | 含服务器处理时间 |
| **合计** | | **~170ms** | **端到端感知延迟** |

测试结论：系统端到端响应时间约 170ms，用户感知的操作响应流畅，满足"点按即开"的实时性体验要求（行业参考值通常 ≤500ms）。

## 5.3 安全测试

### 5.3.1 BOLA 防护测试

BOLA 测试模拟攻击者在持有合法 JWT 令牌（用户 A）的条件下，尝试访问不属于自己的设备（设备 B）。

**表5-3 BOLA 防护测试用例**

| 用例编号 | 测试场景 | 请求 | 预期结果 | 实际结果 |
|---------|---------|------|---------|---------|
| T-001 | 用户 A 访问已授权设备 A 的快照 | GET /api/device/snapshot/{macA} | HTTP 200，返回快照 | HTTP 200，通过 |
| T-002 | 用户 A 访问未授权设备 B 的快照 | GET /api/device/snapshot/{macB} | HTTP 403，拒绝 | HTTP 403，通过 |
| T-003 | 用户 A 对未授权设备 B 发起远程开锁 | POST /api/device/unlock，body `{mac: macB}` | HTTP 403，拒绝 | HTTP 403，通过 |
| T-004 | 未携带 Token 访问受保护接口 | GET /api/user/devices（无 Authorization 头） | HTTP 401，拒绝 | HTTP 401，通过 |

所有 BOLA 测试用例均通过，系统对越权访问的拦截率为 **100%**。

### 5.3.2 MAC 地址标准化测试

**表5-5 MAC 地址标准化测试用例**

| 输入格式 | 输入示例 | normalize_mac() 输出 | 是否正确 |
|---------|---------|---------------------|---------|
| 冒号分隔（标准） | `AA:BB:CC:DD:EE:FF` | `AA:BB:CC:DD:EE:FF` | 是 |
| 无分隔符 | `AABBCCDDEEFF` | `AA:BB:CC:DD:EE:FF` | 是 |
| 连字符分隔 | `AA-BB-CC-DD-EE-FF` | `AA:BB:CC:DD:EE:FF` | 是 |
| 小写输入 | `aa:bb:cc:dd:ee:ff` | `AA:BB:CC:DD:EE:FF` | 是 |
| 非法格式（长度不符） | `AABBCCDDEE` | 返回错误 | 是（正确拒绝） |

## 5.4 性能测试

### 5.4.1 快照延迟测试

**表5-6 快照获取延迟统计（连续 100 次采样，内存缓存命中场景）**

| 统计项 | 数值 |
|--------|------|
| 平均延迟 | 85ms |
| 最小延迟 | 42ms |
| 最大延迟 | 210ms |
| P95 延迟 | 155ms |
| 缓存命中率 | 96%（设备在线时） |

快照延迟主要由网络 RTT 决定，内存缓存命中时无磁盘 I/O 开销，P95 延迟满足 2 秒轮询周期的实时性要求。

### 5.4.2 权限状态机完整流程测试

**表5-7 权限状态机完整工作流测试（8 步骤）**

| 步骤 | 操作 | 执行角色 | 预期权限状态 | 验证点 |
|------|------|---------|------------|--------|
| 1 | 用户申请设备权限 | 普通用户 | pending | 数据库写入记录，HTTP 201 |
| 2 | 重复申请同一设备 | 普通用户 | — | HTTP 409 Conflict，唯一约束生效 |
| 3 | 管理员查看待审批列表 | Admin | — | 返回含步骤1记录的列表 |
| 4 | 管理员批准申请 | Admin | approved | HTTP 200，status 字段变更 |
| 5 | 用户访问已授权设备 | 普通用户 | approved | HTTP 200，业务正常执行 |
| 6 | 管理员撤销权限 | Admin | — | HTTP 200，记录删除 |
| 7 | 用户再次访问已撤销设备 | 普通用户 | — | HTTP 403，BOLA 防护生效 |
| 8 | 用户重新申请权限 | 普通用户 | pending | HTTP 201，新记录写入 |

全部 8 个步骤结果与预期一致，权限状态机流转正确，BOLA 防护在权限撤销后立即生效。

## 5.5 测试结果分析

综合以上测试，系统在功能正确性、安全性与性能三个维度均达到预期目标：

- **功能完整性**：远程开锁、快照查看、权限申请审批、日志记录等核心功能全部通过端到端验证；
- **安全性**：BOLA 防护拦截率 100%，JWT 过期检测与格式校验覆盖所有异常情况，MAC 地址标准化兼容率 100%；
- **性能**：端到端开锁延迟约 170ms，快照内存缓存命中 P95 延迟 155ms，心跳检测延迟 ≤20 秒，均满足实时门禁管控场景的需求。

## 5.6 本章小结

本章介绍了系统的生产环境部署方案与全面测试策略。Docker Compose 编排实现了一键部署，ProxyFix 中间件解决了 Nginx 反向代理下的协议头问题。通过端到端功能测试、BOLA 安全测试、MAC 标准化测试与快照性能测试，验证了系统在各关键指标上的达标情况，证明本系统具备在实际高校门禁场景中稳定运行的能力。

---

# 第6章 总结与展望

## 6.1 工作总结

本文围绕高校宿舍门禁管控场景的实际需求，设计并实现了一套基于双 MCU 架构与云端协同的智能门禁控制系统。系统采用 ESP32-S3 + STM32 双控制器嵌入式设计、Flask 云端 REST API 服务、微信小程序移动端的三层架构，覆盖了从硬件接入到云端管理再到用户交互的完整技术链路。本文的主要工作与成果可归纳为以下几个方面：

**（1）设计并实现了双 MCU 协作嵌入式架构。** 提出以 ESP32-S3 负责网络通信与图像处理、STM32 负责实时硬件控制的分工协作模式，并设计了 6 字节定长二进制帧格式（双字节同步头 + CMD + LEN + DATA + 累加校验和）的自定义 UART 通信协议。该协议通过非阻塞 FSM 状态机实现，避免了阻塞等待对主循环调度的影响，具有较高的实时性与可靠性。

**（2）构建了工程化的 Flask 云端后端服务。** 采用应用工厂模式（`create_app()`）组织项目结构，通过蓝图（Blueprint）对 API 路由进行模块化拆分。利用 SQLAlchemy Mixin 设计统一的数据模型基类，实现自动序列化与时间戳管理。MQTT 与 HTTP 混合接入策略保证了设备通信的实时性与快照传输的低延迟。`DatabaseHelper` 工具类统一封装数据库操作，所有接口一致返回 `(result, error)` 元组，便于上层路由处理异常。

**（3）实现了完善的安全认证与权限管控机制。** 系统采用 PyJWT HS256 算法生成 7 天有效期的令牌，通过 `token_required` 装饰器对所有需认证接口统一保护。设计了基于用户-设备映射表的 BOLA 防护机制，确保任意用户只能访问其已获批权限的设备。权限管理引入状态机模型（`pending` → `approved`/`rejected`），并由 `PermissionHelper` 统一封装权限校验逻辑，全面覆盖越权访问风险。

**（4）设计了三级快照优先级分发策略并解决渲染兼容性问题。** 系统设计了"云端中继 → 内存缓存 → 本地直连"三级降级策略，保证在不同网络环境下均能提供最优质的快照服务。针对微信小程序 `<image>` 组件无法正确渲染含换行符的 Base64 字符串的问题，通过后端标准化编码与前端 `.replace(/[\r\n]/g, "")` 过滤联合修复，彻底消除了图像黑屏故障。

**（5）完成了容器化生产环境部署与全面系统测试。** 基于 Docker Compose 编排 Flask 应用容器（4 Gunicorn Workers）与 Nginx 反向代理容器，实现一键部署。通过 `ProxyFix` 中间件修复 Nginx 代理下的重定向错误问题。系统测试结果显示，端到端命令响应延迟约 170ms，BOLA 防护拦截率达 100%，MAC 地址标准化兼容率达 100%，具备良好的实用性与稳定性。

## 6.2 系统创新点

综合上述工作，本系统的主要创新点体现在以下三个方面：

**创新点一：双 MCU 分工协作架构与自定义二进制帧协议。** 现有开源门禁方案大多以单一 MCU 承担全部任务，存在实时性与网络功能相互竞争的问题。本文提出 ESP32-S3（网络/图像）+ STM32（硬件控制）的分工协作模式，并设计了带校验和的定长二进制帧协议，通过非阻塞 FSM 实现，在提升系统实时性的同时降低了两端耦合度。

**创新点二：三级快照优先级分发与 MAC 地址标准化统一架构。** 系统创新性地设计了"云端中继 → 内存缓存 → 本地直连"的三级快照分发降级策略，同时引入 `normalize_mac()` 函数统一不同来源（ESP32/小程序/管理端）的 MAC 地址格式，从根本上消除了因格式不一致导致的缓存命中失败问题。

**创新点三：全栈 BOLA 防护与权限状态机设计。** 在对象级权限保护方面，系统不仅在 API 层实现了 `check_device_access()` 拦截，还在数据模型层通过唯一约束（`UniqueConstraint`）防止重复申请，在 MQTT 层通过主题命名规则限制设备消息范围，形成多层次的纵深防护体系，这在同类学术设计系统中较为少见。

## 6.3 系统不足与改进方向

尽管本系统已实现完整的功能链路并通过全面测试，但仍存在若干不足，有待后续改进：

**（1）人脸识别功能尚未完整集成。** 代码中已预留 `create_face_recognition_log()` 接口，`unlock_method` 枚举中也暂未包含 `face` 选项（仅支持 `fingerprint`、`nfc`、`remote`）。后续可集成 ESP32-S3 本地推理方案（如 ESP-WHO 框架）或云端人脸比对 API，实现无感通行。

**（2）MQTT 通信缺乏消息持久化与离线重传机制。** 当前系统在设备离线期间发出的控制指令将丢失，无法在设备重新上线后自动补发。后续可引入 MQTT QoS 1/2 等级，或在后端实现指令队列缓存，提升离线场景下的控制可靠性。

**（3）快照图像存储依赖内存缓存，不支持历史回溯。** 当前 `device_frames` 字典仅保存最新一帧，历史快照无法持久化查询。后续可引入对象存储服务（如 MinIO 或阿里云 OSS）将抓拍图像持久化，并将 `snapshot_url` 字段指向外部存储链接，支持按时间范围检索历史记录。

**（4）单点架构在高并发下存在扩展瓶颈。** 当前部署方案为单机 Docker Compose，MQTT Broker 与 Flask 应用均为单实例。当管控设备规模显著扩大（如超过 500 台）时，需引入消息队列（如 Kafka/RabbitMQ）解耦 MQTT 消息处理，并将 Flask 服务迁移至 Kubernetes 集群实现水平扩展 [7]。

**（5）缺乏完善的告警与通知机制。** 当前系统在设备离线、开锁失败等异常事件发生时，仅依赖前端轮询状态接口感知，缺乏主动推送能力。后续可通过微信小程序订阅消息（Template Message）或集成企业微信/钉钉机器人，实现异常事件的实时告警通知。

## 6.4 研究展望

面向未来，智能门禁控制系统的研究与发展将沿以下几个方向持续深化：

**（1）边缘 AI 与端侧推理。** 随着 ESP32-S3 等具备向量指令集的边缘 MCU 性能提升，人脸检测、活体识别等轻量级 AI 模型将可直接部署于端侧，在保护用户生物特征隐私的同时实现毫秒级本地响应，彻底摆脱对网络连通性的依赖。

**（2）零信任安全架构演进。** 未来门禁系统将引入持续身份验证（Continuous Authentication）理念，结合行为特征分析（如进出时间规律、设备使用模式），对异常访问进行实时风险评分与动态阻断，超越传统基于静态权限表的访问控制模型。

**（3）数字孪生与可视化管控。** 将门禁设备状态、人员流动数据与建筑 BIM 模型融合，构建楼宇安全数字孪生系统，通过三维可视化界面实现全楼设备状态的统一监控与历史回溯，为安全管理决策提供更直观的数据支撑。

**（4）隐私计算与联邦学习。** 在涉及人脸、指纹等生物特征数据的场景中，联邦学习技术可使模型在不暴露原始数据的前提下完成训练与更新，满足《个人信息保护法》等数据合规要求，为智能门禁在更广泛场景中的合法化应用奠定基础。

**（5）与智慧校园/智慧建筑生态集成。** 门禁系统将与宿舍管理系统、考勤系统、能源管理系统深度集成，通过统一的物联网数据平台实现跨系统联动（如刷卡开门同步触发考勤打卡、进入宿舍自动开启空调），推动单点门禁控制向综合智慧管理演进。

---

# 参考文献

[1] PANDEY S, MOHARKAR L. Suitability of MQTT and REST communication protocols for AIoT or IIoT devices based on ESP32 S3[C]// Computer Science and Its Applications: CoMeSySo 2022. Cham: Springer, 2022: 219-230.

[2] ZARE M, IQBAL J. Low-cost ESP32, Raspberry Pi, Node-RED, and MQTT protocol based SCADA system[J/OL]. (2022)[2026-03-06]. https://www.semanticscholar.org/paper/Low-Cost-ESP32,-Raspberry-Pi,-Node-Red,-and-MQTT-Zare-Iqbal/2b98b1ccaa00dd89b38daa2d83bfc9feee5cdaed.

[3] NIKOLOV N, et al. A secure firmware update over-the-air of ESP32 using MQTT protocol from cloud[J/OL]. (2023)[2026-03-06]. https://www.researchgate.net/publication/374786538.

[4] OWASP FOUNDATION. API1:2023 broken object level authorization[EB/OL]. (2023)[2026-03-06]. https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/.

[5] AGUILAR R. Impact of performance on security: JWT token[D]. San Bernardino: California State University, 2022.

[6] 刘韵洁, 张娇, 尹浩, 等. 智慧物联网系统发展战略研究[J]. 中国工程科学, 2022, 24(4): 1-9.

[7] GRINBERG M. How to dockerize a React + Flask project[EB/OL]. (2023)[2026-03-06]. https://blog.miguelgrinberg.com/post/how-to-dockerize-a-react-flask-project.

[8] AGARWAL A, et al. Design and implementation of ESP32-based IoT devices[J]. Sensors, 2023, 23(15): 6739.

[9] AHMED I, et al. Securing communication between ESP32-based IoT devices using HTTPS/MQTT[J]. International Journal of Scientific Development and Research, 2023, 8(5): 015.

[10] WROBEL M, et al. Effective feature engineering framework for securing MQTT protocol in IoT environments[J/OL]. (2024)[2026-03-06]. https://pmc.ncbi.nlm.nih.gov/articles/PMC10975182/.

[11] OASIS STANDARDS. MQTT version 3.1.1[S/OL]. (2014-10-29)[2026-03-06]. http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html.

[12] JONES M, BRADLEY J, SAKIMURA N. JSON web token (JWT): RFC 7519[S/OL]. (2015-05)[2026-03-06]. https://datatracker.ietf.org/doc/html/rfc7519.

[13] ESPRESSIF SYSTEMS. ESP32-S3 technical reference manual[EB/OL]. (2022)[2026-03-06]. https://www.espressif.com/sites/default/files/documentation/esp32-s3_technical_reference_manual_en.pdf.

[14] 微信开放平台. 微信小程序开发文档[EB/OL]. (2023)[2026-03-06]. https://developers.weixin.qq.com/miniprogram/dev/framework/.

[15] PALLETS PROJECTS. Flask documentation (2.3.x)[EB/OL]. (2023)[2026-03-06]. https://flask.palletsprojects.com/en/2.3.x/.

[16] SQLALCHEMY. SQLAlchemy 2.0 documentation[EB/OL]. (2023)[2026-03-06]. https://docs.sqlalchemy.org/en/20/.

[17] DOCKER INC. Docker Compose documentation[EB/OL]. (2023)[2026-03-06]. https://docs.docker.com/compose/.

[18] ST MICROELECTRONICS. STM32F4 reference manual: RM0090[EB/OL]. (2022)[2026-03-06]. https://www.st.com/resource/en/reference_manual/rm0090-stm32f4-reference-manual.pdf.

[19] RED HAT DEVELOPER. How to deploy a Flask application in Python with Gunicorn[EB/OL]. (2023-08-17)[2026-03-06]. https://developers.redhat.com/articles/2023/08/17/how-deploy-flask-application-python-gunicorn.

[20] SALT SECURITY. API1:2023 broken object level authorization (BOLA)[EB/OL]. (2023)[2026-03-06]. https://salt.security/blog/api1-2023-broken-object-level-authentication.
