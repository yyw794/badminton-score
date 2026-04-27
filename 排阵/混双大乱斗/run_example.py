#!/usr/bin/env python3
"""
混双大乱斗 - 快速使用示例
修改球员名单后直接运行即可
"""

from mixed_doubles_chaos import generate_mixed_doubles_matches, create_excel, print_schedule_summary


def main():
    # ========== 在这里修改你的球员名单 ==========
    
    # A组男队员
    group_a_males = [
        "林锋", 
        "王小波", 
        "陈顺星", 
        "罗琴荩", 
        "苏大哲", 
        "黄冬青"
    ]
    
    # B组女队员
    group_b_females = [
        "田茜", 
        "李祺祺", 
        "高洁", 
        "滕菲", 
        "崔倩男", 
        "李杏芝"
    ]
    
    # ========== 配置参数 ==========
    court_count = 2      # 场地数量（默认2个）
    mode = "fair"        # 排阵模式："fair"=公平模式（每人6场），"max"=最大场次模式
    
    # ========== 生成对阵表 ==========
    print("=" * 60)
    print("混双大乱斗排阵系统")
    print("=" * 60)
    print(f"\nA组男队员 ({len(group_a_males)}人): {', '.join(group_a_males)}")
    print(f"B组女队员 ({len(group_b_females)}人): {', '.join(group_b_females)}")
    print(f"\n配置: {court_count}个场地 | {'公平模式（每人6场）' if mode == 'fair' else '最大场次模式'}")
    
    print(f"\n正在生成对阵表...")
    matches = generate_mixed_doubles_matches(
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        court_count=court_count,
        mode=mode
    )
    
    if not matches:
        print("❌ 未能生成比赛，请检查球员人数是否足够（至少2男2女）")
        return
    
    # 打印摘要
    print_schedule_summary(matches)
    
    # 生成Excel文件
    output_filename = "混双大乱斗_对阵表.xlsx"
    create_excel(
        matches=matches,
        group_a_males=group_a_males,
        group_b_females=group_b_females,
        output_path=output_filename
    )
    
    print(f"\n🎉 完成！请查看文件: {output_filename}")


if __name__ == "__main__":
    main()
