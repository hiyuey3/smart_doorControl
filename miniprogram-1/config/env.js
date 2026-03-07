/**
 * 环境与配置管理。
 * 启动时先拉取服务端配置；失败时回退本地缓存或默认值。
 */

// 本地默认配置（服务端不可用时回退）
const CONFIG_VERSION = '1.1.0';  // 用于控制缓存失效

const DEFAULT_LOCAL_CONFIG = {
  version: CONFIG_VERSION,
  // API 配置
  api: {
    // 启动阶段用于获取远端配置
    baseUrl: 'https://dev.api.5i03.cn/api',
    timeout: 10000,
    debug: true,
    retryCount: 3
  },
  
  // 应用定义
  app: {
    name: '门禁系统',
    version: '1.0.0'
  },
  
  // 功能开关
  features: {
    fingerprint: true,
    nfc: true,
    local_unlock: true,
    remote_unlock: true,
    capture_image: true,
    activity_log: true
  },
  
  // 第三方服务
  servers: {
    // 快照获取方式：
    // 方式1（生产常用）：直连云端中继 URL
    //   video_stream: 'https://relay.example.com/snapshot'
    // 方式2（当前）：通过后端 API 代理，便于做鉴权和缓存
    //   video_stream: 'https://dev.api.5i03.cn/api/device/snapshot'
    video_stream: 'https://dev.api.5i03.cn/api/device/snapshot',
    mqtt: {
      broker: 'mqtt.5i03.cn',
      port: 1883
    }
  }
};

// 全局配置缓存
let GLOBAL_CONFIG = { ...DEFAULT_LOCAL_CONFIG };

// 环境检测
const getEnv = () => {
  try {
    const savedEnv = wx.getStorageSync('app_env');
    if (savedEnv) {
      return savedEnv;
    }
  } catch (e) {
    console.warn('Failed to get saved env:', e);
  }
  return 'development';
};

const ENV = getEnv();

// 导出函数
module.exports = {
  /**
   * 获取当前环境
   */
  getEnv: () => ENV,
  
  /**
   * 设置环境 (开发/测试/生产)
   */
  setEnv: (env) => {
    try {
      wx.setStorageSync('app_env', env);
      console.log('Environment switched to:', env);
    } catch (e) {
      console.error('Failed to set env:', e);
    }
  },
  
  /**
   * 获取当前配置对象
   */
  getConfig: () => {
    return GLOBAL_CONFIG;
  },
  
  /**
   * 获取 API 基础 URL
   */
  getApiUrl: () => {
    return GLOBAL_CONFIG.api.baseUrl;
  },
  
  /**
    * 获取 API 配置
   */
  getApiConfig: () => {
    return {
      baseUrl: GLOBAL_CONFIG.api.baseUrl,
      timeout: GLOBAL_CONFIG.api.timeout,
      debug: GLOBAL_CONFIG.api.debug,
      retryCount: GLOBAL_CONFIG.api.retryCount
    };
  },
  
  /**
   * 获取是否调试模式
   */
  isDebug: () => {
    return GLOBAL_CONFIG.api.debug;
  },
  
  /**
   * 获取指定路径的配置值
   * 例如: getValue('features.fingerprint') -> true
   */
  getValue: (path, defaultValue = null) => {
    const keys = path.split('.');
    let value = GLOBAL_CONFIG;
    
    for (const key of keys) {
      if (value && typeof value === 'object' && key in value) {
        value = value[key];
      } else {
        return defaultValue;
      }
    }
    
    return value;
  },
  
  /**
    * 初始化配置。
    * 建议在 App.onLaunch 中调用。
   */
  async initConfig() {
    try {
      console.log('[配置] 正在从服务器获取配置...');
      
      // 版本不一致时清理旧缓存
      try {
        const cachedConfig = wx.getStorageSync('app_config');
        if (cachedConfig && cachedConfig.version !== CONFIG_VERSION) {
          console.log('检测到配置版本更新，清除旧缓存');
          wx.removeStorageSync('app_config');
          wx.removeStorageSync('app_config_time');
        }
      } catch (e) {
        console.warn('检查缓存版本失败:', e);
      }
      
      const baseUrl = GLOBAL_CONFIG.api.baseUrl;
      const response = await module.exports.fetchConfig(baseUrl + '/config');
      
      if (response && response.success) {
        // 保留当前 baseUrl，避免被远端配置覆盖
        const originalBaseUrl = GLOBAL_CONFIG.api.baseUrl;
        
        // 合并服务端配置
        GLOBAL_CONFIG = {
          version: CONFIG_VERSION,
          ...GLOBAL_CONFIG,
          ...response.data,
          // 合并 api 字段并保留本地 baseUrl
          api: {
            ...GLOBAL_CONFIG.api,
            ...(response.data.api || {}),
            baseUrl: originalBaseUrl
          }
        };
        
        // 写入本地缓存
        try {
          wx.setStorageSync('app_config', GLOBAL_CONFIG);
          wx.setStorageSync('app_config_time', Date.now());
        } catch (e) {
          console.warn('Failed to cache config:', e);
        }
        
        console.log('服务器配置加载成功');
        console.log('配置内容:', GLOBAL_CONFIG);
        
        return true;
      }
    } catch (e) {
      console.warn('从服务器获取配置失败，使用本地缓存或默认配置', e);
      
      // 回退到本地缓存
      try {
        const cachedConfig = wx.getStorageSync('app_config');
        if (cachedConfig) {
          // 保留当前 baseUrl
          const originalBaseUrl = GLOBAL_CONFIG.api.baseUrl;
          
          GLOBAL_CONFIG = {
            version: CONFIG_VERSION,
            ...cachedConfig,
            // 缓存回读时也保持当前 baseUrl
            api: {
              ...(cachedConfig.api || {}),
              baseUrl: originalBaseUrl
            }
          };
          
          console.log('使用本地缓存配置');
          return true;
        }
      } catch (err) {
        console.warn('Failed to read cached config:', err);
      }
    }
    
    console.log('使用默认本地配置');
    return false;
  },
  
  /**
   * 发送配置获取请求（内部使用）
   */
  fetchConfig: (url) => {
    return new Promise((resolve, reject) => {
      wx.request({
        url: url,
        method: 'GET',
        timeout: 5000,
        success: (res) => {
          if (res.statusCode === 200) {
            resolve(res.data);
          } else {
            reject(new Error(`HTTP ${res.statusCode}`));
          }
        },
        fail: (err) => {
          reject(err);
        }
      });
    });
  },
  
  /**
   * 刷新配置 - 手动从服务器重新获取配置
   */
  async refreshConfig() {
    try {
      console.log('[刷新] 正在刷新服务器配置...');
      const success = await module.exports.initConfig();
      
      if (success) {
        console.log('配置刷新成功');
        // 广播配置更新事件
        wx.eventCenter?.emit('configUpdated', GLOBAL_CONFIG);
      } else {
        console.warn('配置刷新失败');
      }
      
      return success;
    } catch (e) {
      console.error('[Error] Config refresh error:', e);
      return false;
    }
  },
  
  /**
   * 获取本地默认配置
   */
  getDefaultConfig: () => {
    return { ...DEFAULT_LOCAL_CONFIG };
  },
  
  /**
   * 手动设置配置值（主要用于本地测试或偏好设置）
   */
  setConfigValue: (path, value) => {
    const keys = path.split('.');
    let config = GLOBAL_CONFIG;
    
    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i];
      if (!(key in config)) {
        config[key] = {};
      }
      config = config[key];
    }
    
    config[keys[keys.length - 1]] = value;
        console.log(`配置已更新: ${path} = ${value}`);
  }
};
