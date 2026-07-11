"""
MinerU 解析器测试
支持 PDF、Word、Excel 三种格式
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.parser.mineru_parser import MinerUParser


async def test_parser():
    """测试解析器"""
    print("=" * 50)
    print("MinerU 解析器测试")
    print("=" * 50)

    # 获取文件路径
    file_path = input("\n请输入文件路径（支持 PDF/Word/Excel）: ").strip()

    # 去除引号（用户可能复制了带引号的路径）
    file_path = file_path.strip('"').strip("'")

    # 检查文件是否存在
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return

    # 获取文件类型
    file_ext = os.path.splitext(file_path)[1].lower().replace(".", "")
    print(f"\n📄 文件类型: {file_ext}")

    # 检查是否支持
    parser = MinerUParser()
    supported = parser.supported_types()
    if file_ext not in supported:
        print(f"❌ 不支持的文件类型: {file_ext}")
        print(f"   支持的类型: {', '.join(supported)}")
        return

    # 解析文件
    print(f"\n⏳ 正在解析文件...")
    try:
        result = await parser.parse(file_path, file_id=1)

        print(f"\n✅ 解析成功!")
        print(f"   文件名: {result.file_name}")
        print(f"   文件类型: {result.file_type}")
        print(f"   内容长度: {len(result.content)} 字符")
        print(f"\n📋 MinIO 信息:")
        print(f"   原始文件: {result.metadata.get('minio_key', 'N/A')}")
        print(f"   解析文件: {result.metadata.get('parsed_minio_key', 'N/A')}")
        print(f"   图片数量: {len(result.metadata.get('parsed_images', []))}")

        # 显示内容预览
        preview = result.content[:500] + "..." if len(result.content) > 500 else result.content
        print(f"\n📝 内容预览:")
        print("-" * 50)
        print(preview)
        print("-" * 50)

    except Exception as e:
        print(f"\n❌ 解析失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_parser())
