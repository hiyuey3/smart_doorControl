#!/bin/bash
# 智慧校园门禁系统 - 快速部署脚本

set -e  # 遇到错误立即退出

echo "======================================"
echo "  智慧校园门禁系统 - 部署脚本"
echo "======================================"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: Docker 未安装"
    echo "请先安装 Docker: https://docs.docker.com/engine/install/"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ 错误: Docker Compose 未安装"
    echo "请先安装 Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "⚠️  警告: .env 文件不存在，从 .env.example 复制..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✅ 已创建 .env 文件，请修改其中的配置"
        echo ""
        read -p "是否现在编辑 .env 文件? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            ${EDITOR:-nano} .env
        fi
    else
        echo "❌ 错误: .env.example 文件不存在"
        exit 1
    fi
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p instance logs ssl

# 检查 SSL 证书
if [ ! -f ssl/fullchain.pem ] || [ ! -f ssl/privkey.pem ]; then
    echo "⚠️  警告: SSL 证书不存在"
    echo "请将证书文件放置在 ssl/ 目录下:"
    echo "  - ssl/fullchain.pem (完整证书链)"
    echo "  - ssl/privkey.pem (私钥)"
    echo ""
    read -p "是否继续部署? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 停止旧容器
echo "🛑 停止旧容器..."
docker-compose down 2>/dev/null || true

# 构建镜像
echo "🔨 构建 Docker 镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo ""
echo "📊 检查服务状态..."
docker-compose ps

# 测试健康检查
echo ""
echo "🏥 测试健康检查..."
if curl -f http://localhost:5000/api/health 2>/dev/null; then
    echo "✅ 后端服务正常"
else
    echo "⚠️  后端服务可能未完全启动，请查看日志"
fi

echo ""
echo "======================================"
echo "  ✅ 部署完成！"
echo "======================================"
echo ""
echo "📝 常用命令:"
echo "  查看日志: docker-compose logs -f"
echo "  重启服务: docker-compose restart"
echo "  停止服务: docker-compose down"
echo "  查看状态: docker-compose ps"
echo ""
echo "🌐 访问地址:"
echo "  HTTP:  http://your-server-ip:80"
echo "  HTTPS: https://dev.api.5i03.cn"
echo ""
