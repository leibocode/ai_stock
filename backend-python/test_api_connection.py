#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断爬虫API连接问题
测试外部API是否可访问，识别被封IP的问题
"""

import asyncio
import httpx
import time
import sys
import io
from typing import Dict, List, Tuple

# 设置Windows的输出编码为UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 测试的API端点
TEST_APIS = {
    "同花顺涨停": {
        "url": "https://data.10jqka.com.cn/dataapi/limit_up/limit_up_pool",
        "params": {"date": "2024-12-18"}
    },
    "东财龙虎榜": {
        "url": "https://datacenter-web.eastmoney.com/api/data/v1/get",
        "params": {
            "reportName": "RPT_DAILYBILLBOARD_DETAILSNEW",
            "pageNumber": 1,
            "pageSize": 500,
            "sortTypes": "-1",
            "sortFields": "TRADE_DATE",
            "conditions": "TRADE_DATE=20241218",
        }
    },
    "东财北向资金(方案1-新)": {
        "url": "https://datacenter-web.eastmoney.com/api/data/v1/get",
        "params": {
            "reportName": "RPT_HK_IPOLDERS",
            "pageNumber": 1,
            "pageSize": 10,
            "sortTypes": "-1",
            "sortFields": "HOLD_MARKET_CAP",
        }
    },
    "东财北向资金(方案2-push2)": {
        "url": "https://push2.eastmoney.com/api/qt/clist/get",
        "params": {
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:116",
            "fields": "f12,f14,f2,f3,f62,f104,f105,f106,f107,f109,f110",
            "pagesize": "10",
            "pageindex": "1",
        }
    },
    "东财板块资金": {
        "url": "https://push2.eastmoney.com/api/qt/clist/get",
        "params": {
            "np": "1",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:90+t:2",
            "fields": "f12,f14,f2,f3,f62,f104,f105,f106,f107,f109,f110",
            "pagesize": "500",
            "pageindex": "1",
        }
    }
}

# 代理列表（测试用）
TEST_PROXIES = [
    "http://127.0.0.1:7890",  # Clash
    "http://127.0.0.1:1080",  # Shadowsocks
    # 可以添加更多代理
]

async def test_api(
    name: str,
    url: str,
    params: Dict,
    proxy: str = None,
    timeout: int = 10
) -> Tuple[bool, str, int]:
    """测试单个API

    返回: (成功, 消息, 状态码)
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    headers = {
        "User-Agent": user_agents[0],
        "Referer": "https://www.eastmoney.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
    }

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            proxy=proxy,
            verify=False
        ) as client:
            resp = await client.get(url, params=params, headers=headers)
            status = resp.status_code

            if status == 200:
                # 检查响应内容
                data = resp.json()
                if isinstance(data, dict) and data:
                    has_data = bool(data.get("data") or data.get("result") or len(data) > 0)
                    msg = f"[OK] 成功，返回数据: {len(str(data))} bytes"
                    return (True, msg, status)
                else:
                    msg = f"[WARN] 响应为空"
                    return (False, msg, status)
            else:
                msg = f"[FAIL] 状态码 {status}"
                return (False, msg, status)

    except httpx.HTTPStatusError as e:
        msg = f"[FAIL] HTTP {e.response.status_code}"
        return (False, msg, e.response.status_code)
    except asyncio.TimeoutError:
        msg = "[FAIL] 超时"
        return (False, msg, 0)
    except Exception as e:
        msg = f"[FAIL] 错误: {str(e)[:50]}"
        return (False, msg, 0)

async def diagnose():
    """诊断所有API连接"""
    print("\n" + "="*80)
    print("API连接诊断报告")
    print("="*80 + "\n")

    # 1. 测试直接连接（无代理）
    print("【第1阶段】测试直接连接（无代理）")
    print("-" * 80)

    results = {}
    for name, config in TEST_APIS.items():
        print(f"测试: {name:20} ", end="", flush=True)
        success, msg, status = await test_api(
            name,
            config["url"],
            config["params"],
            proxy=None
        )
        results[name] = (success, msg, status)
        print(msg)
        await asyncio.sleep(1)  # 避免请求过快

    # 2. 分析结果
    print("\n【第2阶段】分析结果")
    print("-" * 80)

    failed_apis = [name for name, (success, _, _) in results.items() if not success]

    if not failed_apis:
        print("[OK] 所有API都可以访问，无需代理")
        return

    print(f"[WARN] {len(failed_apis)} 个API无法访问:")
    for name in failed_apis:
        print(f"  - {name}")

    # 3. 测试代理
    print("\n【第3阶段】测试代理")
    print("-" * 80)

    for proxy in TEST_PROXIES:
        print(f"\n测试代理: {proxy}")
        print("-" * 40)

        proxy_available = False
        for name in failed_apis[:1]:  # 只用第一个失败的API测试代理
            config = TEST_APIS[name]
            print(f"  {name:20} ", end="", flush=True)
            success, msg, status = await test_api(
                name,
                config["url"],
                config["params"],
                proxy=proxy,
                timeout=5
            )
            print(msg)
            if success:
                proxy_available = True
            await asyncio.sleep(1)

        if not proxy_available:
            print(f"  [FAIL] 代理 {proxy} 不可用或无法改善连接")

    # 4. 建议
    print("\n【诊断建议】")
    print("-" * 80)
    print("""
如果所有API都无法访问：
1. IP可能被封 - 需要配置可用的代理
2. API端点可能已更改 - 需要验证URL是否正确
3. 网络连接问题 - 检查防火墙和网络设置

代理配置步骤：
1. 获取可用的代理服务器地址
2. 在 app/services/crawler/base.py 中的 PROXIES 列表中添加
3. 重启服务器进行测试

常见代理来源：
- 免费代理池: https://www.freeproxylists.net/
- 付费代理: 西刻代理、阿布云等
- 本地代理: Clash、Shadowsocks 等
""")

if __name__ == "__main__":
    asyncio.run(diagnose())
