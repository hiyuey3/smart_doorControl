// app.js - 微信小程序全局应用配置和初始化
// 
// 功能职责：
// 1. 全局应用生命周期管理（onLaunch、onShow、onHide）
// 2. 初始化 API 地址、用户信息等全局数据
// 3. 恢复用户登录会话（Token 机制）
// 4. 为所有页面提供便捷的网络请求方法

const envConfig = require('./config/env.js');
const { request, post, get, put, delete: del } = require('./utils/request.js');

App({
  // 全局数据对象
  // 所有页面可通过 getApp().globalData 访问
  globalData: {
    // API 相关配置
    apiUrl: envConfig.getApiUrl(),  // 后端 API 服务器地址（可动态切换）
    config: null,                    // 从服务器获取的完整配置
    
    // 用户会话信息
    user: null,                       // 当前登录用户信息
    token: null,                      // 用户认证令牌（JWT Token）
    
    // 其他资源地址
    videoStreamUrl: '',               // 视频流地址（用于实时视频）
    imageUrl: ''                      // 图片资源地址
  },

  /**
   * 应用启动生命周期钩子
   * 
   * 调用时机：
   * - 小程序首次启动时调用
   * - 冷启动（完全退出后重新打开）
   * - 不会在用户切换到后台再切回时调用
   * 
   * 初始化步骤：
   * 1. 初始化全局配置（API 地址等）
   * 2. 恢复用户登录会话（如果存在）
   * 3. 设置图片和视频流地址
   */
  async onLaunch() {
    console.log('应用启动中...');
    
    // 步骤1：初始化配置
    // 从服务器获取应用配置（API 地址、超时时间等）
    console.log('第1步: 初始化配置...');
    const configReady = await envConfig.initConfig();
    
    // 保存配置到全局数据（供所有页面使用）
    this.globalData.config = envConfig.getConfig();
    this.globalData.apiUrl = envConfig.getApiUrl();
    
    console.log('API URL:', this.globalData.apiUrl);
    
    if (configReady) {
      console.log('服务器配置已加载');
    } else {
      console.log('使用本地/缓存配置');
    }
    
    // 步骤2：尝试恢复用户会话
    // 检查本地存储中是否有用户登录信息
    console.log('第2步: 恢复用户会话...');
    try {
      const token = wx.getStorageSync('token');
      const user = wx.getStorageSync('user');
      
      if (token) {
        // 本地存储中有 Token，说明用户之前登录过
        this.globalData.token = token;
        this.globalData.user = user;
        console.log('用户会话已恢复，可直接进入首页');
      } else {
        // 没有 Token，需要到登录页
        console.log('无用户会话，会自动跳转到登录页');
      }
    } catch (e) {
      console.warn('Failed to restore session:', e);
    }
    
    // 步骤3：设置图片和视频流地址
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

  // 导出便捷的网络请求方法
  // 供所有页面直接使用：getApp().post()、getApp().get() 等
  // 这些方法会自动处理 Token、错误检查、登录过期等
  request: request,
  post: post,
  get: get,
  put: put,
  delete: del,
  
  /**
   * 切换 API 环境 (开发/测试/生产)
   * 
   * 用途：便于开发者快速切换服务器地址
   * 调用方式：getApp().setApiEnv('dev')
   * 
   * 参数：
   * - 'dev'：本地开发环境
   * - 'test'：测试环境
   * - 'prod'：生产环境
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

