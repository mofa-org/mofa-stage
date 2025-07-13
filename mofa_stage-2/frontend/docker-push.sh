#!/bin/bash

# Docker Hub推送脚本

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 配置
DOCKER_USERNAME="liyao1119"  # 修改为你的Docker Hub用户名
IMAGE_NAME="mofa-stage-frontend"
VERSION="latest"

echo -e "${GREEN}==== 推送到Docker Hub ====${NC}"

# 检查是否登录
if ! docker info | grep -q "Username: $DOCKER_USERNAME"; then
    echo -e "${YELLOW}请先登录Docker Hub:${NC}"
    docker login
fi

# 构建镜像
echo -e "${YELLOW}构建镜像...${NC}"
docker build -t $IMAGE_NAME:$VERSION .

if [ $? -ne 0 ]; then
    echo -e "${RED}构建失败！${NC}"
    exit 1
fi

# 标记镜像
echo -e "${YELLOW}标记镜像...${NC}"
docker tag $IMAGE_NAME:$VERSION $DOCKER_USERNAME/$IMAGE_NAME:$VERSION
docker tag $IMAGE_NAME:$VERSION $DOCKER_USERNAME/$IMAGE_NAME:latest

# 推送镜像
echo -e "${YELLOW}推送镜像到Docker Hub...${NC}"
docker push $DOCKER_USERNAME/$IMAGE_NAME:$VERSION
docker push $DOCKER_USERNAME/$IMAGE_NAME:latest

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 推送成功！${NC}"
    echo
    echo -e "${GREEN}其他人可以使用以下命令拉取镜像：${NC}"
    echo "docker pull $DOCKER_USERNAME/$IMAGE_NAME:latest"
    echo
    echo -e "${GREEN}运行容器：${NC}"
    echo "docker run -d -p 3000:80 --name mofa-frontend \\"
    echo "  --add-host=host.docker.internal:host-gateway \\"
    echo "  $DOCKER_USERNAME/$IMAGE_NAME:latest"
else
    echo -e "${RED}✗ 推送失败！${NC}"
    exit 1
fi