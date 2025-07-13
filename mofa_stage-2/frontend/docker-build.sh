#!/bin/bash

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}==== MoFA Stage Frontend Docker Build ====${NC}"

# 检查是否在frontend目录
if [ ! -f "package.json" ]; then
    echo -e "${RED}错误: 请在frontend目录下运行此脚本${NC}"
    exit 1
fi

# 构建Docker镜像
echo -e "${YELLOW}构建Docker镜像...${NC}"
docker build -t mofa-stage-frontend:latest .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Docker镜像构建成功${NC}"
    
    # 询问是否运行
    echo -e "${YELLOW}是否立即运行容器? (Y/n):${NC}"
    read -r REPLY
    
    if [ "$REPLY" != "n" ] && [ "$REPLY" != "N" ]; then
        # 停止旧容器
        docker stop mofa-frontend 2>/dev/null
        docker rm mofa-frontend 2>/dev/null
        
        # 运行新容器
        echo -e "${YELLOW}启动容器...${NC}"
        docker run -d \
            --name mofa-frontend \
            -p 3000:80 \
            --add-host=host.docker.internal:host-gateway \
            --restart unless-stopped \
            mofa-stage-frontend:latest
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ 容器启动成功${NC}"
            echo -e "${GREEN}访问地址: http://localhost:3000${NC}"
            echo
            echo -e "${YELLOW}容器管理命令:${NC}"
            echo "  查看日志: docker logs mofa-frontend"
            echo "  停止容器: docker stop mofa-frontend"
            echo "  启动容器: docker start mofa-frontend"
            echo "  删除容器: docker rm mofa-frontend"
        else
            echo -e "${RED}✗ 容器启动失败${NC}"
            exit 1
        fi
    fi
else
    echo -e "${RED}✗ Docker镜像构建失败${NC}"
    exit 1
fi