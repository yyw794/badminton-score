from mixed_doubles_chaos import generate_mixed_doubles_matches
from collections import defaultdict

def test_pairing_uniformity():
    """测试男女搭配的均匀度"""
    
    males = ['林锋', '王小波', '陈顺星', '罗琴荩', '苏大哲', '黄冬青']
    females = ['田茜', '李祺祺', '高洁', '滕菲', '崔倩男', '李杏芝']
    
    matches = generate_mixed_doubles_matches(males, females, 2)
    
    print('=' * 60)
    print('男女搭配均匀度分析')
    print('=' * 60)
    
    # 统计每个男队员与每个女队员的搭配次数
    pair_count = defaultdict(int)
    
    for match in matches:
        # 每场比赛有2个配对
        pair1 = match['match'][0]  # (男, 女)
        pair2 = match['match'][1]  # (男, 女)
        
        pair_count[pair1] += 1
        pair_count[pair2] += 1
    
    # 按男队员分组显示
    print('\n【每个男队员的搭配情况】')
    for male in males:
        print(f'\n{male} (共6场):')
        female_partners = []
        for (m, f), count in sorted(pair_count.items()):
            if m == male:
                female_partners.append((f, count))
                symbol = '✅' if count == 1 else '⚠️'
                print(f'  {symbol} 与 {f}: {count}次')
        
        # 检查是否有重复
        duplicates = [(f, c) for f, c in female_partners if c > 1]
        if duplicates:
            print(f'  ❌ 重复搭配: {len(duplicates)}个女队员')
        else:
            print(f'  ✅ 完美！所有女队员都不重复')
    
    # 统计重复情况
    print('\n' + '=' * 60)
    print('【整体统计】')
    total_pairs = len(pair_count)
    unique_pairs = sum(1 for count in pair_count.values() if count == 1)
    duplicate_pairs = sum(1 for count in pair_count.values() if count > 1)
    
    print(f'总配对数: {total_pairs}')
    print(f'唯一配对: {unique_pairs}')
    print(f'重复配对: {duplicate_pairs}')
    
    if duplicate_pairs > 0:
        print(f'\n❌ 存在重复搭配:')
        for (m, f), count in sorted(pair_count.items()):
            if count > 1:
                print(f'  {m} + {f}: {count}次')
    else:
        print(f'\n✅ 完美！36个配对全部不重复，每个男队员与每个女队员恰好搭配1次')
    
    print('=' * 60)

if __name__ == '__main__':
    test_pairing_uniformity()
