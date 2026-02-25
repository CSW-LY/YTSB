#!/usr/bin/env python3
"""
测试修复后的update_rule函数（完整逻辑）
验证添加session.refresh(rule)后是否能解决过期错误
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db import async_session_maker
from app.models.database import IntentRule


async def test_update_rule_with_refresh():
    """
    测试带有session.refresh的更新规则功能
    模拟main_ui.py中的完整逻辑
    """
    print("开始测试 update_rule 修复（完整逻辑）...")
    print("=" * 60)
    
    async with async_session_maker() as session:
        try:
            # 1. 查找一个现有的规则
            print("1. 查找测试规则...")
            result = await session.execute(
                select(IntentRule).limit(1)
            )
            rule = result.scalar_one_or_none()
            
            if not rule:
                print("错误: 未找到测试规则")
                return False
            
            print(f"找到测试规则: ID={rule.id}, 内容={rule.content}")
            
            # 2. 模拟更新操作
            print("2. 模拟更新操作...")
            original_content = rule.content
            
            # 更新规则内容
            new_content = original_content + "_updated"
            setattr(rule, "content", new_content)
            
            # 3. 提交事务
            print("3. 提交事务...")
            await session.commit()
            
            # 4. 关键修复：刷新规则对象状态
            print("4. 刷新规则对象状态（关键修复步骤）...")
            await session.refresh(rule)
            
            # 5. 现在尝试访问updated_at字段
            print("5. 测试访问 updated_at 字段...")
            updated_at = rule.updated_at
            print(f"✓ 成功访问 updated_at: {updated_at}")
            
            # 6. 验证内容是否已更新
            print("6. 验证规则内容是否已更新...")
            print(f"   原始内容: {original_content}")
            print(f"   更新后内容: {rule.content}")
            
            if rule.content == new_content:
                print("✓ 规则内容更新成功")
            else:
                print("✗ 规则内容更新失败")
                return False
            
            # 7. 恢复原始内容
            print("7. 恢复原始内容...")
            setattr(rule, "content", original_content)
            await session.commit()
            await session.refresh(rule)  # 再次刷新
            print("✓ 原始内容已恢复")
            
            print("\n" + "=" * 60)
            print("测试成功! session.refresh 修复有效")
            return True
            
        except Exception as e:
            print(f"\n✗ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            await session.close()


async def main():
    """
    主函数
    """
    success = await test_update_rule_with_refresh()
    if success:
        print("\n🎉 所有测试通过!")
        print("修复方案：在session.commit()后添加await session.refresh(rule)")
        print("这样可以确保在访问updated_at等自动更新的字段时，对象状态是最新的")
    else:
        print("\n❌ 测试失败，修复可能未生效")
    return success


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        sys.exit(1)
