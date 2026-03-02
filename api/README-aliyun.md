# 阿里云函数计算 Web 函数配置说明

## 上传代码
- 文件：`function.zip`（包含 aliyun_web.py 和 requirements.txt）

## Handler 配置
```
aliyun_web:app
```

## 监听端口
```
8080
```

## 启动命令
```
python3 aliyun_web.py
```

## 环境变量
```json
{
  "TIDB_HOST": "gateway01.ap-southeast-1.prod.aws.tidbcloud.com",
  "TIDB_PORT": "4000",
  "TIDB_USER": "8AXKPCJGEHG5Qqv.root",
  "TIDB_PASSWORD": "7iv93aerRyGckxqw",
  "TIDB_DATABASE": "test"
}
```
