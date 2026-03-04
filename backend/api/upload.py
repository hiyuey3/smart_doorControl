"""
V3.0 说明：
- 旧接口 /api/upload_snapshot 已下线。
- 抓拍上传统一由 routes.py 中 POST /api/hardware/snapshot 提供。

保留该文件仅为了兼容 api/__init__.py 的导入，不再注册任何路由。
"""
