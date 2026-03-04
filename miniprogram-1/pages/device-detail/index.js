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
   * 第二部分：实时快照加载（通过后端代理，自动处理占位符）
   * 
   * ⚠️ V3.1 重要变更：统一接收 JSON 格式的 Base64 数据
   * - 后端现在返回 JSON: {success: true, data: {image_base64: "..."}}
   * - 前端强制清理换行符（解决微信小程序黑屏问题）
   * - 双重保险：后端去除换行符 + 前端额外清理
   */
  
  loadDeviceSnapshot(mac_address) {
    console.log('[Snapshot] Loading device snapshot, source:', this.data.snapshotSource);
    
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');
    const mac_clean = mac_address.replace(/:/g, '');
    const device = this.data.device;
    
    let snapshotUrl;
    let needAuth = true;
    
    if (this.data.snapshotSource === 'local' && device.ip_address) {
      snapshotUrl = `http://${device.ip_address}:81/stream?action=snapshot`;
      needAuth = false;
      console.log('[Snapshot] Using local ESP32');
    } else {
      snapshotUrl = `${apiUrl}/device/snapshot/${mac_clean}`;
      console.log('[Snapshot] Using backend proxy');
    }
    
    wx.request({
      url: snapshotUrl,
      method: 'GET',
      header: needAuth ? {
        'Authorization': 'Bearer ' + token
      } : {},
      responseType: needAuth ? 'text' : 'arraybuffer',  // ✅ 后端返回 JSON，前端接收文本
      timeout: 8000,
      success: (res) => {
        if (res.statusCode === 200) {
          let imageUrl;
          let source = 'unknown';
          
          if (needAuth) {
            // ✅ 解析 JSON 响应
            try {
              const jsonData = typeof res.data === 'string' ? JSON.parse(res.data) : res.data;
              
              if (!jsonData.success || !jsonData.data || !jsonData.data.image_base64) {
                console.error('[Snapshot] Invalid JSON response:', jsonData);
                this.setData({ isSnapshotLoading: false });
                return;
              }
              
              // ✅ 核心修复：强制清理所有可能存在的换行符（\r\n）
              // 微信小程序的 <image> 标签对 Base64 非常严格，
              // 任何换行符都会导致图片渲染为灰块或黑屏
              let rawBase64 = jsonData.data.image_base64;
              let cleanBase64 = rawBase64.replace(/[\r\n]/g, "");  // 🔥 关键修复
              
              imageUrl = 'data:image/jpeg;base64,' + cleanBase64;
              source = jsonData.data.source || 'proxy-source';
              
              console.log(`[Snapshot] Loaded from: ${source} (size: ${jsonData.data.size || 'unknown'} bytes)`);
              if (jsonData.data.frame_age) {
                console.log(`[Snapshot] Frame age: ${jsonData.data.frame_age}s`);
              }
            } catch (err) {
              console.error('[Snapshot] JSON parse error:', err);
              this.setData({ isSnapshotLoading: false });
              return;
            }
          } else {
            // 本地 ESP32 直连模式（仍然使用 arraybuffer）
            const arrayBuffer = res.data;
            const base64 = wx.arrayBufferToBase64(arrayBuffer);
            
            // ✅ 额外清理（即使是本地模式也执行，增强鲁棒性）
            const cleanBase64 = base64.replace(/[\r\n]/g, "");
            imageUrl = 'data:image/jpeg;base64,' + cleanBase64;
            source = 'esp32-direct';
            
            console.log(`[Snapshot] Loaded from: ${source}`);
          }
          
          this.setData({
            videoFrame: imageUrl,
            isSnapshotLoading: false
          });
        } else {
          console.warn('[Snapshot] Failed with status:', res.statusCode);
          this.setData({ isSnapshotLoading: false });
        }
      },
      fail: (err) => {
        console.error('[Snapshot] Failed:', err);
        this.setData({ isSnapshotLoading: false });
      }
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
