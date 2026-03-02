# 🏸 羽毛球计分系统 - Vercel 部署教程（免费）

## 📐 架构

```
GitHub Pages (前端)  ──HTTPS──►  Vercel Serverless (API)  ──MySQL──►  TiDB Cloud (数据库)
```

---

## 🚀 部署步骤（5 分钟搞定）

### 第 1 步：创建 Vercel 项目

1. 访问 https://vercel.com/signup
2. 使用 **GitHub 账号登录**（推荐）
3. 点击 **"Add New Project"**
4. 选择 **"Import Git Repository"**
5. 选择你的 GitHub 仓库：`pingan_tech_badminton_team`

---

### 第 2 步：配置 Vercel 项目

#### 2.1 设置 Root Directory

在 Vercel 项目设置中：
- **Framework Preset**: `Other`
- **Root Directory**: `api-vercel`（点击 Edit 输入）

#### 2.2 添加环境变量

在 Vercel 项目设置 → **Environment Variables** 添加：

| Key | Value |
|-----|-------|
| `TIDB_HOST` | `gateway01.ap-southeast-1.prod.aws.tidbcloud.com` |
| `TIDB_PORT` | `4000` |
| `TIDB_USER` | `8AXKPCJGEHG5Qqv.root` |
| `TIDB_PASSWORD` | `7iv93aerRyGckxqw` |
| `TIDB_DATABASE` | `badminton` |

---

### 第 3 步：部署

1. 点击 **"Deploy"**
2. 等待部署完成（约 1-2 分钟）
3. 复制生成的域名（类似 `https://your-project.vercel.app`）

---

### 第 4 步：初始化数据库

在浏览器访问：
```
https://your-project.vercel.app/init
```

看到以下响应表示成功：
```json
{"success": true, "message": "数据库表初始化完成"}
```

---

### 第 5 步：导入活动数据

#### 方式 1：使用 curl（推荐）

```bash
cd /Users/yanyongwen712/Documents/pingan_tech_badminton_team

# 读取 data.json 并创建活动
curl -X POST https://your-project.vercel.app/events \
  -H "Content-Type: application/json" \
  -d @<(cat <<EOF
{
  "name": "$(jq -r '.eventName' docs/data.json)",
  "court_count": $(jq -r '.courtCount' docs/data.json),
  "matches": $(jq -c '.matches' docs/data.json)
}
EOF
)
```

#### 方式 2：使用 Python 脚本

```bash
cd api-vercel
python ../api/import_from_json.py ../docs/data.json
```

保存输出的 `EVENT_ID`

---

### 第 6 步：修改前端配置

编辑 `docs/app.js` 第 7-12 行：

```javascript
const API_BASE_URL = 'https://your-project.vercel.app';  // 替换为你的 Vercel 域名
const EVENT_ID = '上一步生成的活动 ID';  // 替换为实际活动 ID
const ENABLE_CLOUD_SYNC = true;  // 改为 true
```

---

### 第 7 步：推送部署

```bash
git add docs/app.js
git commit -m "启用云端同步"
git push
```

Vercel 会自动检测 GitHub 推送并重新部署（无需手动操作）。

---

## ✅ 验证

1. 打开 GitHub Pages 网址
2. 点击任意比赛录入比分
3. 打开浏览器控制台（F12），查看是否有 `比赛 xxx 比分已同步到云端` 日志
4. 在另一台设备打开网页，应该能看到同步的比分

---

## 💰 费用说明

### Vercel Hobby 计划（免费）

| 资源 | 额度 | 说明 |
|------|------|------|
| 带宽 | 100 GB/月 | 足够数千次 API 调用 |
| Serverless 执行 | 100 GB-小时/月 | 足够小项目使用 |
| 域名 | 免费 | `*.vercel.app` |

### TiDB Cloud（免费层）

| 资源 | 额度 |
|------|------|
| 存储 | 5 GB |
| 请求单位 | 5000 万 RUs/月 |

---

## 🔧 故障排查

### 问题 1：部署失败

- 确保 `api-vercel/` 目录包含 `vercel.json`、`index.py`、`requirements.txt`
- 检查 Vercel 构建日志

### 问题 2：API 返回 500 错误

- 检查环境变量是否正确配置
- 查看 Vercel 函数日志（Dashboard → Functions → Logs）

### 问题 3：数据库连接失败

- 确认 TiDB Cloud 集群状态正常
- 检查防火墙设置（TiDB Cloud 需允许公网访问）

---

## 📝 对比：阿里云 vs Vercel

| 特性 | 阿里云函数计算 | Vercel |
|------|---------------|--------|
| 免费额度 | 15 万 CU/月（3 个月） | 100 GB/月（永久） |
| 配置复杂度 | 需要配置实例 | 零配置 |
| 中国大陆访问 | 快 | 一般（但 API 请求量小） |
| 部署方式 | 手动上传 ZIP | Git 推送自动部署 |
| 推荐 | 企业用户 | 个人项目 ✅ |

---

## 🎉 完成！

现在你的应用支持：
- ✅ 多人同时编辑比分
- ✅ 实时同步（每 5 秒）
- ✅ 完全免费
- ✅ 自动部署
