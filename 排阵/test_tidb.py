#!/usr/bin/env python3
"""测试 TiDB Cloud 连接性"""

import mysql.connector
from mysql.connector import Error

# TiDB Cloud 连接配置
config = {
    'host': 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com',
    'port': 4000,
    'user': '8AXKPCJGEHG5Qqv.root',
    'password': '7iv93aerRyGckxqw',
    'database': 'test',
    'ssl_ca': '/etc/ssl/cert.pem',
    'ssl_verify_cert': True,
}

def test_connection():
    """测试 TiDB 连接"""
    print("=" * 50)
    print("TiDB Cloud 连接测试")
    print("=" * 50)
    
    try:
        # 尝试连接
        print("\n[1] 正在连接 TiDB Cloud...")
        conn = mysql.connector.connect(**config)
        
        if conn.is_connected():
            print("    ✅ 连接成功！")
            
            # 获取服务器信息
            print("\n[2] 服务器信息:")
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION();")
            version = cursor.fetchone()
            print(f"    TiDB 版本：{version[0]}")
            
            # 获取当前数据库
            cursor.execute("SELECT DATABASE();")
            db = cursor.fetchone()
            print(f"    当前数据库：{db[0]}")
            
            # 获取当前用户
            cursor.execute("SELECT USER();")
            user = cursor.fetchone()
            print(f"    当前用户：{user[0]}")
            
            # 测试创建表
            print("\n[3] 测试创建表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_connection (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    message VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            print("    ✅ 表创建成功")
            
            # 测试插入数据
            print("\n[4] 测试插入数据...")
            cursor.execute(
                "INSERT INTO test_connection (message) VALUES (%s)",
                ("TiDB Cloud 连接测试成功",)
            )
            conn.commit()
            print(f"    ✅ 插入成功，影响行数：{cursor.rowcount}")
            
            # 测试查询数据
            print("\n[5] 测试查询数据...")
            cursor.execute("SELECT * FROM test_connection ORDER BY created_at DESC LIMIT 5;")
            rows = cursor.fetchall()
            print(f"    ✅ 查询成功，共 {len(rows)} 条记录:")
            for row in rows:
                print(f"       - ID:{row[0]}, Message:{row[1]}, Time:{row[2]}")
            
            # 清理测试数据
            print("\n[6] 清理测试数据...")
            cursor.execute("DROP TABLE test_connection;")
            print("    ✅ 测试表已删除")
            
            cursor.close()
            print("\n" + "=" * 50)
            print("🎉 所有测试通过！TiDB Cloud 连接正常")
            print("=" * 50)
            
        else:
            print("    ❌ 连接失败：无法建立连接")
            
    except Error as e:
        print(f"\n    ❌ 数据库错误：{e}")
        return False
    except Exception as e:
        print(f"\n    ❌ 未知错误：{e}")
        return False
    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()
            print("\n[✓] 连接已关闭")
    
    return True

if __name__ == "__main__":
    test_connection()
