// pages/console/index.js
const envConfig = require('../../config/env.js');
const pageHelper = require('../../utils/page-helper.js');

Page({
  data: {
    devices: [],               // 设备列表
    videoStreamUrl: '',        // 视频流 URL
    videoError: false,
    showBindModal: false,      // 是否显示绑定设备弹窗
    bindMacAddress: '',        // 待绑定的 MAC 地址
    bindDeviceName: ''         // 待绑定的设备名称
  },

  onLoad(options) {
    console.log(' 控制台页面 onLoad ', options);
    
    if (!pageHelper.ensureLogin()) {
      return;
    }
    
    const app = getApp();
    
    // 获取视频流地址
    this.setData({
      videoStreamUrl: app.globalData.config?.servers?.video_stream || 'https://dev.api.5i03.cn/api/device/snapshot'
    });
    
    this.loadDevices();
  },

  onShow() {
    console.log(' 控制台页面 onShow ');
    
    if (!pageHelper.ensureLogin()) {
      return;
    }
    
    this.loadDevices();
  },

  onPullDownRefresh() {
    this.loadDevices();
    wx.stopPullDownRefresh();
  },

  loadDevices() {
    const that = this;
    const apiUrl = envConfig.getApiUrl();
    
    console.log(' 加载用户的已批准设备列表 ');
    console.log('API 地址:', apiUrl);
    
    if (!apiUrl) {
      pageHelper.showError('API 地址未配置', 3000);
      return;
    }
    
    // 调用 /api/user/devices 获取用户已批准的所有设备
    wx.request({
      url: apiUrl + '/user/devices',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success(res) {
        console.log(' 设备列表响应 ', res);
        
        // 处理 401 未授权错误
        if (res.statusCode === 401) {
          console.log('Token 无效或已过期');
          pageHelper.handleUnauthorized({ redirectDelay: 2000 });
          return;
        }
        
        // 成功获取设备列表
        if (res.statusCode === 200 && res.data && res.data.success) {
          const devices = res.data.data || [];
          console.log(`已加载 ${devices.length} 个已授权设备:`, devices);
          
          that.setData({
            devices: devices
          });
          
          // 同步到全局数据，供详情页使用
          const app = getApp();
          app.globalData.devices = devices;
          console.log('设备列表已同步到 globalData');
          
          // 如果设备列表为空，显示空状态提示
          if (devices.length === 0) {
            console.log('用户没有已批准的设备');
          }
        } else {
          wx.showToast({
            title: res.data?.message || '加载设备失败',
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail(err) {
        console.error('加载设备请求失败:', err);
        wx.showToast({
          title: '网络连接失败，请检查网络',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 处理单个设备的开锁操作
   * @param {Object} e - 事件对象，包含设备的 mac_address 和 name
   */
  onUnlockDevice(e) {
    const { mac, name } = e.currentTarget.dataset;
    
    if (!mac) {
      wx.showToast({
        title: '设备信息错误',
        icon: 'none'
      });
      return;
    }

    const apiUrl = envConfig.getApiUrl();
    
    // 移除MAC地址中的冒号，统一使用无冒号格式（如 ACA704260CFC）
    const macWithoutColon = mac.replace(/:/g, '');

    wx.showLoading({
      title: '发送开锁指令...',
      mask: true
    });

    wx.request({
      url: apiUrl + '/devices/' + macWithoutColon + '/unlock',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      data: {},
      success(res) {
        wx.hideLoading();
        console.log(' 开锁响应 ', res);
        
        // 处理 401 未授权错误
        if (res.statusCode === 401) {
          console.log('Token 无效或已过期，跳转到登录页面');
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          wx.showToast({
            title: '登录已过期，请重新登录',
            icon: 'none',
            duration: 2000
          });
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/login/index'
            });
          }, 2000);
          return;
        }
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          pageHelper.showSuccess('开锁成功');
        } else {
          pageHelper.showError(res.data?.message || '开锁失败');
        }
      },
      fail(err) {
        wx.hideLoading();
        console.error('开锁请求失败:', err);
        pageHelper.showError('网络错误，请重试');
      }
    });
  },

  /**
   * 显示绑定设备对话框
   */
  showBindDialog() {
    this.setData({
      showBindModal: true,
      bindMacAddress: '',
      bindDeviceName: ''
    });
  },

  /**
   * 隐藏绑定设备对话框
   */
  hideBindDialog() {
    this.setData({
      showBindModal: false,
      bindMacAddress: '',
      bindDeviceName: ''
    });
  },

  /**
   * 阻止事件冒泡
   */
  stopPropagation() {
    // 阻止点击对话框内容时关闭弹窗
  },

  /**
   * MAC 地址输入
   */
  onMacAddressInput(e) {
    this.setData({
      bindMacAddress: e.detail.value
    });
  },

  /**
   * 设备名称输入
   */
  onDeviceNameInput(e) {
    this.setData({
      bindDeviceName: e.detail.value
    });
  },

  /**
   * 确认添加设备（改用申请-审批工作流）
   */
  confirmBindDevice() {
    const { bindMacAddress, bindDeviceName } = this.data;
    
    // 验证 MAC 地址格式
    if (!bindMacAddress || bindMacAddress.trim() === '') {
      wx.showToast({
        title: '请输入 MAC 地址',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 简单的 MAC 地址格式验证
    const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
    if (!macRegex.test(bindMacAddress.trim())) {
      wx.showToast({
        title: 'MAC 地址格式错误',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    const apiUrl = envConfig.getApiUrl();

    wx.showLoading({
      title: '正在提交申请...',
      mask: true
    });

    wx.request({
      url: apiUrl + '/user/apply_device',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      data: {
        mac_address: bindMacAddress.trim(),
        reason: bindDeviceName.trim() || '申请绑定设备'
      },
      success: (res) => {
        wx.hideLoading();
        console.log(' 申请设备响应 ', res);
        
        // 处理 401 未授权错误
        if (res.statusCode === 401) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          wx.showToast({
            title: '登录已过期，请重新登录',
            icon: 'none',
            duration: 2000
          });
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/login/index'
            });
          }, 2000);
          return;
        }
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          wx.showToast({
            title: '申请已提交，等待管理员审批',
            icon: 'success',
            duration: 2500
          });
          this.hideBindDialog();
          // 重新加载设备列表（显示已批准的设备）
          setTimeout(() => {
            this.loadDevices();
          }, 500);
        } else {
          // 显示后端返回的错误信息
          const errorMsg = res.data?.message || '申请失败';
          wx.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 2500
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('申请设备请求失败:', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 在弹窗中扫码输入设备码
   */
  handleScanCodeInModal() {
    wx.scanCode({
      onlyFromCamera: true,
      scanType: ['qrCode'],
      success: (res) => {
        console.log('扫码成功:', res);
        
        // 从扫码结果中提取 MAC 地址
        const result = res.result;
        let macAddress = '';
        
        if (result.includes('mac=')) {
          const match = result.match(/mac=([0-9A-Fa-f:]{17}|[0-9A-Fa-f-]{17})/);
          if (match) {
            macAddress = match[1];
          }
        } else {
          const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
          if (macRegex.test(result)) {
            macAddress = result;
          }
        }
        
        if (!macAddress) {
          wx.showToast({
            title: '无效的设备二维码',
            icon: 'none',
            duration: 2000
          });
          return;
        }
        
        // 将扫描到的 MAC 地址填入输入框
        this.setData({
          bindMacAddress: macAddress
        });
        
        wx.showToast({
          title: '已识别设备码',
          icon: 'success',
          duration: 1500
        });
      },
      fail: (err) => {
        console.error('扫码失败:', err);
        if (err.errMsg.includes('cancel')) {
          return;
        }
        wx.showToast({
          title: '扫码失败',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 扫码后发起设备绑定申请。
   */
  handleScanCode() {
    wx.scanCode({
      onlyFromCamera: true,  // 仅使用相机扫码
      scanType: ['qrCode'],  // 仅处理二维码
      success: (res) => {
        console.log('扫码成功:', res);
        
        // 从扫码结果提取 MAC
        const result = res.result;
        let macAddress = '';
        
        // 同时支持 URL 参数和纯 MAC 文本
        
        if (result.includes('mac=')) {
          // URL 中提取
          const match = result.match(/mac=([0-9A-Fa-f:]{17}|[0-9A-Fa-f-]{17})/);
          if (match) {
            macAddress = match[1];
          }
        } else {
          // 纯 MAC 文本
          const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
          if (macRegex.test(result)) {
            macAddress = result;
          }
        }
        
        if (!macAddress) {
          wx.showToast({
            title: '无效的设备二维码',
            icon: 'none',
            duration: 2000
          });
          return;
        }
        
        // 二次确认后再提交申请
        wx.showModal({
          title: '申请绑定设备',
          content: `是否申请绑定设备 ${macAddress}？\n\n提交后需要等待管理员审批。`,
          confirmText: '确认申请',
          cancelText: '取消',
          success: (modalRes) => {
            if (modalRes.confirm) {
              this.submitDeviceApplication(macAddress);
            }
          }
        });
      },
      fail: (err) => {
        console.error('扫码失败:', err);
        if (err.errMsg.includes('cancel')) {
          // 用户主动取消时不提示
          return;
        }
        wx.showToast({
          title: '扫码失败',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 提交设备绑定申请
   * @param {string} macAddress - 设备 MAC 地址
   */
  submitDeviceApplication(macAddress) {
    const apiUrl = envConfig.getApiUrl();

    wx.showLoading({
      title: '正在提交申请...',
      mask: true
    });

    wx.request({
      url: apiUrl + '/user/apply_device',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      data: {
        mac_address: macAddress,
        reason: '扫码申请绑定设备'
      },
      success: (res) => {
        wx.hideLoading();
        console.log(' 提交申请响应 ', res);
        
        // 处理 401 未授权错误
        if (res.statusCode === 401) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          wx.showToast({
            title: '登录已过期，请重新登录',
            icon: 'none',
            duration: 2000
          });
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/login/index'
            });
          }, 2000);
          return;
        }
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          wx.showModal({
            title: '申请已提交',
            content: '您的设备绑定申请已提交成功，请等待管理员审批。审批结果会在"个人配置"页面中查看。',
            showCancel: false,
            confirmText: '知道了'
          });
        } else {
          // 处理特定错误码
          const errorCode = res.data?.error_code;
          let errorMsg = res.data?.message || '申请失败';
          
          if (errorCode === 'DUPLICATE_APPLICATION') {
            errorMsg = '您已提交过该设备的申请，请勿重复提交';
          } else if (errorCode === 'ALREADY_BOUND') {
            errorMsg = '您已绑定该设备，无需重复申请';
          }
          
          wx.showToast({
            title: errorMsg,
            icon: 'none',
            duration: 3000
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('提交申请失败:', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 显示绑定设备对话框
   */
  showBindDialog() {
    this.setData({
      showBindModal: true,
      bindMacAddress: '',
      bindDeviceName: ''
    });
  },

  /**
   * 隐藏绑定设备对话框
   */
  hideBindDialog() {
    this.setData({
      showBindModal: false,
      bindMacAddress: '',
      bindDeviceName: ''
    });
  },

  /**
   * 阻止事件冒泡
   */
  stopPropagation() {
    // 空函数，用于阻止点击事件冒泡到遮罩层
  },

  /**
   * MAC 地址输入处理
   */
  onMacAddressInput(e) {
    this.setData({
      bindMacAddress: e.detail.value
    });
  },

  /**
   * 设备名称输入处理
   */
  onDeviceNameInput(e) {
    this.setData({
      bindDeviceName: e.detail.value
    });
  },

  /**
   * 确认绑定设备
   */
  confirmBindDevice() {
    const { bindMacAddress, bindDeviceName } = this.data;

    if (!bindMacAddress.trim()) {
      wx.showToast({
        title: '请输入设备 MAC 地址',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    // 验证 MAC 地址格式
    const macRegex = /^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$/;
    if (!macRegex.test(bindMacAddress.trim())) {
      wx.showToast({
        title: 'MAC 地址格式不正确',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    this.hideBindDialog();
    this.submitDeviceApplication(bindMacAddress.trim());
  },

  /**
   * 导航到设备详情页
   * @param {Object} e - 事件对象，包含设备 MAC 地址
   */
  handleDeviceCardTap(e) {
    const { mac } = e.currentTarget.dataset;
    
    if (!mac) {
      wx.showToast({
        title: '设备信息错误',
        icon: 'none'
      });
      return;
    }
    
    console.log('导航到设备详情页:', mac);
    
    wx.navigateTo({
      url: `/pages/device-detail/index?mac_address=${mac}`,
      fail: (err) => {
        console.error('导航失败:', err);
        wx.showToast({
          title: '页面跳转失败',
          icon: 'none'
        });
      }
    });
  }
});