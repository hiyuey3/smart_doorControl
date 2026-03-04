// pages/users/manage.js
// 成员管理页 - 宿管/管理员功能
const envConfig = require('../../config/env.js');

Page({
  data: {
    currentTab: 0,           // 当前标签页：0=成员列表, 1=待审批
    members: [],             // 成员列表
    applications: [],        // 待审批申请列表
    pendingCount: 0,         // 待审批数量
    loading: false
  },

  onLoad(options) {
    // 检查用户角色
    const user = wx.getStorageSync('user');
    if (!user || user.role !== 'admin') {
      wx.showToast({
        title: '仅管理员可访问',
        icon: 'none',
        duration: 2000
      });
      setTimeout(() => {
        wx.navigateBack();
      }, 2000);
      return;
    }

    this.loadMembers();
    this.loadApplications();
  },

  onShow() {
    // 每次显示页面时刷新数据
    this.loadApplications();
  },

  onPullDownRefresh() {
    if (this.data.currentTab === 0) {
      this.loadMembers();
    } else {
      this.loadApplications();
    }
    wx.stopPullDownRefresh();
  },

  /**
   * 切换标签页
   */
  switchTab(e) {
    const index = parseInt(e.currentTarget.dataset.index);
    this.setData({
      currentTab: index
    });
  },

  loadMembers() {
    this.setData({ loading: true });

    getApp().request({
      url: '/users',
      method: 'GET'
    }).then(res => {
      if (res && res.statusCode === 200 && res.data && res.data.success) {
        this.setData({
          members: res.data.data || [],
          loading: false
        });
      }
    }).catch(err => {
      console.error('加载成员失败:', err);
      this.setData({ loading: false });
      wx.showToast({
        title: '网络错误',
        icon: 'none'
      });
    });
  },

  /**
   * 加载待审批申请列表
   */
  loadApplications() {
    const apiUrl = envConfig.getApiUrl();

    wx.request({
      url: apiUrl + '/admin/applications?status=pending',
      method: 'GET',
      header: {
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      success: (res) => {
        console.log(' 获取待审批列表 ', res);
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          const applications = res.data.data || [];
          
          // 格式化申请时间
          applications.forEach(app => {
            if (app.created_at) {
              app.created_at = this.formatTime(app.created_at);
            }
          });
          
          this.setData({
            applications: applications,
            pendingCount: applications.length
          });
        } else {
          wx.showToast({
            title: res.data?.message || '加载失败',
            icon: 'none'
          });
        }
      },
      fail: (err) => {
        console.error('加载申请列表失败:', err);
        wx.showToast({
          title: '网络错误',
          icon: 'none'
        });
      }
    });
  },

  /**
   * 处理批准操作
   */
  handleApprove(e) {
    const { id, name } = e.currentTarget.dataset;
    
    wx.showModal({
      title: '确认批准',
      content: `确定批准 ${name} 的设备绑定申请吗？`,
      confirmText: '批准',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.reviewApplication(id, 'approve');
        }
      }
    });
  },

  /**
   * 处理拒绝操作
   */
  handleReject(e) {
    const { id, name } = e.currentTarget.dataset;
    
    wx.showModal({
      title: '确认拒绝',
      content: `确定拒绝 ${name} 的设备绑定申请吗？`,
      confirmText: '拒绝',
      confirmColor: '#fa5151',
      cancelText: '取消',
      success: (res) => {
        if (res.confirm) {
          this.reviewApplication(id, 'reject');
        }
      }
    });
  },

  /**
   * 调用审批 API
   * @param {number} applicationId - 申请 ID
   * @param {string} action - 操作类型：'approve' 或 'reject'
   */
  reviewApplication(applicationId, action) {
    const apiUrl = envConfig.getApiUrl();

    wx.showLoading({
      title: action === 'approve' ? '正在批准...' : '正在拒绝...',
      mask: true
    });

    wx.request({
      url: apiUrl + '/admin/applications/' + applicationId,
      method: 'PUT',
      header: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + wx.getStorageSync('token')
      },
      data: {
        action: action,
        comment: action === 'approve' ? '已批准' : '已拒绝'
      },
      success: (res) => {
        wx.hideLoading();
        console.log(' 审批响应 ', res);
        
        if (res.statusCode === 200 && res.data && res.data.success) {
          wx.showToast({
            title: action === 'approve' ? '已批准' : '已拒绝',
            icon: 'success',
            duration: 2000
          });
          
          // 从列表中移除该申请
          const applications = this.data.applications.filter(app => app.id !== applicationId);
          this.setData({
            applications: applications,
            pendingCount: applications.length
          });
        } else {
          wx.showToast({
            title: res.data?.message || '操作失败',
            icon: 'none',
            duration: 2000
          });
        }
      },
      fail: (err) => {
        wx.hideLoading();
        console.error('审批请求失败:', err);
        wx.showToast({
          title: '网络错误，请重试',
          icon: 'none',
          duration: 2000
        });
      }
    });
  },

  /**
   * 格式化时间
   */
  formatTime(isoString) {
    if (!isoString) return '';
    
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    // 1小时内显示"刚刚"
    if (diff < 3600000) {
      const minutes = Math.floor(diff / 60000);
      return minutes < 1 ? '刚刚' : `${minutes}分钟前`;
    }
    
    // 24小时内显示"X小时前"
    if (diff < 86400000) {
      const hours = Math.floor(diff / 3600000);
      return `${hours}小时前`;
    }
    
    // 否则显示完整日期
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hour}:${minute}`;
  },

  viewMemberDetail(e) {
    const member = e.currentTarget.dataset.member;
    wx.showModal({
      title: member.name,
      content: `角色: ${member.role}\n指纹ID: ${member.fingerprint_id || '未录入'}\nNFC: ${member.nfc_uid || '未绑定'}`,
      showCancel: false
    });
  },

  addNewMember() {
    wx.navigateTo({
      url: '/pages/users/add'
    });
  },

  deleteMember(e) {
    const member = e.currentTarget.dataset.member;
    wx.showModal({
      title: '确认删除',
      content: `确定要删除成员 ${member.name} 吗？`,
      success: (res) => {
        if (res.confirm) {
          getApp().request({
            url: `/users/${member.id}`,
            method: 'DELETE'
          }).then(res => {
            if (res && res.statusCode === 200 && res.data && res.data.success) {
              wx.showToast({
                title: '删除成功',
                icon: 'success'
              });
              this.loadMembers();
            }
          }).catch(err => {
            console.error('删除失败:', err);
            wx.showToast({
              title: '删除失败',
              icon: 'none'
            });
          });
        }
      }
    });
  }
})