# 🏸 羽毛球比赛记分系统

## 项目简介

这是一个完整的羽毛球比赛排阵和记分系统，包含：

1. **排阵系统（Python）**: 根据报名名单自动生成均衡的对阵表
2. **记分系统（Web）**: 移动端友好的比分录入、统计和分享

## 🚀 快速开始

### 1. 生成对阵表

```bash
# 更新报名名单（排阵/微信接龙.txt）
# 然后运行排阵脚本
uv run python 排阵/lineup_scheduler.py

# 导出为 Web 格式
uv run python 排阵/web/export_to_web.py
```

### 2. 使用 Web 应用

**本地使用**:
```bash
open 排阵/web/index.html
```

**线上分享**:
部署到 GitHub Pages，访问 `https://yyw794.github.io/badminton-score/`

### 3. 更新并部署

```bash
# 复制 web 文件到 docs 目录
cp -r 排阵/web/* docs/

# 提交并推送
git add .
git commit -m "更新对阵数据"
git push
```

## 📁 目录结构

```
.
├── 排阵/                      # 排阵系统
│   ├── lineup_scheduler.py    # 排阵脚本
│   ├── 微信接龙.txt            # 报名名单
│   ├── 对阵表.xlsx             # 生成的对阵表
│   └── web/                   # Web 应用源码
├── docs/                      # GitHub Pages 部署目录
└── README.md                  # 本文件
```

详细结构说明见 [排阵/项目结构说明.md](排阵/项目结构说明.md)

## 📱 Web 功能

- ✅ 比分录入
- ✅ 球员统计
- ✅ 战绩分析
- ✅ 海报生成
- ✅ 数据导出/导入

## 🔗 链接

- **在线访问**: https://yyw794.github.io/badminton-score/
- **部署指南**: [docs/部署指南.md](docs/部署指南.md)
