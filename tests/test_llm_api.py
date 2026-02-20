# 导入所需库
from openai import OpenAI

# 配置你的API信息（直接替换为你提供的参数）
API_KEY = "930ebd9a476b485b997317bfccd8c498.geoZsTpKY84dVVh5"
BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
MODEL = "glm-4-flash"

def test_glm_api():
    """测试GLM API配置是否有效"""
    try:
        # 初始化客户端
        client = OpenAI(
            api_key=API_KEY,
            base_url=BASE_URL
        )
        
        # 发送测试请求（简单的问答）
        print("正在发送测试请求...")
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "user", "content": "你好，请确认接口调用成功，回复一句话即可"}
            ],
            temperature=0.7,  # 生成温度，控制随机性
            max_tokens=100     # 最大生成token数
        )
        
        # 检查返回结果是否包含错误
        if hasattr(completion, 'success') and not completion.success:
            print("❌ API调用失败！返回错误信息：")
            if hasattr(completion, 'code'):
                print(f"   错误代码：{completion.code}")
            if hasattr(completion, 'msg'):
                print(f"   错误信息：{completion.msg}")
        else:
            # 打印返回结果结构
            print("✅ API配置有效！接口调用成功！")
            print("返回结果类型：", type(completion))
            print("返回结果：", completion)
            
            # 尝试访问模型回复
            if hasattr(completion, 'choices') and completion.choices:
                print("choices存在且不为空")
                if hasattr(completion.choices[0], 'message') and completion.choices[0].message:
                    print("message存在且不为空")
                    if hasattr(completion.choices[0].message, 'content') and completion.choices[0].message.content:
                        print("📝 模型回复：", completion.choices[0].message.content.strip())
                    else:
                        print("⚠️ message.content为空或不存在")
                else:
                    print("⚠️ message为空或不存在")
            else:
                print("⚠️ choices为空或不存在")
        
    except Exception as e:
        # 捕获并打印错误信息
        print("❌ API调用失败！错误信息：")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n可能的原因：")
        print("   1. API_KEY错误或已过期")
        print("   2. BASE_URL填写错误")
        print("   3. MODEL名称不正确（如glm-4-flash是否存在）")
        print("   4. 网络问题或API服务暂时不可用")

if __name__ == "__main__":
    test_glm_api()
