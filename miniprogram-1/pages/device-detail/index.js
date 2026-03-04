// pages/device-detail/index.js
/**
 * 设备详情页 - 沉浸式监控 + 多维控制（HTTP 版本，不使用 WebSocket）
 * 
 * 核心功能：
 * 1. 显示设备实时快照（HTTP GET）
 * 2. MQTT 指令分发（开启、警报、补光等）
 * 3. 设备信息获取
 * 4. 设备解绑流程
 */

const envConfig = require('../../config/env.js');

Page({
  data: {
    device: {
      mac_address: '',
      name: '',
      status: 'online',
      created_at: '',
      ip_address: ''
    },
    
    // 视频相关（HTTP 快照模式）
    videoFrame: '',  // 快照 URL (实时或占位符)
    isSnapshotLoading: false,
    snapshotSource: 'proxy',  // 'proxy'（后端代理）或 'local'（本地ESP32直连）
    
    // 设备信息
    deviceInfo: {
      rssi: '-80 dBm',
      signalLevel: 'medium',
      uptime: '--',
      firmwareVersion: 'v1.0.0',
      temperature: '--°C'
    },
    
    // 控制状态
    actionStates: {
      open_door: '',
      keep_open: '',
      alarm: '',
      light: '',
      query_status: '',
      reboot: ''
    }
  },

  onLoad(options) {
    console.log(' 设备详情页 onLoad ', options);
    
    const { mac_address } = options;
    if (!mac_address) {
      wx.showToast({
        title: '设备信息错误',
        icon: 'none'
      });
      setTimeout(() => wx.navigateBack(), 1500);
      return;
    }
    
    this.setData({
      'device.mac_address': mac_address
    });
    
    // 1. 加载设备详情
    this.loadDeviceDetail(mac_address);
    
    // 2. 加载设备快照
    this.loadDeviceSnapshot(mac_address);
    
    // 3. 启动快照定时刷新
    this.startSnapshotPolling(mac_address);
    
    // 4. 启动状态定时轮询
    this.startStatusPolling();
  },

  onUnload() {
    console.log(' 设备详情页 onUnload ');
    
    // 1. 清理快照轮询定时器
    if (this.snapshotPollingTimer) {
      clearInterval(this.snapshotPollingTimer);
    }
    
    // 2. 清理状态轮询定时器
    if (this.statusPollingTimer) {
      clearInterval(this.statusPollingTimer);
    }
  },

  /**
   * 第一部分：设备详情加载
   */
  
  loadDeviceDetail(mac_address) {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');
    
    // 从全局数据获取设备信息
    const app = getApp();
    const deviceList = app.globalData.devices || [];
    const device = deviceList.find(d => d.mac_address === mac_address);
    
    if (device) {
      this.setData({
        device: {
          mac_address: device.mac_address,
          name: device.name || '未命名设备',
          status: device.status || 'online',
          created_at: device.created_at || '--',
          ip_address: device.ip_address || ''
        }
      });
      
      // 更新页面标题
      wx.setNavigationBarTitle({
        title: device.name
      });
    }
    
    // 查询设备实时状态
    this.queryDeviceStatus(mac_address, token, apiUrl);
  },

  queryDeviceStatus(mac_address, token, apiUrl) {
    // 发送查询状态指令到后端
    wx.request({
      url: apiUrl + '/device/action',
      method: 'POST',
      header: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      data: {
        mac_address: mac_address,
        action_type: 'query_status'
      },
      success: (res) => {
        console.log('设备状态查询响应:', res);
        if (res.statusCode === 200 && res.data.success) {
          // 更新设备信息（后端返回的实时数据）
          if (res.data.data && res.data.data.device_info) {
            this.setData({
              deviceInfo: res.data.data.device_info
            });
          }
        }
      },
      fail: (err) => {
        console.error('设备状态查询失败:', err);
      }
    });
  },

  /**
   * 第二部分：实时快照加载（优先级策略）
   * 
   * V3.2 新特性：本地优先策略
   * 优先级1（首选）：本地 ESP32 直连（http://local_ip:81/stream?action=snapshot）
   *   - 优点：无网络延迟，实时性最好
   *   - 缺点：依赖本地网络环境
   * 
   * 优先级2（备选）：后端代理（https://dev.api.5i03.cn/api/device/snapshot/<mac>）
   *   - 优点：云端中继、支持异地访问
   *   - 缺点：网络延迟可能较大
   * 
   * 优先级3（兜底）：占位符（校园门禁场景提示）
   *   - 显示：离线提示、网络异常提示
   */

  loadDeviceSnapshot(mac_address) {
    const device = this.data.device;
    const hasLocalIP = device.ip_address && device.ip_address.trim() !== '';
    
    console.log('[Snapshot] 加载策略：优先使用本地源');
    
    if (hasLocalIP) {
      // 优先级1：尝试本地 ESP32 直连（超时3秒快速失败）
      this.loadFromLocalESP32(device.ip_address, mac_address);
    } else {
      // 没有本地IP，直接跳到后端代理
      console.log('[Snapshot] 设备无本地IP，跳转到后端代理');
      this.loadFromBackendProxy(mac_address);
    }
  },

  loadFromLocalESP32(ip_address, mac_address) {
    console.log(`[Snapshot] 尝试优先级1：本地 ESP32 (${ip_address}:81)`);
    
    const snapshotUrl = `http://${ip_address}:81/stream?action=snapshot`;
    
    wx.request({
      url: snapshotUrl,
      method: 'GET',
      header: {},
      responseType: 'arraybuffer',
      timeout: 3000,  // 本地源使用短超时（3秒），快速失败
      success: (res) => {
        if (res.statusCode === 200) {
          console.log('[Snapshot] 成功从本地 ESP32 获取快照');
          const arrayBuffer = res.data;
          const base64 = wx.arrayBufferToBase64(arrayBuffer);
          const cleanBase64 = base64.replace(/[\r\n]/g, "");
          
          this.setData({
            videoFrame: 'data:image/jpeg;base64,' + cleanBase64,
            isSnapshotLoading: false,
            snapshotSource: 'local'
          });
        } else {
          console.warn(`[Snapshot] 本地源返回异常状态 ${res.statusCode}，降级到后端`);
          this.loadFromBackendProxy(mac_address);
        }
      },
      fail: (err) => {
        console.warn(`[Snapshot] 本地源连接失败 (${err.errMsg})，降级到后端代理`);
        this.loadFromBackendProxy(mac_address);
      }
    });
  },

  loadFromBackendProxy(mac_address) {
    console.log('[Snapshot] 尝试优先级2：后端代理');
    
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');
    const mac_clean = mac_address.replace(/:/g, '');
    const snapshotUrl = `${apiUrl}/device/snapshot/${mac_clean}`;
    
    wx.request({
      url: snapshotUrl,
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + token
      },
      responseType: 'text',
      timeout: 8000,  // 后端代理使用较长超时（8秒）
      success: (res) => {
        if (res.statusCode === 200) {
          console.log('[Snapshot] 成功从后端代理获取快照');
          
          try {
            const jsonData = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
            
            if (!jsonData.success || !jsonData.data || !jsonData.data.image_base64) {
              console.error('[Snapshot] JSON 响应无效:', jsonData);
              this.loadFromPlaceholder('后端数据异常');
              return;
            }
            
            // 关键修复：强制清理所有可能存在的换行符
            let rawBase64 = jsonData.data.image_base64;
            let cleanBase64 = rawBase64.replace(/[\r\n]/g, "");
            
            this.setData({
              videoFrame: 'data:image/jpeg;base64,' + cleanBase64,
              isSnapshotLoading: false,
              snapshotSource: 'proxy'
            });
            
            const source = jsonData.data.source || 'proxy';
            console.log(`[Snapshot] 数据来源：${source}`);
            
          } catch (err) {
            console.error('[Snapshot] JSON 解析失败:', err);
            this.loadFromPlaceholder('数据格式错误');
          }
        } else {
          console.warn(`[Snapshot] 后端代理返回异常 ${res.statusCode}，显示离线提示`);
          this.loadFromPlaceholder(`服务异常 (${res.statusCode})`);
        }
      },
      fail: (err) => {
        console.error(`[Snapshot] 后端代理连接失败 (${err.errMsg})，显示离线提示`);
        this.loadFromPlaceholder('网络不可用');
      }
    });
  },

  loadFromPlaceholder(reason = '未知错误') {
    console.log(`[Snapshot] 默认兜底：显示离线占位符 (${reason})`);
    
    // 创建一个简单的离线提示图片（灰色背景）
    const placeholderBase64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQIW2NgAAIAAAUAAdafFs0AAAAASUVORK5CYII=';
    
    this.setData({
      videoFrame: 'data:image/jpeg;base64,' + placeholderBase64,
      isSnapshotLoading: false,
      snapshotSource: 'placeholder'
    });
  },

  /**
   * 第三部分：多维控制指令分发
   */
  
  handleAction(e) {
    const { action } = e.currentTarget.dataset;
    const state = e.currentTarget.dataset.state || undefined;
    
    console.log('执行动作:', action, 'state:', state);
    
    if (!action) return;
    
    // 设置加载状态
    this.setData({
      [`actionStates.${action}`]: 'loading'
    });
    
    // 调用后端接口发送 MQTT 指令
    this.sendDeviceAction(action, state);
  },

  sendDeviceAction(actionType, actionState) {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');
    const mac_address = this.data.device.mac_address;
    
    const payload = {
      mac_address: mac_address,
      action_type: actionType
    };
    
    // 某些动作需要状态参数
    if (actionState !== undefined) {
      payload.state = parseInt(actionState);
    }
    
    wx.request({
      url: apiUrl + '/device/action',
      method: 'POST',
      header: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      data: payload,
      success: (res) => {
        console.log('设备动作响应:', res);
        
        if (res.statusCode === 200 && res.data.success) {
          // 设置成功状态
          this.setData({
            [`actionStates.${actionType}`]: 'success'
          });
          
          wx.showToast({
            title: res.data.message || '指令已发送',
            icon: 'success',
            duration: 2000
          });
          
          // 3 秒后清除成功状态
          setTimeout(() => {
            this.setData({
              [`actionStates.${actionType}`]: ''
            });
          }, 3000);
        } else {
          wx.showToast({
            title: res.data.message || '指令发送失败',
            icon: 'none',
            duration: 2000
          });
          this.setData({
            [`actionStates.${actionType}`]: ''
          });
        }
      },
      fail: (err) => {
        console.error('指令发送失败:', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none',
          duration: 2000
        });
        this.setData({
          [`actionStates.${actionType}`]: ''
        });
      }
    });
  },

  /**
   * 第四部分：快照手动刷新
   */
  
  handleStreamRefresh() {
    console.log('手动刷新快照');
    this.loadDeviceSnapshot(this.data.device.mac_address);
  },

  /**
   * 第五部分：设备解绑流程
   */
  
  handleUnbindClick() {
    console.log('点击解绑按钮');
    const deviceName = this.data.device.name || '该设备';
    
    wx.showModal({
      title: '确认解除绑定',
      content: `你确定要解除与 ${deviceName} 的绑定吗？解绑后，你将无法远程控制该设备，此操作无法撤销。`,
      confirmText: '确认解绑',
      cancelText: '取消',
      confirmColor: '#EE0A24',
      success: (res) => {
        if (res.confirm) {
          this.handleUnbindConfirm();
        }
      }
    });
  },

  handleUnbindConfirm() {
    console.log('确认解绑');
    
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');
    const mac_address = this.data.device.mac_address;
    
    wx.showLoading({
      title: '解绑中...',
      mask: true
    });
    
    wx.request({
      url: apiUrl + '/user/devices/' + mac_address,
      method: 'DELETE',
      header: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        wx.hideLoading();
        console.log('解绑响应:', res);
        
        if (res.statusCode === 200 && res.data.success) {
          wx.showToast({
            title: '解绑成功',
            icon: 'success',
            duration: 2000
          });
          
          // 返回控制台页面并刷新
          setTimeout(() => {
            wx.navigateBack();
            // 通知控制台页面刷新
            const pages = getCurrentPages();
            const prevPage = pages[pages.length - 2];
            if (prevPage && prevPage.loadDevices) {
              prevPage.loadDevices();
            }
          }, 2000);
        } else {
          wx.showToast({
            title: res.data.message || '解绑失败',
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('解绑请求失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 辅助方法
   */

  stopPropagation() {
    // 阻止事件冒泡
  },

  onVideoLoad() {
    console.log('快照加载成功');
  },

  onVideoError(e) {
    console.error('快照加载失败:', e);
    wx.showToast({
      title: '快照加载失败，请检查设备是否在线',
      icon: 'none',
      duration: 2000
    });
  },

  /**
   * 切换快照源（代理 <-> 本地ESP32直连）
   */
  toggleSnapshotSource() {
    const device = this.data.device;

    if (!device.ip_address) {
      wx.showToast({
        title: '设备未配置IP地址',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    const newSource = this.data.snapshotSource === 'proxy' ? 'local' : 'proxy';
    this.setData({
      snapshotSource: newSource
    });

    wx.showToast({
      title: `已切换至${newSource === 'local' ? '本地' : '代理'}源`,
      icon: 'success',
      duration: 1500
    });

    this.loadDeviceSnapshot(device.mac_address);
  },

  /**
   * 定时轮询
   */
  
  startSnapshotPolling(mac_address) {
    // 每 10 秒刷新一次快照（降低频率避免 504 超时雪崩）
    this.snapshotPollingTimer = setInterval(() => {
      this.loadDeviceSnapshot(mac_address);
    }, 10000);
  },

  startStatusPolling() {
    // 每 30 秒查询一次设备状态
    this.statusPollingTimer = setInterval(() => {
      this.queryDeviceStatus(
        this.data.device.mac_address,
        wx.getStorageSync('token'),
        envConfig.getApiUrl()
      );
    }, 30000);
  }
});
