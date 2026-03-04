// pages/login/index.js
// 身份鉴权页 - 入口大门

const envConfig = require('../../config/env.js');

Page({
  data: {
    username: '',
    password: '',
    isLoggingIn: false,
    showPassword: false
  },

  onLoad: function (options) {
    // 检查本地是否有有效 token
    const token = wx.getStorageSync('token');
    if (token) {
      // 有 token 则直接跳转到控制台
      wx.switchTab({
        url: '/pages/console/index'
      });
    }
  },

  /**
   * 学号/工号输入
   */
  onUsernameInput: function(e) {
    this.setData({
      username: e.detail.value
    });
  },

  /**
   * 密码输入
   */
  onPasswordInput: function(e) {
    this.setData({
      password: e.detail.value
    });
  },

  /**
   * 切换密码可见性
   */
  togglePassword: function() {
    this.setData({
      showPassword: !this.data.showPassword
    });
  },

  /**
   * 微信登录
   * 流程（符合微信官方文档）：
   * 1. 调用 wx.login() 获取临时登录凭证 code（静默）
   * 2. 将 code 发送到后端
   * 3. 后端用 code 换取 openid 并生成 token
   * 4. 保存 token 并跳转
   */
  onWechatLogin: function() {
    if (this.data.isLoggingIn) return;

    const that = this;
    this.setData({ isLoggingIn: true });

    wx.showLoading({
      title: '登录中...',
      mask: true
    });

    console.log(' 开始调用 wx.login ');

    // 调用 wx.login() 获取临时登录凭证 code
    wx.login({
      timeout: 10000,
      success: function(res) {
        console.log(' wx.login 成功 ', res);

        if (res.code) {
          const username = (that.data.username || '').trim();
          const password = (that.data.password || '').trim();
          that.requestLogin(res.code, username, password);
        } else {
          wx.hideLoading();
          that.setData({ isLoggingIn: false });
          console.error('wx.login 失败：', res.errMsg);
          wx.showToast({
            title: '微信登录失败：' + res.errMsg,
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: function(err) {
        console.error(' wx.login 失败 ', err);
        wx.hideLoading();
        that.setData({ isLoggingIn: false });
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 账号密码登录
   */
  onPasswordLogin: function() {
    const username = this.data.username.trim();
    const password = this.data.password.trim();

    if (!username) {
      wx.showToast({
        title: '请输入学号/工号',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    if (!password) {
      wx.showToast({
        title: '请输入密码',
        icon: 'none',
        duration: 2000
      });
      return;
    }

    if (this.data.isLoggingIn) return;

    const that = this;
    this.setData({ isLoggingIn: true });

    wx.showLoading({
      title: '登录中...',
      mask: true
    });

    console.log(' 账号密码登录 ', username);

    const apiUrl = envConfig.getApiUrl();

    // 调用后端账号密码登录接口
    wx.request({
      url: apiUrl + '/login',
      method: 'POST',
      data: {
        login_type: 'password',
        username: username,
        password: password
      },
      header: {
        'Content-Type': 'application/json'
      },
      success: function(res) {
        console.log(' 后端登录响应 ', res);

        if (res.statusCode === 200 && res.data && res.data.success) {
          // 登录成功
          // 关键：先清除旧数据，再保存新数据，防止账号切换时数据混乱
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          
          // 关键修复：安全访问响应数据 res.data.data
          // 原因：防止响应格式异常导致 undefined 错误
          // 示例场景：
          //   修复前：const token = res.data.data.token  (若data不存在则报错)
          //   修复后：const responseData = res.data.data || {}  (安全)
          const responseData = res.data.data || {};
          const token = responseData.token;
          const userInfo = responseData.user || {};
          
          // 额外的数据有效性检查：确保token不为空
          // 防线说明：
          // 1. 后端返回success=true，但token为空（异常情况）
          // 2. 如果不检查直接保存空token，后续API调用会失败
          // 3. 提前检查可以提供更好的错误提示
          if (!token) {
            console.error('后端返回的 token 为空');
            wx.hideLoading();
            wx.showToast({
              title: '登录失败：响应数据异常',
              icon: 'none',
              duration: 2000
            });
            that.setData({ isLoggingIn: false });
            return;
          }
          
          // 保存token和用户信息到本地存储
          // token用于后续API认证（Authorization: Bearer {token}）
          // userInfo用于展示用户信息（姓名、学号等）
          wx.setStorageSync('token', token);
          wx.setStorageSync('userInfo', userInfo);

          console.log('登录成功，数据已更新');
          console.log('Token:', token.substring(0, 50) + '...');  // 仅打印前50个字符（保护敏感信息）
          console.log('用户信息:', userInfo);

          // 关闭 loading 动画
          wx.hideLoading();

          // 显示成功提示
          wx.showToast({
            title: '登录成功',
            icon: 'success',
            duration: 1500
          });

          // 延迟后跳转到控制台，给用户查看成功提示的时间
          setTimeout(function() {
            console.log('执行跳转');
            wx.switchTab({
              url: '/pages/console/index'
            });
          }, 1500);

        } else {
          // 后端返回失败（如：账号或密码错误）
          wx.hideLoading();
          console.error('后端返回失败:', res);
          wx.showToast({
            title: res.data?.message || '账号或密码错误',
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: function(err) {
        console.error(' 请求后端失败 ', err);
        wx.hideLoading();
        wx.showToast({
          title: '网络错误，请检查后端服务',
          icon: 'none',
          duration: 2000
        });
      },
      complete: function() {
        that.setData({ isLoggingIn: false });
      }
    });
  },

  /**
   * 通用登录请求处理（微信登录）
   */
  /**
   * 微信登录请求处理函数
   * @param {string} code - 微信临时登录凭证（由wx.login()获取）
   * @param {string} username - 可选，学号/工号（用于绑定现有账号）
   * @param {string} password - 可选，密码（用于绑定现有账号）
   * 
   * 微信登录流程：
   * 1. 前端调用 wx.login() → 获取临时code（只能用一次，5分钟内有效）
   * 2. 将code发送到后端 POST /api/login?login_type=wechat
   * 3. 后端调用微信API验证code → 获取openid
   * 4. 后端查询/创建用户 → 签发JWT token
   * 5. 前端保存token到本地存储 → 跳转到应用主页面
   */
  requestLogin: function(code, username, password) {
    const that = this;
    const apiUrl = envConfig.getApiUrl();

    console.log(' 请求后端登录 ', apiUrl + '/login');

    wx.request({
      url: apiUrl + '/login',
      method: 'POST',
      data: {
        login_type: 'wechat',  // 告知后端使用微信登录流程
        code: code,            // 微信登录凭证
        username: username || '',  // 可选：用户名（用于绑定）
        password: password || ''    // 可选：密码（用于绑定）
      },
      header: {
        'Content-Type': 'application/json'
      },
      success: function(res) {
        console.log('后端登录响应', res);

        if (res.statusCode === 200 && res.data && res.data.success) {
          // 微信登录成功
          // 关键：先清除旧数据，再保存新数据，防止账号切换时数据混乱
          wx.removeStorageSync('token');
          wx.removeStorageSync('userInfo');
          
          // 关键修复：安全访问响应数据 res.data.data
          // 防止响应格式异常导致 undefined 错误
          const responseData = res.data.data || {};
          const token = responseData.token;
          const userInfo = responseData.user || {};
          
          // 验证token有效性
          // 重要：token是后续所有API调用的凭证，不能为空
          if (!token) {
            console.error('后端返回的 token 为空');
            wx.hideLoading();
            wx.showToast({
              title: '登录失败：响应数据异常',
              icon: 'none',
              duration: 2000
            });
            that.setData({ isLoggingIn: false });
            return;
          }
          
          // 保存认证凭证
          wx.setStorageSync('token', token);
          wx.setStorageSync('userInfo', userInfo);

          console.log(' 微信登录成功，数据已更新 ');
          console.log('Token:', token.substring(0, 50) + '...');  // 仅打印前50个字符
          console.log('用户信息:', userInfo);

          // 关闭loading动画
          wx.hideLoading();

          // 显示成功提示
          wx.showToast({
            title: '登录成功',
            icon: 'success',
            duration: 1500
          });

          // 延迟后跳转到应用主页面
          setTimeout(function() {
            console.log(' 执行跳转 ');
            wx.switchTab({
              url: '/pages/console/index'
            });
          }, 1500);

        } else {
          wx.hideLoading();
          console.error('后端返回失败:', res);
          const isServerError = res.statusCode >= 500;
          wx.showToast({
            title: isServerError ? '微信登录异常，请改用账号密码登录' : (res.data?.message || '登录失败'),
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: function(err) {
        console.error(' 请求后端失败 ', err);
        wx.hideLoading();
        wx.showToast({
          title: '网络错误，请检查后端服务',
          icon: 'none',
          duration: 2000
        });
      },
      complete: function() {
        that.setData({ isLoggingIn: false });
      }
    });
  },

  onShow: function() {
    // 每次页面显示时检查 token
    const token = wx.getStorageSync('token');
    if (token) {
      wx.switchTab({
        url: '/pages/console/index'
      });
    }
  }
});
