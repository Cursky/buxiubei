#!/usr/bin/env bash
# moying-harness-init.sh — Create .harness/ directory structure with initial files
#
# Usage: ./moying-harness-init.sh [PROJECT_DIR]
#   PROJECT_DIR defaults to current directory

set -e

PROJECT_DIR="${1:-.}"
PROJECT_DIR="$(cd "$PROJECT_DIR" && pwd)"
HARNESS_DIR="$PROJECT_DIR/.harness"

if [ -d "$HARNESS_DIR" ]; then
    echo "INFO: .harness/ already exists at $HARNESS_DIR"
    exit 0
fi

echo "INFO: Creating .harness/ structure at $HARNESS_DIR"

mkdir -p "$HARNESS_DIR/designs"
mkdir -p "$HARNESS_DIR/plans"

# clarifications.md
cat > "$HARNESS_DIR/clarifications.md" << 'EOF'
# 项目澄清记录

## 活跃澄清

## 已归档
EOF

# constitution.md
cat > "$HARNESS_DIR/constitution.md" << 'EOF'
# 项目原则

（暂无原则。使用 /moying-constitution 添加。）
EOF

# project-spec.md
cat > "$HARNESS_DIR/project-spec.md" << 'EOF'
# 项目规范

**项目名称**: （待设定）
**题材类型**: （待设定）
**画风**: （待设定）
**目标平台**: Seedance 2.0
**总集数**: （待设定）
**每集时长**: 根据叙事需要灵活决定
**特殊要求**: （待设定）

## 补充说明
EOF

# moying-source.txt (placeholder for moying-skills repo path, filled by /moying-init)
touch "$HARNESS_DIR/moying-source.txt"

# plugins.md (empty table for plugin registration)
cat > "$HARNESS_DIR/plugins.md" << 'EOF'
# 已启用插件

| 插件 | 类型 | 状态 | 启用时间 |
|------|------|------|---------|
EOF

echo "✅ .harness/ 目录已创建: $HARNESS_DIR"
echo "   - clarifications.md"
echo "   - constitution.md"
echo "   - project-spec.md"
echo "   - plugins.md"
echo "   - moying-source.txt"
echo "   - designs/"
echo "   - plans/"
