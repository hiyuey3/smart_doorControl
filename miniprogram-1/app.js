// 小程序入口：负责全局配置、会话恢复和通用请求方法。

const envConfig = require('./config/env.js');
const { request, post, get, put, delete: del } = require('./utils/request.js');

App({
  // 全局状态，页面可通过 getApp().globalData 读取。
  globalData: {
    // API 配置
    apiUrl: envConfig.getApiUrl(),
    config: null,
    
    // 登录态
    user: null,
    token: null,
    
    // 资源地址
    videoStreamUrl: '',
    imageUrl: ''
  },

  /**
   * 冷启动初始化：拉取配置、恢复登录态、设置资源地址。
   */
  async onLaunch() {
    console.log('应用启动中...');
    
    // 先加载配置
    console.log('第1步: 初始化配置...');
    const configReady = await envConfig.initConfig();
    
    // 保存配置，供页面读取
    this.globalData.config = envConfig.getConfig();
    this.globalData.apiUrl = envConfig.getApiUrl();
    
    console.log('API URL:', this.globalData.apiUrl);
    
    if (configReady) {
      console.log('服务器配置已加载');
    } else {
      console.log('使用本地/缓存配置');
    }
    
    // 尝试恢复本地登录态
    console.log('第2步: 恢复用户会话...');
    try {
      const token = wx.getStorageSync('token');
      const user = wx.getStorageSync('user');
      
      if (token) {
        // 本地有 token，沿用当前会话
        this.globalData.token = token;
        this.globalData.user = user;
        console.log('用户会话已恢复，可直接进入首页');
      } else {
        // 没有 token，后续按页面逻辑跳转登录
        console.log('无用户会话，会自动跳转到登录页');
      }
    } catch (e) {
      console.warn('Failed to restore session:', e);
    }
    
    // 设置资源访问地址
    const config = this.globalData.config;
    if (config && config.servers) {
      this.globalData.videoStreamUrl = config.servers.video_stream || '';
      this.globalData.imageUrl = this.globalData.apiUrl + '/static/';
    }
    
    console.log('应用启动完成');
    console.log('当前配置:', this.globalData.config);
  },

  /**
   * 应用从后台进入前台时的生命周期钩子
   * 
   * 调用时机：
   * - 用户在后台运行时切回小程序
   * - 扫码打开小程序时
   * - 从分享卡片打开小程序时
   */
  onShow(options) {
    console.log('应用进入前台');
    // 这里可以做一些业务逻辑，如刷新数据、检查登录状态等
  },

  /**
   * 应用进入后台时的生命周期钩子
   * 
   * 调用时机：
   * - 用户点击左上角返回按钮
   * - 按下设备 Home 键
   * - 从小程序跳转到其他应用
   */
  onHide() {
    console.log('应用进入后台');
    // 清理资源（如定时器、录音等）
  },

  // 导出通用请求方法，页面可直接调用 getApp().post/get 等。
  request: request,
  post: post,
  get: get,
  put: put,
  delete: del,
  
  /**
   * 切换 API 环境（dev/test/prod）。
   */
  setApiEnv: function(env) {
    envConfig.setEnv(env);
    this.globalData.apiUrl = envConfig.getApiUrl();
    console.log('API 环境已切换:', env);
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

