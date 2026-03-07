// pages/settings/config.js
// 个人中心与账号安全

const envConfig = require('../../config/env.js');
const pageHelper = require('../../utils/page-helper.js');

Page({
  data: {
    userInfo: {
      id: '',
      username: '',
      name: '',
      role: ''
    },
    wechatBindingStatus: {
      is_bound: false,
      openid: null
    },
    showPasswordModal: false,
    passwordLoading: false,
    passwordForm: {
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    },
    // 最近动作标签和数据
    activeTab: 'access',
    accessLogs: [],
    applicationLogs: [],
    unbindLoading: false
  },

  onLoad(options) {
    console.log(' 个人中心页 onLoad ');
    if (!pageHelper.ensureLogin()) {
      return;
    }
    this.loadUserInfo();
    this.loadAccessLogs();
    this.loadApplicationLogs();
  },

  onShow() {
    console.log(' 个人中心页 onShow ');
    // 强制从后端重新获取最新用户信息（确保登录切换后能同步）
    const token = wx.getStorageSync('token');
    if (token) {
      this.loadUserInfoFromBackend();
    }
    this.loadAccessLogs();
    this.loadApplicationLogs();
  },

  /**
   * 从后端获取最新用户信息（不用本地缓存）
   */
  loadUserInfoFromBackend() {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');

    if (!token) {
      return;
    }

    wx.request({
      url: apiUrl + '/user',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + token
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.success) {
          const responseData = res.data.data || {};
          const user = responseData.user || {};
          const wechatData = responseData.wechat || {};
          
          // 更新用户信息到本地存储
          wx.setStorageSync('userInfo', user);
          
          // 更新页面数据
          this.setData({
            userInfo: {
              id: user.id || '',
              username: user.username || '未知',
              name: user.name || '未知',
              role: user.role || ''
            },
            wechatBindingStatus: {
              is_bound: wechatData.is_bound || false,
              openid: wechatData.openid || null
            }
          });
          console.log('用户信息已更新:', this.data.userInfo);
        } else if (res.statusCode === 401) {
          console.warn('登录已过期');
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
        }
      },
      fail: (err) => {
        console.error('从后端获取用户信息失败:', err);
      }
    });
  },

  loadUserInfo() {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');

    // 优先从本地存储获取
    const cachedUserInfo = wx.getStorageSync('userInfo') || {};
    this.setData({
      userInfo: {
        id: cachedUserInfo.id || '',
        username: cachedUserInfo.username || '未知',
        name: cachedUserInfo.name || '未知',
        role: cachedUserInfo.role || ''
      }
    });

    // 如果有 token，从后端实时获取最新信息
    if (token) {
      wx.request({
        url: apiUrl + '/user',
        method: 'GET',
        header: {
          'Authorization': 'Bearer ' + token
        },
        success: (res) => {
          if (res.statusCode === 200 && res.data && res.data.success) {
            const responseData = res.data.data || {};
            const user = responseData.user || {};
            const wechatData = responseData.wechat || {};
            
            this.setData({
              userInfo: {
                id: user.id || '',
                username: user.username || '未知',
                name: user.name || '未知',
                role: user.role || ''
              },
              wechatBindingStatus: {
                is_bound: wechatData.is_bound || false,
                openid: wechatData.openid || null
              }
            });
            console.log(' 用户信息 ', this.data.userInfo);
            console.log(' 微信绑定状态 ', this.data.wechatBindingStatus);
          } else if (res.statusCode === 401) {
            console.warn('登录已过期');
            wx.removeStorageSync('token');
          }
        },
        fail: (err) => {
          console.error('获取用户信息失败', err);
        }
      });
    }
  },

  /**
   * 处理微信状态徽章点击：已绑定则解绑，未绑定则绑定
   */
  handleWechatAction() {
    if (this.data.wechatBindingStatus.is_bound) {
      // 已绑定 -> 解绑
      this.onUnbindWechat();
    } else {
      // 未绑定 -> 绑定
      this.onBindWechat();
    }
  },

  onBindWechat() {
    wx.showModal({
      title: '绑定微信',
      content: '将使用微信账号与当前账号绑定，绑定后可用微信快速登录。',
      confirmText: '开始绑定',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.performBindWechat();
        }
      }
    });
  },

  performBindWechat() {
    wx.showLoading({
      title: '获取微信授权...',
      mask: true
    });

    wx.login({
      timeout: 10000,
      success: (res) => {
        if (res.code) {
          this.requestBindWechat(res.code);
        } else {
          wx.hideLoading();
          wx.showToast({
            title: '微信授权失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('wx.login 失败', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 向后端提交微信绑定请求
   * @param {string} code - 微信登录凭证（由wx.login()生成，5分钟有效）
   */
  requestBindWechat(code) {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');

    wx.request({
      url: apiUrl + '/user',
      method: 'PUT',
      data: { 
        action: 'bind_wechat',
        code: code 
      },
      header: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        wx.hideLoading();
        console.log(' 微信绑定响应 ', res);

        if (res.statusCode === 200 && res.data && res.data.success) {
          //  绑定成功
          // 使用兜底对象，避免响应字段缺失时报错
          const responseData = res.data.data || {};
          
          // 更新绑定状态展示
          this.setData({
            wechatBindingStatus: {
              // 后端未返回 is_bound 时，按成功分支视为已绑定
              is_bound: responseData.is_bound !== undefined ? responseData.is_bound : true,
              // openid 仅用于展示
              openid: responseData.openid || null
            }
          });
          
          // 显示成功提示
          wx.showToast({
            title: '微信绑定成功',
            icon: 'success',
            duration: 1500
          });
        } else if (res.statusCode === 400) {
          // 客户端错误（如已经绑定过微信）
          wx.showToast({
            title: res.data?.message || '已绑定微信',
            icon: 'none',
            duration: 1500
          });
        } else if (res.statusCode === 401) {
          // 认证失败（token 过期）
          wx.removeStorageSync('token');
          wx.showToast({
            title: '登录已过期',
            icon: 'none'
          });
          // 重定向到登录页
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/login/index'
            });
          }, 1500);
        } else {
          // 其他错误（例如 5xx 服务器错误）
          wx.showToast({
            title: res.data?.message || '绑定失败',
            icon: 'none',
            duration: 1500
          });
        }
      },
      fail: (err) => {
        // 网络错误（无法连接到后端）
        wx.hideLoading();
        console.error(' 绑定网络错误 ', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none',
          duration: 1500
        });
      }
    });
  },

  onUnbindWechat() {
    wx.showModal({
      title: '解绑微信',
      content: '确定要解绑微信账号吗？解绑后需要重新绑定新的微信才能使用微信登录。',
      confirmText: '确定解绑',
      cancelText: '取消',
      confirmColor: '#ff4c4c',
      success: (res) => {
        if (res.confirm) {
          this.performUnbindWechat();
        }
      }
    });
  },

  performUnbindWechat() {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');

    if (!token) {
      wx.showToast({
        title: '未登录',
        icon: 'none'
      });
      return;
    }

    this.setData({ unbindLoading: true });

    wx.showLoading({
      title: '解绑中...',
      mask: true
    });

    wx.request({
      url: apiUrl + '/user',
      method: 'PUT',
      data: {
        action: 'unbind_wechat'
      },
      header: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        wx.hideLoading();
        console.log(' 微信解绑响应 ', res);

        if (res.statusCode === 200 && res.data && res.data.success) {
          this.setData({
            wechatBindingStatus: {
              is_bound: false,
              openid: null
            }
          });
          pageHelper.showSuccess('微信解绑成功', 1500);
        } else if (res.statusCode === 400) {
          wx.showToast({
            title: '未绑定微信',
            icon: 'none',
            duration: 1500
          });
        } else if (res.statusCode === 401) {
          wx.removeStorageSync('token');
          wx.showToast({
            title: '登录已过期',
            icon: 'none'
          });
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/login/index'
            });
          }, 1500);
        } else {
          wx.showToast({
            title: res.data.message || '解绑失败',
            icon: 'none',
            duration: 1500
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error(' 解绑网络错误 ', err);
        pageHelper.showError('网络错误', 1500);
      },
      complete: () => {
        this.setData({ unbindLoading: false });
      }
    });
  },

  // 管理员导航到成员管理页面
  navigateToMemberManage() {
    wx.navigateTo({
      url: '/pages/users/manage',
      success: () => {
        console.log('成功导航到成员管理页面');
      },
      fail: () => {
        wx.showToast({
          title: '页面跳转失败',
          icon: 'error'
        });
      }
    });
  },

  onShowChangePassword() {
    this.setData({
      showPasswordModal: true,
      passwordForm: {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      }
    });
  },

  onHideChangePassword() {
    this.setData({
      showPasswordModal: false,
      passwordLoading: false,
      passwordForm: {
        oldPassword: '',
        newPassword: '',
        confirmPassword: ''
      }
    });
  },

  stopPropagation() {
  },

  onOldPasswordInput(e) {
    this.setData({
      'passwordForm.oldPassword': e.detail.value || ''
    });
  },

  onNewPasswordInput(e) {
    this.setData({
      'passwordForm.newPassword': e.detail.value || ''
    });
  },

  onConfirmPasswordInput(e) {
    this.setData({
      'passwordForm.confirmPassword': e.detail.value || ''
    });
  },

  onSubmitChangePassword() {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');
    const { oldPassword, newPassword, confirmPassword } = this.data.passwordForm;

    if (!token) {
      pageHelper.showError('未登录', 1500);
      return;
    }

    if (!newPassword || !confirmPassword) {
      pageHelper.showError('请填写完整密码信息', 1800);
      return;
    }

    if (newPassword.length < 6) {
      pageHelper.showError('新密码至少 6 位', 1800);
      return;
    }

    if (newPassword !== confirmPassword) {
      pageHelper.showError('两次输入的新密码不一致', 1800);
      return;
    }

    this.setData({ passwordLoading: true });

    wx.request({
      url: apiUrl + '/user',
      method: 'PUT',
      data: {
        action: 'change_password',
        old_password: oldPassword,
        new_password: newPassword
      },
      header: {
        'Authorization': 'Bearer ' + token,
        'Content-Type': 'application/json'
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data && res.data.success) {
          pageHelper.showSuccess('密码修改成功', 1500);
          this.onHideChangePassword();
          return;
        }

        if (res.statusCode === 401) {
          wx.removeStorageSync('token');
          wx.showToast({
            title: '登录已过期',
            icon: 'none'
          });
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/login/index'
            });
          }, 1500);
          return;
        }

        pageHelper.showError((res.data && res.data.message) || '修改密码失败', 1800);
      },
      fail: (err) => {
        console.error('修改密码网络错误:', err);
        pageHelper.showError('网络错误', 1500);
      },
      complete: () => {
        this.setData({ passwordLoading: false });
      }
    });
  },

  onLogout() {
    wx.showModal({
      title: '退出登录',
      content: '确定要退出登录吗？',
      confirmText: '退出',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          // 清除本地存储的 token 和用户信息
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          
          wx.showToast({
            title: '已退出登录',
            icon: 'success',
            duration: 1500
          });
          
          // 延迟后重定向到登录页
          setTimeout(() => {
            wx.redirectTo({
              url: '/pages/login/index'
            });
          }, 1500);
        }
      }
    });
  },

  /**
   * 切换标签
   */
  switchTab(e) {
    const tab = e.currentTarget.dataset.tab;
    if (tab === this.data.activeTab) return;
    
    this.setData({
      activeTab: tab
    });
  },

  /**
   * 加载访问记录
   */
  loadAccessLogs() {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');

    if (!token) {
      return;
    }

    wx.request({
      url: apiUrl + '/logs?page=1&per_page=5',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + token
      },
      success: (res) => {
        console.log(' 获取访问记录 ', res);
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          const logs = res.data.data || [];
          
          // 格式化时间和方法
          logs.forEach(log => {
            if (log.create_time) {
              log.create_time = this.formatTime(log.create_time);
            }
            log.methodText = this.getMethodText(log.unlock_method);
          });
          
          this.setData({
            accessLogs: logs
          });
        }
      },
      fail: (err) => {
        console.error('加载访问记录失败:', err);
      }
    });
  },

  /**
   * 加载申请记录
   */
  loadApplicationLogs() {
    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');

    if (!token) {
      return;
    }

    wx.request({
      url: apiUrl + '/user/applications',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + token
      },
      success: (res) => {
        console.log(' 获取申请记录 ', res);
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          const applications = res.data.data || [];
          
          // 格式化时间，最多显示 5 条
          applications.forEach(app => {
            if (app.created_at) {
              app.created_at = this.formatTime(app.created_at);
            }
          });
          
          const recentApplications = applications.slice(0, 5);
          
          this.setData({
            applicationLogs: recentApplications
          });
        }
      },
      fail: (err) => {
        console.error('加载申请记录失败:', err);
      }
    });
  },

  /**
   * 获取解锁方法的文字描述
   */
  getMethodText(method) {
    const methodMap = {
      'face': '人脸识别',
      'fingerprint': '指纹识别',
      'nfc': 'NFC 卡',
      'qrcode': '二维码',
      'password': '密码',
      'wechat': '微信',
      'remote': '远程开启'
    };
    return methodMap[method] || method || '未知';
  },

  /**
   * 加载我的申请记录（仅学生可见）
   */
  loadApplications() {
    const userInfo = wx.getStorageSync('userInfo') || {};
    
    // 只有学生才需要加载申请记录
    if (userInfo.role !== 'student') {
      return;
    }

    const apiUrl = envConfig.getApiUrl();
    const token = wx.getStorageSync('token');

    if (!token) {
      return;
    }

    wx.request({
      url: apiUrl + '/user/applications',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + token
      },
      success: (res) => {
        console.log(' 获取申请记录 ', res);
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          const applications = res.data.data || [];
          
          // 格式化时间
          applications.forEach(app => {
            if (app.created_at) {
              app.created_at = this.formatTime(app.created_at);
            }
          });
          
          // 按时间倒序排列，最多显示 5 条
          applications.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
          const recentApplications = applications.slice(0, 5);
          
          this.setData({
            applications: recentApplications
          });
        }
      },
      fail: (err) => {
        console.error('加载申请记录失败:', err);
      }
    });
  },

  /**
   * 格式化时间
   */
  formatTime(isoString) {
    if (!isoString) return '';
    
    const date = new Date(isoString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    
    return `${month}-${day} ${hour}:${minute}`;
  }
});