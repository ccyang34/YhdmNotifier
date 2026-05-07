#!/usr/bin/env python3
"""
验证小米模型参数是否正确识别
"""
import sys
import os

# 添加 Hermes Agent 的路径
sys.path.insert(0, '/opt/homebrew/lib/python3.13/site-packages')

print("=== 验证小米模型配置 ===")

try:
    from agent.models_dev import get_model_capabilities, fetch_models_dev
    
    print("\n1. 尝试获取模型能力...")
    caps = get_model_capabilities("xiaomi", "mimo-v2.5-pro")
    
    if caps:
        print(f"✓ 成功获取模型能力")
        print(f"  - Supports Tools: {caps.supports_tools}")
        print(f"  - Supports Vision: {caps.supports_vision}")
        print(f"  - Supports Reasoning: {caps.supports_reasoning}")
        print(f"  - Context Window: {caps.context_window:,}  tokens")
        print(f"  - Max Output: {caps.max_output_tokens:,} tokens")
        print(f"  - Model Family: {caps.model_family}")
        
        # 验证参数是否正确
        assert caps.context_window == 1048576, f"Context window 应为 1,048,576，实际是 {caps.context_window}"
        assert caps.max_output_tokens == 131072, f"Max output 应为 131,072，实际是 {caps.max_output_tokens}"
        
        print("\n✓ 所有参数验证通过！")
    else:
        print("✗ 无法获取模型能力")
    
    print("\n2. 检查模型 dev 缓存...")
    data = fetch_models_dev()
    xiaomi = data.get('xiaomi', {})
    
    if xiaomi:
        print(f"✓ 小米 provider 存在")
        models = xiaomi.get('models', {})
        if 'mimo-v2.5-pro' in models:
            print(f"✓ mimo-v2.5-pro 模型存在")
            model = models['mimo-v2.5-pro']
            limit = model.get('limit', {})
            print(f"  - Context from cache: {limit.get('context'):,}")
            print(f"  - Output from cache: {limit.get('output'):,}")
            print(f"  - Tool Call: {model.get('tool_call')}")
            print(f"  - Temperature: {model.get('temperature')}")
            print(f"  - Knowledge Cutoff: {model.get('knowledge')}")
            print(f"  - Release Date: {model.get('release_date')}")
            print(f"  - Modalities: {model.get('modalities')}")
    else:
        print("✗ 小米 provider 不存在于缓存中")
        
except Exception as e:
    print(f"✗ 验证失败: {e}")
    import traceback
    traceback.print_exc()

print("\n=== 验证完成 ===")
