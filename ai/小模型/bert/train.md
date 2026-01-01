我来为您提供一个完整的中文意图分类模型训练方案，包括数据样例和可运行的代码。

## 1. 训练数据样例

首先创建一个数据文件 `intent_data.csv`：

```csv
text,label
我想查询一下我的账户余额,query_balance
帮我查一下银行卡余额,query_balance
我的账户还有多少钱,query_balance
我要转账给张三,transfer
请帮我转100元到李四账户,transfer
转账操作,transfer
我想投诉你们服务,complaint
对你们的服务很不满意,complaint
我要投诉客服态度不好,complaint
查询理财产品,query_financial
有什么投资产品推荐,query_financial
我想了解基金产品,query_financial
帮我订一张机票,book_ticket
预订明天去北京的飞机票,book_ticket
我想买机票,book_ticket
查询航班状态,query_flight
航班是否准点,query_flight
看看我的航班信息,query_flight
```

## 2. 安装依赖

```bash
pip install transformers datasets torch pandas sklearn
```

## 3. 完整训练代码

```python
import pandas as pd
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification, AdamW, get_linear_schedule_with_warmup
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import numpy as np
from tqdm import tqdm
import random

# 设置随机种子
seed = 42
random.seed(seed)
np.random.seed(seed)
torch.manual_seed(seed)
torch.cuda.manual_seed_all(seed)

class IntentDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
  
    def __len__(self):
        return len(self.texts)
  
    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]
      
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
      
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long)
        }

class IntentClassifier:
    def __init__(self, model_name='bert-base-chinese', num_labels=6, max_length=128):
        self.model_name = model_name
        self.num_labels = num_labels
        self.max_length = max_length
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertForSequenceClassification.from_pretrained(
            model_name, 
            num_labels=num_labels
        )
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
      
        self.label_encoder = {}
        self.label_decoder = {}
  
    def prepare_data(self, csv_file):
        # 读取数据
        df = pd.read_csv(csv_file)
      
        # 创建标签编码
        unique_labels = df['label'].unique()
        self.label_encoder = {label: idx for idx, label in enumerate(unique_labels)}
        self.label_decoder = {idx: label for label, idx in self.label_encoder.items()}
      
        # 编码标签
        df['label_encoded'] = df['label'].map(self.label_encoder)
      
        # 分割数据集
        train_texts, val_texts, train_labels, val_labels = train_test_split(
            df['text'].values,
            df['label_encoded'].values,
            test_size=0.2,
            random_state=42,
            stratify=df['label_encoded'].values
        )
      
        # 创建数据集
        train_dataset = IntentDataset(train_texts, train_labels, self.tokenizer, self.max_length)
        val_dataset = IntentDataset(val_texts, val_labels, self.tokenizer, self.max_length)
      
        return train_dataset, val_dataset
  
    def train(self, train_dataset, val_dataset, epochs=3, batch_size=16, learning_rate=2e-5):
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)
      
        optimizer = AdamW(self.model.parameters(), lr=learning_rate)
        total_steps = len(train_loader) * epochs
      
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=0,
            num_training_steps=total_steps
        )
      
        best_accuracy = 0
      
        for epoch in range(epochs):
            print(f'\nEpoch {epoch + 1}/{epochs}')
            print('-' * 50)
          
            # 训练阶段
            self.model.train()
            total_train_loss = 0
            train_correct = 0
            train_total = 0
          
            progress_bar = tqdm(train_loader, desc='Training')
            for batch in progress_bar:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
              
                self.model.zero_grad()
              
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
              
                loss = outputs.loss
                logits = outputs.logits
              
                total_train_loss += loss.item()
              
                predictions = torch.argmax(logits, dim=1)
                train_correct += (predictions == labels).sum().item()
                train_total += labels.size(0)
              
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
              
                progress_bar.set_postfix({
                    'loss': f'{loss.item():.4f}',
                    'acc': f'{train_correct/train_total:.4f}'
                })
          
            avg_train_loss = total_train_loss / len(train_loader)
            train_accuracy = train_correct / train_total
          
            # 验证阶段
            val_accuracy, val_report = self.evaluate(val_loader)
          
            print(f'训练损失: {avg_train_loss:.4f}')
            print(f'训练准确率: {train_accuracy:.4f}')
            print(f'验证准确率: {val_accuracy:.4f}')
            print('\n验证集分类报告:')
            print(val_report)
          
            # 保存最佳模型
            if val_accuracy > best_accuracy:
                best_accuracy = val_accuracy
                self.save_model('./best_intent_model')
                print(f'保存最佳模型，准确率: {best_accuracy:.4f}')
  
    def evaluate(self, dataloader):
        self.model.eval()
        predictions = []
        true_labels = []
      
        with torch.no_grad():
            for batch in dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['labels'].to(self.device)
              
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
              
                logits = outputs.logits
                batch_predictions = torch.argmax(logits, dim=1)
              
                predictions.extend(batch_predictions.cpu().numpy())
                true_labels.extend(labels.cpu().numpy())
      
        accuracy = accuracy_score(true_labels, predictions)
        report = classification_report(
            true_labels, 
            predictions, 
            target_names=[self.label_decoder[i] for i in range(len(self.label_decoder))],
            digits=4
        )
      
        return accuracy, report
  
    def predict(self, text):
        self.model.eval()
      
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
      
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
      
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            prediction = torch.argmax(logits, dim=1).cpu().numpy()[0]
      
        return self.label_decoder[prediction], torch.softmax(logits, dim=1).cpu().numpy()[0]
  
    def save_model(self, output_dir):
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
      
        # 保存标签映射
        import json
        with open(f'{output_dir}/label_mapping.json', 'w', encoding='utf-8') as f:
            json.dump({
                'label_encoder': self.label_encoder,
                'label_decoder': self.label_decoder
            }, f, ensure_ascii=False, indent=2)
  
    def load_model(self, model_dir):
        self.model = BertForSequenceClassification.from_pretrained(model_dir)
        self.tokenizer = BertTokenizer.from_pretrained(model_dir)
        self.model.to(self.device)
      
        # 加载标签映射
        import json
        with open(f'{model_dir}/label_mapping.json', 'r', encoding='utf-8') as f:
            label_mapping = json.load(f)
            self.label_encoder = label_mapping['label_encoder']
            self.label_decoder = {int(k): v for k, v in label_mapping['label_decoder'].items()}

# 训练模型
def main():
    # 初始化分类器
    classifier = IntentClassifier(num_labels=6, max_length=128)
  
    # 准备数据
    print("准备数据...")
    train_dataset, val_dataset = classifier.prepare_data('intent_data.csv')
  
    print(f"训练样本数: {len(train_dataset)}")
    print(f"验证样本数: {len(val_dataset)}")
    print(f"标签类别: {classifier.label_encoder}")
  
    # 训练模型
    print("开始训练...")
    classifier.train(
        train_dataset, 
        val_dataset, 
        epochs=3, 
        batch_size=16, 
        learning_rate=2e-5
    )

# 测试训练好的模型
def test_model():
    classifier = IntentClassifier()
    classifier.load_model('./best_intent_model')
  
    test_texts = [
        "帮我查一下余额",
        "我要转账100元",
        "有什么理财产品",
        "我要投诉服务问题",
        "预订去上海的机票",
        "航班什么时候到"
    ]
  
    print("\n测试预测结果:")
    for text in test_texts:
        intent, probabilities = classifier.predict(text)
        print(f"文本: '{text}' -> 意图: {intent}")
        print(f"各类别概率: {dict(zip([classifier.label_decoder[i] for i in range(len(classifier.label_decoder))], probabilities.round(4)))}")
        print()

if __name__ == "__main__":
    # 训练模型
    main()
  
    # 测试模型
    test_model()
```

## 4. 模型推理代码

```python
# inference.py
import torch
from transformers import BertForSequenceClassification, BertTokenizer
import json

class IntentPredictor:
    def __init__(self, model_path):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = BertForSequenceClassification.from_pretrained(model_path)
        self.tokenizer = BertTokenizer.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
      
        # 加载标签映射
        with open(f'{model_path}/label_mapping.json', 'r', encoding='utf-8') as f:
            label_mapping = json.load(f)
            self.label_decoder = {int(k): v for k, v in label_mapping['label_decoder'].items()}
  
    def predict(self, text, max_length=128):
        encoding = self.tokenizer(
            text,
            truncation=True,
            padding='max_length',
            max_length=max_length,
            return_tensors='pt'
        )
      
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
      
        with torch.no_grad():
            outputs = self.model(input_ids=input_ids, attention_mask=attention_mask)
            logits = outputs.logits
            probabilities = torch.softmax(logits, dim=1)
            prediction = torch.argmax(logits, dim=1).cpu().numpy()[0]
      
        intent = self.label_decoder[prediction]
        confidence = probabilities[0][prediction].cpu().numpy()
      
        return {
            'intent': intent,
            'confidence': float(confidence),
            'all_probabilities': {
                self.label_decoder[i]: float(prob)
                for i, prob in enumerate(probabilities[0].cpu().numpy())
            }
        }

# 使用示例
if __name__ == "__main__":
    predictor = IntentPredictor('./best_intent_model')
  
    while True:
        text = input("\n请输入文本（输入'quit'退出）: ")
        if text.lower() == 'quit':
            break
      
        result = predictor.predict(text)
        print(f"预测结果: {result}")
```

## 5. 运行说明

1. **准备数据**: 将第一个代码块中的数据保存为 `intent_data.csv`
2. **安装依赖**: 执行安装命令
3. **训练模型**: 运行主训练代码
4. **测试模型**: 代码会自动测试训练好的模型

## 6. 关键特点

- **使用bert-base-chinese预训练模型**
- **完整的数据预处理流程**
- **训练验证集分割**
- **自动保存最佳模型**
- **详细的训练日志和评估指标**
- **易于使用的预测接口**

这个方案可以直接运行，您可以根据实际需求调整数据、超参数和模型结构。训练完成后，模型会保存在 `best_intent_model` 目录中，可以用于生产环境部署。
