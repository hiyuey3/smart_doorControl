// 全局请求封装：统一处理 Token 和 401 跳转。

const envConfig = require('../config/env.js');

/**
 * 封装的 HTTP 请求工具函数
 * @param {Object} options - 请求配置选项
 * @param {string} options.url - 请求 URL（相对路径，需要以 / 开头）
 * @param {string} options.method - 请求方法（GET/POST 等，默认 GET）
 * @param {Object} options.data - 请求数据
 * @param {Object} options.header - 自定义请求头
 * @returns {Promise} - 返回 Promise 对象，resolve(response) 或 reject(error)
 */
const request = (options) => {
  return new Promise((resolve, reject) => {
    // 读取本地 token
    const token = wx.getStorageSync('token');

    // 组装请求头
    const header = {
      'Content-Type': 'application/json',
      ...options.header
    };

    // 自动携带 token
    if (token) {
      header['Authorization'] = `Bearer ${token}`;
    }

    // 获取 API 地址
    const apiUrl = envConfig.getApiUrl();

    // 调试日志：请求
    if (envConfig.isDebug()) {
      console.log('API Request:', {
        url: apiUrl + options.url,
        method: options.method || 'GET',
        data: options.data
      });
    }

    // 发起请求
    wx.request({
      url: apiUrl + options.url,
      method: options.method || 'GET',
      data: options.data,
      header: header,
      timeout: envConfig.getConfig().timeout,
      success: (res) => {
        // 调试日志：响应
        if (envConfig.isDebug()) {
          console.log('API Response:', {
            url: apiUrl + options.url,
            statusCode: res.statusCode,
            data: res.data
          });
        }

        // 登录失效时清理会话并跳转登录页
        if (res.statusCode === 401) {
          wx.removeStorageSync('token');
          wx.removeStorageSync('user');

          wx.showToast({
            title: '登录已过期，请重新登录',
            icon: 'none',
            duration: 2000
          });

          // 延迟跳转，避免短时间重复导航
          setTimeout(() => {
            wx.navigateTo({
              url: '/pages/login/index'
            });
          }, 500);

          // 拒绝 Promise，传递错误信息
          reject(new Error('Unauthorized: Token expired'));
          return;
        }

        // 检查服务器返回的 success 字段
        if (res.data && res.data.success === false) {
          reject(new Error(res.data.message || 'API returned error'));
          return;
        }

        // 解析成功，返回响应数据
        resolve(res.data || res);
      },
      fail: (err) => {
        // 请求失败，拒绝 Promise
        console.error('网络请求失败:', err);
        
        // 显示错误提示
        let errorMessage = '网络连接失败';
        if (err.errMsg && err.errMsg.includes('timeout')) {
          errorMessage = '请求超时，请检查网络';
        }
        
        wx.showToast({
          title: errorMessage,
          icon: 'none',
          duration: 2000
        });

        reject(err);
      },
      complete: () => {
        // 请求完成（成功或失败都会执行）
      }
    });
  });
};

// 便捷方法
const get = (url, data = {}, header = {}) => {
  return request({
    url,
    method: 'GET',
    data,
    header
  });
};

const post = (url, data = {}, header = {}) => {
  return request({
    url,
    method: 'POST',
    data,
    header
  });
};

const put = (url, data = {}, header = {}) => {
  return request({
    url,
    method: 'PUT',
    data,
    header
  });
};

const del = (url, data = {}, header = {}) => {
  return request({
    url,
    method: 'DELETE',
    data,
    header
  });
};

// 导出 request 函数和便捷方法
module.exports = {
  request: request,
  get: get,
  post: post,
  put: put,
  delete: del
};
