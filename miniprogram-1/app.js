// app.js - 微信小程序全局配置

const envConfig = require('./config/env.js');
const { request, post, get, put, delete: del } = require('./utils/request.js');

App({
  globalData: {
    // API 相关
    apiUrl: envConfig.getApiUrl(),
    config: null,  // 完整的服务器配置
    
    // 用户信息
    user: null,
    token: null,
    
    // 其他
    videoStreamUrl: '',
    imageUrl: ''
  },

  async onLaunch() {
    console.log('应用启动中...');
    
    // 1. 初始化配置 - 从服务器获取
    console.log('第1步: 初始化配置...');
    const configReady = await envConfig.initConfig();
    
    // 保存配置到 globalData
    this.globalData.config = envConfig.getConfig();
    this.globalData.apiUrl = envConfig.getApiUrl();
    
    console.log('API URL:', this.globalData.apiUrl);
    
    if (configReady) {
      console.log('服务器配置已加载');
    } else {
      console.log('使用本地/缓存配置');
    }
    
    // 2. 尝试恢复用户会话
    console.log('第2步: 恢复用户会话...');
    try {
      const token = wx.getStorageSync('token');
      const user = wx.getStorageSync('user');
      if (token) {
        this.globalData.token = token;
        this.globalData.user = user;
        console.log('用户会话已恢复');
      }
    } catch (e) {
      console.warn('Failed to restore session:', e);
    }
    
    // 3. 设置图片相关地址
    const config = this.globalData.config;
    if (config && config.servers) {
      this.globalData.videoStreamUrl = config.servers.video_stream || '';
      this.globalData.imageUrl = this.globalData.apiUrl + '/static/';
    }
    
    console.log('应用启动完成');
    console.log('当前配置:', this.globalData.config);
  },

  // 网络请求便捷方法（从 utils/request 导出）
  request: request,
  post: post,
  get: get,
  put: put,
  delete: del,
  
  /**
   * 切换 API 环境 (开发/测试/生产)
   * @param {string} env - 环境名称
   */
  setApiEnv: function(env) {
    envConfig.setEnv(env);
    this.globalData.apiUrl = envConfig.getApiUrl();
    console.log('✏️ API 环境已切换:', env);
    console.log('新 API 地址:', this.globalData.apiUrl);
  },
  
  /**
   * 刷新配置 - 从服务器重新获取最新配置
   */
  async refreshConfig() {
    console.log('正在刷新配置...');
    const success = await envConfig.refreshConfig();
    
    if (success) {
      this.globalData.config = envConfig.getConfig();
      console.log('配置已刷新');
    } else {
      console.warn('配置刷新失败');
    }
    
    return success;
  },
  
  /**
   * 获取配置
   */
  getConfig: function() {
    return envConfig.getConfig();
  },
  
  /**
   * 获取配置中的某个值
   * 例如: app.getConfigValue('features.fingerprint')
   */
  getConfigValue: function(path, defaultValue) {
    return envConfig.getValue(path, defaultValue);
  }
})

