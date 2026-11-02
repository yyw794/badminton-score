#!/usr/bin/env python3
"""2026-10-26 工会杯赛前演练 排阵求解器（4场地16人7轮28场，手排骨架+回溯搜槽）。

固定骨架（意向排阵.md）：
  - 每轮 4 场；SHOWDOWN 轮：男双一 苏大哲+陈财贵 vs 男双二 罗琴荩+刘继宇（不拆）。
  - 其余轮：男双一、男双二 各 1 场，对手 4 槽由陪打池（林锋/王小波/陈小洪/张欣欣，
    可加王苏丹 1-2 场）补齐。
  - 范智强/严勇文 只打男单；王苏丹 男单+混双各半；徐越 女单为主；
    李佳琳/林小连/高洁 女双为主（三组合都要）；唐英武 混双为主+女双；陈小洪/张欣欣 陪打。
搜索变量：男单/混双/男双(陪打对)/女单/女双 的场数与轮次分配；目标=能量极差最小。
"""
import random
from collections import Counter
from itertools import combinations

M = ["苏大哲", "陈财贵", "罗琴荩", "刘继宇", "范智强", "严勇文", "王苏丹",
     "林锋", "王小波", "陈小洪", "张欣欣"]
W = ["徐越", "李佳琳", "林小连", "高洁", "唐英武"]
ALL = M + W
FILLER = ["林锋", "王小波", "陈小洪", "张欣欣"]
COURTS = [6, 8, 17, 18]
CAP = 7
BEST = {"spread": 99, "sol": None}


def solve(timeout=60.0):
    import time
    t0 = time.time()
    rng = random.Random(7)
    women = W

    # ---- 候选生成 ----
    # 男单配对（范/严只单打；王苏丹 1-2 场；陈小洪可 1 场补偶）
    ms_cands = []
    for n_f in (3, 4):
        for n_y in (3, 4):
            for n_w in (1, 2):
                for n_c in (0, 1):
                    apps = n_f + n_y + n_w + 2 * n_c  # 陈小洪单打=1场+2能量
                    if apps % 2:
                        continue
                    ms_cands.append((n_f, n_y, n_w, n_c))
    # 去重
    ms_cands = sorted(set(ms_cands))

    # 混双：王苏丹 x 场(与林锋≥1、王小波≥1 同场)，林锋 y，王小波 z，陈小洪/张欣欣 可 1
    def xd_cands():
        out = []
        for n_wsd in (2, 3):
            for m_lf in (1, 2):
                for m_wxb in (1, 2):
                    slots = n_wsd + m_lf + m_wxb  # 其余男槽
                    if slots % 2:
                        continue
                    out.append((n_wsd, m_lf, m_wxb))
        return sorted(set(out))

    # 女单：徐越 n_ws 场，对手从 [李佳琳, 高洁, 唐英武] 选（可重复但场间不重人）
    # 女双：wd 场，4女槽/场，组合覆盖 佳连/佳高/连高 ≥1，唐 ≥1 场
    # 男双(陪打对)：md 场，4 男槽/场，从 FILLER 凑（每场 4 人不同）

    for (n_f, n_y, n_wsd_ms, n_ch_ms) in ms_cands:
        for (n_wsd_xd, m_lf_xd, m_wxb_xd) in xd_cands():
            for n_md in (0, 1, 2):
                for n_ws in (2, 3):
                    for n_wd in (4, 5, 6):
                        n_xd = n_wsd_xd  # 场数=王苏丹混双场数（他每场都上）
                        # 男槽守恒：普通轮 opp 槽由 SHOWDOWN 数决定
                        for n_show in (2, 3):
                            n_plain = 7 - n_show
                            opp_slots = 2 * n_plain
                            # flex 总槽
                            n_flex = 3 * n_show + 2 * n_plain
                            need = (n_f + n_y + n_wsd_ms + n_ch_ms) // 2  # ms 场数
                            total_flex = need + n_xd + n_md + n_ws + n_wd
                            if total_flex != n_flex:
                                continue
                            # 男能量守恒检查
                            # opp 分配（陪打池含 WSD 的 opp 场数变量）
                            yield (n_show, n_f, n_y, n_wsd_ms, n_ch_ms,
                                   n_wsd_xd, m_lf_xd, m_wxb_xd, n_md, n_ws, n_wd)
    return


if __name__ == "__main__":
    n = 0
    for spec in solve():
        n += 1
        if n <= 5:
            print(spec)
    print("候选规格总数:", n)
