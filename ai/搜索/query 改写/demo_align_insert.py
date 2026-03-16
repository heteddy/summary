"""
演示 align_with_insert 方式的数据构建过程

运行此脚本查看训练数据和预测结果的详细示例
"""

import json
from macbert_query_rewrite_train import QueryRewriteDataBuilder, Predictor
from transformers import BertTokenizer

def demo_data_construction():
    """演示数据构建过程"""
    
    print("=" * 80)
    print("align_with_insert 方式训练数据构建演示")
    print("=" * 80)
    
    # 创建数据构建器
    builder = QueryRewriteDataBuilder(
        model_name="hfl/chinese-macbert-base",
        strategy="align_with_insert"
    )
    
    # 测试样例
    test_cases = [
        ("vpn 到期", "vpn 续费申请"),
        ("电脑登录不了", "电脑无法登录"),
        ("密码忘记了", "密码找回"),
        ("寿改", "寿险改革"),
        ("拧毛巾", "清洗毛巾"),
    ]
    
    for i, (original, target) in enumerate(test_cases, 1):
        print(f"\n{'='*80}")
        print(f"样例 {i}: '{original}' → '{target}'")
        print(f"{'='*80}")
        
        # 构建样本
        sample = builder.build_sample(original, target, max_length=64)
        
        # 显示分词结果
        print("\n【分词结果】")
        print(f"原始 tokens: {sample.get('orig_tokens', 'N/A')}")
        print(f"目标 tokens: {sample.get('tgt_tokens', 'N/A')}")
        
        # 显示对齐结果（如果有）
        if 'aligned_source' in sample:
            print("\n【对齐结果】")
            print(f"对齐后的源序列：{sample['aligned_source']}")
            print(f"对齐后的目标序列：{sample['aligned_target']}")
        
        # 显示操作类型（如果有）
        if 'operations' in sample:
            print("\n【操作类型】")
            for op_type, src_idx, tgt_idx in sample['operations']:
                if src_idx != -1 and src_idx < len(sample.get('orig_tokens', [])):
                    src_token = sample['orig_tokens'][src_idx]
                else:
                    src_token = "<INS>"
                
                if tgt_idx != -1 and tgt_idx < len(sample.get('tgt_tokens', [])):
                    tgt_token = sample['tgt_tokens'][tgt_idx]
                else:
                    tgt_token = "<DEL>"
                
                print(f"  {op_type:8s}: {src_token:6s} → {tgt_token:6s}")
        
        # 显示模型输入
        print("\n【模型输入格式】")
        input_ids = sample['input_ids']
        labels = sample['labels']
        attention_mask = sample['attention_mask']
        
        # 转换为 tokens 便于理解
        input_tokens = builder.tokenizer.convert_ids_to_tokens(input_ids)
        label_tokens = []
        for label_id in labels:
            if label_id == -100:
                label_tokens.append("[IGNORE]")
            else:
                token = builder.tokenizer.convert_ids_to_tokens([label_id])[0]
                label_tokens.append(token)
        
        print(f"\n{'位置':<6} {'Input Token':<15} {'Label Token':<15} {'Attention'}")
        print("-" * 60)
        for j in range(len(input_ids)):
            print(f"{j:<6} {input_tokens[j]:<15} {label_tokens[j]:<15} {attention_mask[j]}")
        
        # 统计信息
        print("\n【统计信息】")
        num_keep = sum(1 for l in labels if l != -100 and l in input_ids)
        num_replace = sum(1 for l in labels if l != -100 and l not in input_ids)
        num_delete = sum(1 for l in labels if l == -100)
        
        print(f"KEEP 操作数：{num_keep}")
        print(f"REPLACE 操作数：{num_replace}")
        print(f"DELETE/IGNORE 位置数：{num_delete}")
        print(f"序列长度：{len(input_ids)}")
    
    print(f"\n{'='*80}")
    print("演示完成！")
    print(f"{'='*80}")


def create_training_dataset():
    """创建完整的训练数据集示例"""
    
    print("\n创建训练数据集...")
    
    # 更多训练数据
    training_pairs = [
        ("vpn 到期", "vpn 续费申请"),
        ("电脑登录不了", "电脑无法登录"),
        ("密码忘记了", "密码找回"),
        ("怎么转账", "转账方法"),
        ("余额不足", "充值"),
        ("客服在哪", "联系客服"),
        ("订单取消", "取消订单"),
        ("退款进度", "退款查询"),
        ("寿改", "寿险改革"),
        ("拧毛巾", "清洗毛巾"),
        ("账号冻结", "解冻账号"),
        ("修改手机", "更换手机号"),
        ("忘记密码", "密码重置"),
        ("提额申请", "提升额度"),
        ("还款失败", "重新还款"),
    ]
    
    builder = QueryRewriteDataBuilder(
        model_name="hfl/chinese-macbert-base",
        strategy="align_with_insert"
    )
    
    dataset = []
    for orig, tgt in training_pairs:
        sample = builder.build_sample(orig, tgt, max_length=64)
        
        # 简化保存（只保留必要字段）
        simplified_sample = {
            "original_query": sample["original_query"],
            "target_query": sample["target_query"],
            "input_ids": sample["input_ids"],
            "labels": sample["labels"],
            "attention_mask": sample["attention_mask"]
        }
        dataset.append(simplified_sample)
    
    # 保存到文件
    output_file = "train_data_align_insert_example.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 训练数据集已保存到：{output_file}")
    print(f"✓ 数据集大小：{len(dataset)} 条")
    
    return output_file


def demo_prediction_process():
    """演示预测过程（模拟）"""
    
    print("\n" + "=" * 80)
    print("预测过程演示（模拟）")
    print("=" * 80)
    
    # 模拟预测结果
    prediction_examples = [
        {
            "input": "vpn 到期",
            "output": "vpn 续费申请",
            "confidence": 0.9234,
            "process": [
                "Step 1: 分词 -> ['vpn', '到', '期']",
                "Step 2: 模型编码 -> BERT 输出隐状态",
                "Step 3: 逐位置预测 -> [vpn_id, 续_id, 费_id, 申请_id]",
                "Step 4: 解码拼接 -> 'vpn 续费申请'"
            ]
        },
        {
            "input": "电脑登录不了",
            "output": "电脑无法登录",
            "confidence": 0.8956,
            "process": [
                "Step 1: 分词 -> ['电', '脑', '登', '录', '不', '了']",
                "Step 2: 模型编码 -> BERT 输出隐状态",
                "Step 3: 逐位置预测 -> [电_id, 脑_id, 无_id, 法_id, 登_id, 录_id]",
                "Step 4: 解码拼接 -> '电脑无法登录'"
            ]
        },
        {
            "input": "密码忘记了",
            "output": "密码找回",
            "confidence": 0.8721,
            "process": [
                "Step 1: 分词 -> ['密', '码', '忘', '记', '了']",
                "Step 2: 模型编码 -> BERT 输出隐状态",
                "Step 3: 逐位置预测 -> [密_id, 码_id, 找_id, 回_id, <DEL>_id]",
                "Step 4: 解码拼接 -> '密码找回'"
            ]
        }
    ]
    
    for i, example in enumerate(prediction_examples, 1):
        print(f"\n【预测示例 {i}】")
        print(f"输入：{example['input']}")
        print(f"输出：{example['output']}")
        print(f"置信度：{example['confidence']:.4f}")
        print("\n详细过程:")
        for step in example['process']:
            print(f"  {step}")


if __name__ == "__main__":
    import sys
    
    print("\nMacBERT 查询改写 - align_with_insert 方式演示\n")
    
    # 检查是否提供了模型路径
    if len(sys.argv) > 1:
        model_path = sys.argv[1]
        print(f"使用模型路径：{model_path}")
        
        # 加载真实模型进行预测
        try:
            predictor = Predictor(model_path)
            
            test_queries = ["vpn 到期", "电脑登录不了", "密码忘记了"]
            
            print("\n真实模型预测结果:")
            for query in test_queries:
                rewritten, confidence = predictor.predict(query)
                print(f"  {query:15s} → {rewritten:20s} (置信度：{confidence:.4f})")
        
        except Exception as e:
            print(f"加载模型失败：{e}")
            print("将运行模拟演示...")
    
    # 运行演示
    print("\n运行数据构建演示...\n")
    demo_data_construction()
    
    print("\n创建训练数据集...\n")
    create_training_dataset()
    
    print("\n运行预测过程演示...\n")
    demo_prediction_process()
    
    print("\n" + "=" * 80)
    print("所有演示完成！")
    print("=" * 80)
    print("\n下一步:")
    print("1. 查看生成的训练数据文件")
    print("2. 使用真实数据训练模型")
    print("3. 运行真实预测测试")
    print()
