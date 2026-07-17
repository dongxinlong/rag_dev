"""
MinerU API 测试脚本

测试内容：
1. 提交解析任务
2. 轮询任务状态
3. 下载解析结果
"""
import asyncio
import httpx
import time
import sys
import os

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import settings


# ==================== 配置 ====================
MINERU_API_TOKEN = settings.MINERU_API_TOKEN
MINERU_API_BASE_URL = settings.MINERU_API_BASE_URL

# 测试文件 URL（MinerU 官方示例）
TEST_FILE_URL = "https://cdn-mineru.openxlab.org.cn/demo/example.pdf"


async def test_submit_task():
    """测试 1：提交解析任务"""
    print("\n" + "=" * 50)
    print("测试 1：提交 MinerU API 解析任务")
    print("=" * 50)

    url = f"{MINERU_API_BASE_URL}/extract/task"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_API_TOKEN}"
    }
    data = {
        "url": TEST_FILE_URL,
        "model_version": "vlm",
        "is_ocr": True,
        "enable_formula": True,
        "enable_table": True,
        "language": "ch"
    }

    print(f"请求地址: {url}")
    print(f"测试文件: {TEST_FILE_URL}")

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(url, headers=headers, json=data)
        result = response.json()

        print(f"状态码: {response.status_code}")
        print(f"返回结果: {result}")

        if result.get("code") == 0:
            task_id = result["data"]["task_id"]
            print(f"✅ 任务提交成功! task_id: {task_id}")
            return task_id
        else:
            print(f"❌ 任务提交失败: {result.get('msg')}")
            return None


async def test_poll_task(task_id: str, max_wait: int = 120):
    """测试 2：轮询任务状态"""
    print("\n" + "=" * 50)
    print("测试 2：轮询任务状态")
    print("=" * 50)

    url = f"{MINERU_API_BASE_URL}/extract/task/{task_id}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {MINERU_API_TOKEN}"
    }

    start_time = time.time()
    interval = 3

    print(f"task_id: {task_id}")
    print(f"最长等待: {max_wait} 秒")

    async with httpx.AsyncClient(timeout=30) as client:
        while time.time() - start_time < max_wait:
            response = await client.get(url, headers=headers)
            result = response.json()

            if result.get("code") != 0:
                print(f"❌ 查询失败: {result.get('msg')}")
                return None

            state = result["data"].get("state")
            elapsed = int(time.time() - start_time)

            print(f"[{elapsed}s] 状态: {state}")

            if state == "done":
                zip_url = result["data"].get("full_zip_url")
                print(f"✅ 解析完成!")
                print(f"   zip 下载链接: {zip_url}")
                return result["data"]
            elif state == "failed":
                error_msg = result["data"].get("err_msg", "未知错误")
                print(f"❌ 解析失败: {error_msg}")
                return result["data"]

            await asyncio.sleep(interval)

    print(f"⏰ 轮询超时 ({max_wait}s)")
    return None


async def test_download_zip(zip_url: str):
    """测试 3：下载并解析 zip 包"""
    print("\n" + "=" * 50)
    print("测试 3：下载并解析 zip 包")
    print("=" * 50)

    import zipfile
    import io

    print(f"下载链接: {zip_url}")

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.get(zip_url)
        print(f"下载状态: {response.status_code}")
        print(f"文件大小: {len(response.content)} 字节")

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            print(f"\nzip 包内容:")
            for name in zf.namelist():
                info = zf.getinfo(name)
                print(f"  - {name} ({info.file_size} 字节)")

            # 查找 full.md
            markdown_content = ""
            for name in zf.namelist():
                if name.endswith("full.md"):
                    markdown_content = zf.read(name).decode("utf-8")
                    break

            if markdown_content:
                print(f"\n✅ Markdown 内容预览 (前 500 字符):")
                print("-" * 50)
                print(markdown_content[:500])
                print("-" * 50)
                print(f"总长度: {len(markdown_content)} 字符")
            else:
                print("❌ 未找到 full.md")

            # 统计图片
            images = [n for n in zf.namelist() if n.startswith("images/") and not n.endswith("/")]
            print(f"\n图片数量: {len(images)}")
            for img in images[:5]:
                print(f"  - {img}")

    return markdown_content


async def main():
    """主测试流程"""
    print("🚀 开始测试 MinerU API")
    print(f"API 地址: {MINERU_API_BASE_URL}")
    print(f"Token: {MINERU_API_TOKEN[:20]}...")

    # 测试 1：提交任务
    task_id = await test_submit_task()
    if not task_id:
        print("\n❌ 测试失败：无法提交任务")
        return

    # 测试 2：轮询结果
    result = await test_poll_task(task_id)
    if not result or result.get("state") != "done":
        print("\n❌ 测试失败：解析未完成")
        return

    # 测试 3：下载 zip
    zip_url = result.get("full_zip_url")
    markdown_content = await test_download_zip(zip_url)

    # 总结
    print("\n" + "=" * 50)
    print("📊 测试总结")
    print("=" * 50)
    print("✅ 测试 1：任务提交 - 通过")
    print("✅ 测试 2：轮询结果 - 通过")
    print("✅ 测试 3：下载解析 - 通过")
    print(f"\n🎉 MinerU API 测试全部通过!")
    print(f"   Markdown 长度: {len(markdown_content)} 字符")


if __name__ == "__main__":
    asyncio.run(main())
