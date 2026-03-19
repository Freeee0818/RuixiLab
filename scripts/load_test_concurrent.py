#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
并发负载测试脚本 - 模拟多用户同时提交 PySR 任务
用法:
  python scripts/load_test_concurrent.py                    # 默认 30 并发
  python scripts/load_test_concurrent.py --concurrency 50   # 50 并发
  python scripts/load_test_concurrent.py --base-url http://localhost:8000 --concurrency 30
"""

import argparse
import asyncio
import time
import statistics
from pathlib import Path

try:
    import httpx
except ImportError:
    print("请先安装: pip install httpx")
    raise SystemExit(1)

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def get_test_file_path():
    """优先使用小文件以加快测试；若不存在则用单摆数据"""
    for name in ["src/assets/sample_data.csv", "public/单摆实验数据.txt"]:
        p = PROJECT_ROOT / name
        if p.exists():
            return p
    raise FileNotFoundError("未找到测试数据文件，请指定 --file 或确保 src/assets/sample_data.csv 存在")


async def submit_one(
    client: httpx.AsyncClient,
    base_url: str,
    file_path: Path,
    user_id: int,
    wait_complete: bool = False,
    poll_interval: float = 2.0,
    max_wait: float = 600.0,
) -> dict:
    """
    单次提交任务。
    - 默认只测「提交速度」：返回 task_id 即结束；
    - 在 wait_complete=True 时，会轮询 /tasks/{task_id}，直到 completed/failed 或超时。
    返回:
        {
            user_id, status_code, task_id,
            task_status, elapsed, error
        }
    """
    url_tasks = f"{base_url.rstrip('/')}/tasks"
    start = time.perf_counter()
    result = {
        "user_id": user_id,
        "status_code": None,
        "task_id": None,
        "task_status": None,
        "elapsed": None,
        "error": None,
    }
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        filename = file_path.name
        files = {"file": (filename, data)}
        data_form = {"params": "{}"}

        # 1) 提交任务
        response = await client.post(url_tasks, files=files, data=data_form, timeout=30.0)
        result["status_code"] = response.status_code
        if response.status_code != 200:
            result["elapsed"] = round(time.perf_counter() - start, 3)
            result["error"] = response.text[:200]
            return result

        body = response.json()
        task_id = body.get("task_id")
        result["task_id"] = task_id

        # 仅测提交速度：到这里就结束
        if not wait_complete or not task_id:
            result["elapsed"] = round(time.perf_counter() - start, 3)
            return result

        # 2) 轮询任务状态，直到完成 / 失败 / 超时
        url_status = f"{base_url.rstrip('/')}/tasks/{task_id}"
        while True:
            now = time.perf_counter()
            if now - start > max_wait:
                result["elapsed"] = round(now - start, 3)
                result["task_status"] = "timeout"
                result["error"] = f"等待任务完成超时 (> {max_wait}s)"
                break

            try:
                r = await client.get(url_status, timeout=30.0)
                if r.status_code != 200:
                    result["elapsed"] = round(time.perf_counter() - start, 3)
                    result["task_status"] = f"http_{r.status_code}"
                    result["error"] = r.text[:200]
                    break

                data_status = r.json()
                status = data_status.get("status") or data_status.get("task_status")
                result["task_status"] = status

                if status in {"completed", "failed"}:
                    result["elapsed"] = round(time.perf_counter() - start, 3)
                    if status == "failed":
                        result["error"] = data_status.get("error") or data_status.get("status_message")
                    break

            except Exception as e:
                result["elapsed"] = round(time.perf_counter() - start, 3)
                result["error"] = f"轮询异常: {e}"
                break

            await asyncio.sleep(poll_interval)

    except Exception as e:
        result["elapsed"] = round(time.perf_counter() - start, 3)
        result["error"] = str(e)

    return result


async def run_concurrent(
    base_url: str,
    file_path: Path,
    concurrency: int,
    wait_complete: bool = False,
    poll_interval: float = 2.0,
    max_wait: float = 600.0,
) -> list:
    """并发发起 N 个请求，可选是否等到任务真正完成"""
    async with httpx.AsyncClient() as client:
        tasks = [
            submit_one(
                client,
                base_url,
                file_path,
                i + 1,
                wait_complete=wait_complete,
                poll_interval=poll_interval,
                max_wait=max_wait,
            )
            for i in range(concurrency)
        ]
        return await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(description="PySR 服务并发负载测试")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", help="服务根地址")
    parser.add_argument("--concurrency", "-n", type=int, default=30, help="并发请求数（默认 30）")
    parser.add_argument("--file", "-f", type=Path, default=None, help="上传的测试数据文件路径")
    parser.add_argument(
        "--wait-complete",
        action="store_true",
        help="是否等待每个任务真正完成（轮询 /tasks/{id}，适合测试真实分析耗时）",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=2.0,
        help="轮询任务状态的时间间隔秒，仅在 --wait-complete 时有效",
    )
    parser.add_argument(
        "--max-wait",
        type=float,
        default=600.0,
        help="单个任务允许的最大等待时间（秒），仅在 --wait-complete 时有效",
    )
    args = parser.parse_args()

    file_path = args.file or get_test_file_path()
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path
    if not file_path.exists():
        print(f"错误: 文件不存在 {file_path}")
        raise SystemExit(1)

    print(f"并发数: {args.concurrency}")
    print(f"服务地址: {args.base_url}")
    print(f"测试文件: {file_path}")
    if args.wait_complete:
        print("模式: 提交并等待任务完成（包含真实分析耗时）")
    else:
        print("模式: 仅测试任务提交速度（不等待分析完成）")

    wall_start = time.perf_counter()
    results = asyncio.run(
        run_concurrent(
            args.base_url,
            file_path,
            args.concurrency,
            wait_complete=args.wait_complete,
            poll_interval=args.poll_interval,
            max_wait=args.max_wait,
        )
    )
    wall_elapsed = time.perf_counter() - wall_start

    # 统计
    if args.wait_complete:
        ok = [r for r in results if r.get("task_status") == "completed" and r["error"] is None]
        err = [r for r in results if r["error"] or r.get("task_status") not in {None, "completed"}]
    else:
        ok = [r for r in results if r["status_code"] == 200 and r["error"] is None]
        err = [r for r in results if r["error"] or (r["status_code"] and r["status_code"] != 200)]
    times = [r["elapsed"] for r in results if r["elapsed"] is not None]

    print("\n" + "=" * 50)
    print("负载测试结果")
    print("=" * 50)
    print(f"总请求数:   {len(results)}")
    print(f"成功:       {len(ok)}")
    print(f"失败:       {len(err)}")
    print(f"总耗时:     {wall_elapsed:.2f} 秒")
    if times:
        print(f"响应时间:    min={min(times):.3f}s  max={max(times):.3f}s  avg={statistics.mean(times):.3f}s")
        if len(times) >= 2:
            print(f"标准差:      {statistics.stdev(times):.3f}s")
    if err:
        print("\n失败请求示例 (前 5 条):")
        for r in err[:5]:
            print(f"  用户 {r['user_id']}: status={r['status_code']} error={r['error']}")
    if ok:
        print("\n成功返回的 task_id 示例 (前 3 个):")
        for r in ok[:3]:
            print(f"  用户 {r['user_id']}: task_id={r['task_id']}")
    print("=" * 50)


if __name__ == "__main__":
    main()
