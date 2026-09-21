#!/usr/bin/env python3
"""深度分析羽毛球比赛数据"""
import json
import sys
from collections import defaultdict

def analyze_deep(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    matches = data['matches']

    # 1. 搭档组合分析
    partner_stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'matches': []})

    # 2. 关键场次分析（比分接近）
    close_matches = []

    # 3. 场地分析
    court_stats = defaultdict(lambda: {'wins_a': 0, 'wins_b': 0})

    # 4. 轮次分析
    round_stats = defaultdict(lambda: {'wins_a': 0, 'wins_b': 0})

    # 5. 选手出场轮次分布
    player_rounds = defaultdict(list)

    for m in matches:
        ta = m['team_a']
        tb = m['team_b']
        sa = m['score_a']
        sb = m['score_b']
        rnd = m['round']
        court = m['court']
        typ = m['type']

        # 解析比分
        a1, b1 = int(sa.split(':')[0]), int(sa.split(':')[1])
        a2, b2 = int(sb.split(':')[0]), int(sb.split(':')[1])

        # 判断胜负
        win1 = 'a' if a1 > b1 else 'b'
        win2 = 'a' if a2 > b2 else 'b'

        # 搭档组合统计（双打类型）
        if len(ta) == 2:
            pair_key = tuple(sorted(ta))
            partner_stats[pair_key]['matches'].append({'round': rnd, 'court': court, 'type': typ, 'result': win1 if win1=='a' else 'loss'})
            partner_stats[pair_key]['matches'].append({'round': rnd, 'court': court, 'type': typ, 'result': win2 if win2=='a' else 'loss'})
            if win1 == 'a':
                partner_stats[pair_key]['wins'] += 1
            else:
                partner_stats[pair_key]['losses'] += 1
            if win2 == 'a':
                partner_stats[pair_key]['wins'] += 1
            else:
                partner_stats[pair_key]['losses'] += 1

        if len(tb) == 2:
            pair_key = tuple(sorted(tb))
            partner_stats[pair_key]['matches'].append({'round': rnd, 'court': court, 'type': typ, 'result': win1 if win1=='b' else 'loss'})
            partner_stats[pair_key]['matches'].append({'round': rnd, 'court': court, 'type': typ, 'result': win2 if win2=='b' else 'loss'})
            if win1 == 'b':
                partner_stats[pair_key]['wins'] += 1
            else:
                partner_stats[pair_key]['losses'] += 1
            if win2 == 'b':
                partner_stats[pair_key]['wins'] += 1
            else:
                partner_stats[pair_key]['losses'] += 1

        # 关键场次（分差<=2 或 15:14）
        for score_str, set_num in [(sa, 1), (sb, 2)]:
            parts = score_str.split(':')
            s1, s2 = int(parts[0]), int(parts[1])
            if (s1 == 15 and s2 >= 13) or (s2 == 15 and s1 >= 13):
                winner = ta if s1 > s2 else tb
                loser = tb if s1 > s2 else ta
                close_matches.append({
                    'round': rnd, 'court': court, 'type': typ, 'set': set_num,
                    'score': score_str, 'winner': winner, 'loser': loser
                })

        # 场地统计
        if win1 == 'a':
            court_stats[court]['wins_a'] += 1
        else:
            court_stats[court]['wins_b'] += 1
        if win2 == 'a':
            court_stats[court]['wins_a'] += 1
        else:
            court_stats[court]['wins_b'] += 1

        # 轮次统计
        if win1 == 'a':
            round_stats[rnd]['wins_a'] += 1
        else:
            round_stats[rnd]['wins_b'] += 1
        if win2 == 'a':
            round_stats[rnd]['wins_a'] += 1
        else:
            round_stats[rnd]['wins_b'] += 1

        # 选手出场轮次
        for p in ta + tb:
            player_rounds[p].append(rnd)

    print("=" * 60)
    print("深度分析报告")
    print("=" * 60)

    # 搭档组合排名
    print("\n【搭档组合排名】（双打组合胜率）")
    print("-" * 60)
    partner_rank = []
    for pair, stats in partner_stats.items():
        total = stats['wins'] + stats['losses']
        win_rate = stats['wins'] / total if total > 0 else 0
        partner_rank.append({
            'pair': pair,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'total': total,
            'win_rate': win_rate
        })
    partner_rank.sort(key=lambda x: (-x['win_rate'], -x['wins']))

    print(f"{'排名':<4}{'搭档组合':<20}{'胜':<6}{'负':<6}{'总':<6}{'胜率':<8}")
    for i, item in enumerate(partner_rank[:15], 1):
        pair_str = '/'.join(item['pair'])
        print(f"{i:<4}{pair_str:<20}{item['wins']:<6}{item['losses']:<6}{item['total']:<6}{item['win_rate']:.1%}")

    # 关键场次分析
    print("\n【关键场次】（比分13:15或更接近）")
    print("-" * 60)
    for cm in close_matches:
        winner_str = '/'.join(cm['winner']) if len(cm['winner']) > 1 else cm['winner'][0]
        loser_str = '/'.join(cm['loser']) if len(cm['loser']) > 1 else cm['loser'][0]
        print(f"R{cm['round']}C{cm['court']} [{cm['type']}] 第{cm['set']}局 {cm['score']}: {winner_str} 胜 {loser_str}")

    # 场地分析
    print("\n【场地胜率】（对阵A vs 对阵B）")
    print("-" * 60)
    for court in sorted(court_stats.keys()):
        stats = court_stats[court]
        total = stats['wins_a'] + stats['wins_b']
        a_rate = stats['wins_a'] / total if total > 0 else 0
        b_rate = stats['wins_b'] / total if total > 0 else 0
        court_str = f"{court}号"
        print(f"{court_str}: A胜{stats['wins_a']}局({a_rate:.1%}) vs B胜{stats['wins_b']}局({b_rate:.1%})")

    # 轮次分析
    print("\n【轮次胜率趋势】")
    print("-" * 60)
    for rnd in sorted(round_stats.keys()):
        stats = round_stats[rnd]
        total = stats['wins_a'] + stats['wins_b']
        a_rate = stats['wins_a'] / total if total > 0 else 0
        b_rate = stats['wins_b'] / total if total > 0 else 0
        print(f"第{rnd}轮: A胜{stats['wins_a']}局({a_rate:.1%}) vs B胜{stats['wins_b']}局({b_rate:.1%})")

    # 新人陈财贵详细分析
    print("\n【新人陈财贵详细表现】")
    print("-" * 60)
    caicai_matches = []
    for m in matches:
        if '陈财贵' in m['team_a'] or '陈财贵' in m['team_b']:
            ta_str = '/'.join(m['team_a'])
            tb_str = '/'.join(m['team_b'])
            sa = m['score_a']
            sb = m['score_b']
            a1, b1 = int(sa.split(':')[0]), int(sa.split(':')[1])
            a2, b2 = int(sb.split(':')[0]), int(sb.split(':')[1])

            team = 'A' if '陈财贵' in m['team_a'] else 'B'
            partner = [p for p in (m['team_a'] if team=='A' else m['team_b']) if p != '陈财贵']
            partner_str = partner[0] if partner else ''

            # 判断胜负
            g1_win = '陈财贵' in m['team_a'] if a1 > b1 else '陈财贵' in m['team_b']
            g2_win = '陈财贵' in m['team_a'] if a2 > b2 else '陈财贵' in m['team_b']
            opponent = m['team_b'] if team == 'A' else m['team_a']
            opp_str = '/'.join(opponent)

            caicai_matches.append({
                'round': m['round'],
                'court': m['court'],
                'type': m['type'],
                'partner': partner_str,
                'opponent': opp_str,
                'g1_result': '胜' if g1_win else '负',
                'g2_result': '胜' if g2_win else '负',
                'score_a': sa,
                'score_b': sb
            })

    print(f"{'轮次':<4}{'场地':<4}{'类型':<6}{'搭档':<10}{'对手':<20}{'第1局':<8}{'第2局':<8}")
    for cm in caicai_matches:
        print(f"R{cm['round']:<3}C{cm['court']:<3}{cm['type']:<6}{cm['partner']:<10}{cm['opponent']:<20}{cm['g1_result']}({cm['score_a']}){cm['g2_result']}({cm['score_b']})")

    # 选手出场轮次分布（疲劳分析）
    print("\n【选手出场轮次分布】（疲劳度分析）")
    print("-" * 60)
    player_freq = []
    for p, rounds in player_rounds.items():
        rounds_sorted = sorted(rounds)
        gaps = []
        for i in range(1, len(rounds_sorted)):
            gaps.append(rounds_sorted[i] - rounds_sorted[i-1])
        avg_gap = sum(gaps) / len(gaps) if gaps else 0
        player_freq.append({
            'player': p,
            'count': len(rounds_sorted),
            'rounds': rounds_sorted,
            'avg_gap': avg_gap,
            'max_gap': max(gaps) if gaps else 0
        })
    player_freq.sort(key=lambda x: (-x['count'], -x['avg_gap']))

    print(f"{'选手':<10}{'出场':<6}{'轮次':<20}{'平均间隔':<8}{'最大间隔':<8}")
    for pf in player_freq:
        rounds_str = ','.join(str(r) for r in pf['rounds'])
        print(f"{pf['player']:<10}{pf['count']:<6}{rounds_str:<20}{pf['avg_gap']:.1f}{pf['max_gap']:<8}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        json_path = sys.argv[1]
    else:
        json_path = 'scores/20260629/match_data.json'
    analyze_deep(json_path)