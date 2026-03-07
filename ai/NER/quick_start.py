"""
快速启动示例

演示如何使用 MacBERT + 指针网络 NER 模型进行训练和预测
"""

import json
from data_processor import NERDataProcessor, split_dataset, save_data


def prepare_data():
    """准备训练数据"""
    print("=" * 60)
    print("步骤 1: 准备训练数据")
    print("=" * 60)
    
    # 示例训练数据 (实际使用时应该从 macbert_pointer_ner_data.md 加载完整数据)
    sample_data = [
        {
            "text": "张三在阿里巴巴技术部担任软件工程师",
            "entities": [
                {"type": "ORGANIZATION", "start": 3, "end": 7, "text": "阿里巴巴"},
                {"type": "DEPARTMENT", "start": 7, "end": 10, "text": "技术部"},
                {"type": "POSITION", "start": 13, "end": 18, "text": "软件工程师"}
            ]
        },
        {
            "text": "李四是腾讯科技产品部的高级产品经理",
            "entities": [
                {"type": "ORGANIZATION", "start": 3, "end": 7, "text": "腾讯科技"},
                {"type": "DEPARTMENT", "start": 7, "end": 10, "text": "产品部"},
                {"type": "POSITION", "start": 13, "end": 17, "text": "高级产品经理"}
            ]
        },
        {
            "text": "王五在华为云技术服务部工作",
            "entities": [
                {"type": "ORGANIZATION", "start": 3, "end": 6, "text": "华为云"},
                {"type": "DEPARTMENT", "start": 6, "end": 10, "text": "技术服务部"}
            ]
        },
        {
            "text": "赵六是字节跳动研发中心的算法工程师",
            "entities": [
                {"type": "ORGANIZATION", "start": 3, "end": 7, "text": "字节跳动"},
                {"type": "DEPARTMENT", "start": 7, "end": 11, "text": "研发中心"},
                {"type": "POSITION", "start": 14, "end": 19, "text": "算法工程师"}
            ]
        },
        {
            "text": "孙七担任美团外卖事业群技术负责人",
            "entities": [
                {"type": "ORGANIZATION", "start": 4, "end": 6, "text": "美团"},
                {"type": "DEPARTMENT", "start": 6, "end": 11, "text": "外卖事业群"},
                {"type": "POSITION", "start": 11, "end": 15, "text": "技术负责人"}
            ]
        }
    ]
    
    # 保存完整数据
    with open('ner_all_data.json', 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, ensure_ascii=False, indent=2)
    
    print(f"✓ 已加载 {len(sample_data)} 条训练数据")
    
    # 划分数据集
    train_data, dev_data, test_data = split_dataset(sample_data, train_ratio=0.6, dev_ratio=0.2)
    
    # 保存划分后的数据
    save_data(train_data, 'ner_train.json')
    save_data(dev_data, 'ner_dev.json')
    save_data(test_data, 'ner_test.json')
    
    print(f"✓ 训练集：{len(train_data)} 条")
    print(f"✓ 验证集：{len(dev_data)} 条")
    print(f"✓ 测试集：{len(test_data)} 条")
    print()


def show_training_command():
    """显示训练命令"""
    print("=" * 60)
    print("步骤 2: 训练模型")
    print("=" * 60)
    print("\n运行以下命令开始训练:\n")
    print("python train.py \\")
    print("  --train_file ner_train.json \\")
    print("  --dev_file ner_dev.json \\")
    print("  --model_name hfl/chinese-macbert-base \\")
    print("  --batch_size 8 \\")
    print("  --num_epochs 10 \\")
    print("  --learning_rate 3e-5 \\")
    print("  --output_dir ./outputs\n")
    print("注意: 首次运行时会自动下载 MacBERT 模型 (~400MB)")
    print()


def show_prediction_examples():
    """显示预测示例"""
    print("=" * 60)
    print("步骤 3: 使用模型进行预测")
    print("=" * 60)
    print("\n预测单个文本:")
    print("python predict.py \\")
    print("  --model_path ./outputs \\")
    print("  --text \"张三在百度云计算部门担任架构师\"\n")
    
    print("\n批量预测:")
    print("python predict.py \\")
    print("  --model_path ./outputs \\")
    print("  --file input.txt \\")
    print("  --output predictions.json\n")
    
    print("\n交互模式:")
    print("python predict.py --model_path ./outputs\n")
    
    # 示例预测结果
    print("\n" + "=" * 60)
    print("预测结果示例:")
    print("=" * 60)
    
    example_text = "张三在百度云计算部门担任架构师"
    example_entities = [
        {
            "type": "ORGANIZATION",
            "start": 3,
            "end": 5,
            "text": "百度",
            "confidence": 0.95
        },
        {
            "type": "DEPARTMENT",
            "start": 5,
            "end": 9,
            "text": "云计算部门",
            "confidence": 0.92
        },
        {
            "type": "POSITION",
            "start": 12,
            "end": 15,
            "text": "架构师",
            "confidence": 0.88
        }
    ]
    
    print(f"\n输入文本：{example_text}")
    print("\n识别到的实体:")
    for entity in example_entities:
        print(f"  - {entity['text']} ({entity['type']}) - 置信度：{entity['confidence']:.2f}")
    print()


def show_api_usage():
    """显示 Python API 使用方法"""
    print("=" * 60)
    print("Python API 使用示例")
    print("=" * 60)
    print("""
# 导入必要的模块
from predict import NERPredictor

# 创建预测器
predictor = NERPredictor(
    model_path='./outputs',
    model_name='hfl/chinese-macbert-base'
)

# 预测单个文本
text = "李四在阿里巴巴达摩院担任 AI 科学家"
entities = predictor.predict(text)

print(f"输入：{text}")
print("识别到的实体:")
for entity in entities:
    print(f"  - {entity['text']} ({entity['type']}) - 置信度：{entity['confidence']:.2f}")

# 批量预测
texts = [
    "王五是腾讯科技微信事业群的产品经理",
    "赵六在京东零售技术研发部工作",
    "孙七担任字节跳动抖音事业部总经理"
]

all_entities = predictor.predict_batch(texts)

for text, entities in zip(texts, all_entities):
    print(f"\\n输入：{text}")
    for entity in entities:
        print(f"  - {entity['text']} ({entity['type']})")

# 可视化输出
colored_text = predictor.visualize(text, entities)
print(colored_text)
""")
    print()


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("MacBERT + 指针网络 NER - 快速入门指南")
    print("=" * 60)
    print()
    
    # 准备数据
    prepare_data()
    
    # 显示训练命令
    show_training_command()
    
    # 显示预测示例
    show_prediction_examples()
    
    # 显示 API 使用方法
    show_api_usage()
    
    print("=" * 60)
    print("下一步操作:")
    print("=" * 60)
    print("1. 查看 README.md 了解详细说明")
    print("2. 运行 train.py 开始训练")
    print("3. 使用 predict.py 进行预测")
    print("4. 参考 macbert_pointer_ner_data.md 获取更多训练数据")
    print()


if __name__ == '__main__':
    main()
