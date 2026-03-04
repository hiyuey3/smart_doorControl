const LOGIN_PAGE_URL = '/pages/login/index';

function showToast(title, icon = 'none', duration = 2000) {
  wx.showToast({ title, icon, duration });
}

function showSuccess(title, duration = 2000) {
  showToast(title, 'success', duration);
}

function showError(title, duration = 2000) {
  showToast(title, 'none', duration);
}

function redirectToLogin(delay = 1200) {
  setTimeout(() => {
    wx.redirectTo({
      url: LOGIN_PAGE_URL
    });
  }, delay);
}

function clearSession() {
  wx.removeStorageSync('token');
  wx.removeStorageSync('userInfo');
  wx.removeStorageSync('user');
}

function handleUnauthorized(options = {}) {
  const { showMessage = true, redirectDelay = 1500 } = options;
  clearSession();
  if (showMessage) {
    showError('登录已过期，请重新登录', redirectDelay);
  }
  redirectToLogin(redirectDelay);
}

function ensureLogin() {
  const token = wx.getStorageSync('token');
  if (token) {
    return true;
  }
  redirectToLogin(0);
  return false;
}

module.exports = {
  showToast,
  showSuccess,
  showError,
  redirectToLogin,
  clearSession,
  handleUnauthorized,
  ensureLogin
};
