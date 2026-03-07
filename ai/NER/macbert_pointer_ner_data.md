# MacBERT + 指针网络 NER 训练数据

## 数据说明

本数据集用于训练基于 MacBERT + 指针网络 (Pointer Network) 的命名实体识别模型，专门用于识别企业内部的公司、部门、岗位三类实体。

### 实体类型定义

1. **公司 (ORGANIZATION)**: 企业、子公司、集团名称
   - 示例：阿里巴巴、腾讯科技、华为技术有限公司
   
2. **部门 (DEPARTMENT)**: 内部组织机构
   - 示例：技术部、人力资源部、财务部、研发中心
   
3. **岗位 (POSITION)**: 职位、头衔
   - 示例：软件工程师、产品经理、总监、经理

---

## 训练数据格式

### JSON 格式 (推荐)

```json
{
  "text": "张三在阿里巴巴技术部担任软件工程师",
  "entities": [
    {
      "type": "ORGANIZATION",
      "start": 3,
      "end": 7,
      "text": "阿里巴巴"
    },
    {
      "type": "DEPARTMENT",
      "start": 7,
      "end": 10,
      "text": "技术部"
    },
    {
      "type": "POSITION",
      "start": 13,
      "end": 18,
      "text": "软件工程师"
    }
  ]
}
```

**字段说明**:
- `text`: 原始文本
- `entities`: 实体列表
  - `type`: 实体类型 (ORGANIZATION/DEPARTMENT/POSITION)
  - `start`: 实体起始位置索引 (包含，从 0 开始)
  - `end`: 实体结束位置索引 (不包含)
  - `text`: 实体文本内容

---

## 训练数据示例

### 示例 1: 简单实体
```json
{
  "text": "李四在腾讯科技研发中心工作",
  "entities": [
    {
      "type": "ORGANIZATION",
      "start": 3,
      "end": 7,
      "text": "腾讯科技"
    },
    {
      "type": "DEPARTMENT",
      "start": 7,
      "end": 11,
      "text": "研发中心"
    }
  ]
}
```

### 示例 2: 嵌套实体
```json
{
  "text": "华为技术有限公司云计算部门首席架构师王五",
  "entities": [
    {
      "type": "ORGANIZATION",
      "start": 0,
      "end": 9,
      "text": "华为技术有限公司"
    },
    {
      "type": "DEPARTMENT",
      "start": 9,
      "end": 14,
      "text": "云计算部门"
    },
    {
      "type": "POSITION",
      "start": 14,
      "end": 20,
      "text": "首席架构师"
    }
  ]
}
```

### 示例 3: 多实体
```json
{
  "text": "张三和李四分别在百度市场部和字节跳动产品部任职",
  "entities": [
    {
      "type": "ORGANIZATION",
      "start": 5,
      "end": 7,
      "text": "百度"
    },
    {
      "type": "DEPARTMENT",
      "start": 7,
      "end": 10,
      "text": "市场部"
    },
    {
      "type": "ORGANIZATION",
      "start": 13,
      "end": 17,
      "text": "字节跳动"
    },
    {
      "type": "DEPARTMENT",
      "start": 17,
      "end": 20,
      "text": "产品部"
    }
  ]
}
```

### 示例 4: 复杂场景
```json
{
  "text": "2023 年，京东集团人力资源副总裁赵六在北京总部接待了阿里巴巴菜鸟网络物流事业部总经理",
  "entities": [
    {
      "type": "ORGANIZATION",
      "start": 4,
      "end": 8,
      "text": "京东集团"
    },
    {
      "type": "DEPARTMENT",
      "start": 8,
      "end": 13,
      "text": "人力资源"
    },
    {
      "type": "POSITION",
      "start": 13,
      "end": 17,
      "text": "副总裁"
    },
    {
      "type": "ORGANIZATION",
      "start": 23,
      "end": 27,
      "text": "阿里巴巴"
    },
    {
      "type": "ORGANIZATION",
      "start": 27,
      "end": 31,
      "text": "菜鸟网络"
    },
    {
      "type": "DEPARTMENT",
      "start": 31,
      "end": 36,
      "text": "物流事业部"
    },
    {
      "type": "POSITION",
      "start": 36,
      "end": 40,
      "text": "总经理"
    }
  ]
}
```

---

## 完整训练数据集

以下是 100 条训练数据示例，涵盖各种场景:

```json
[
  {
    "text": "张三在阿里巴巴技术部担任软件工程师",
    "entities": [
      {"type": "ORGANIZATION", "start": 3, "end": 7, "text": "阿里巴巴"},
      {"type": "DEPARTMENT", "start": 7, "end": 10, "text": "技术部"},
      {"type": "POSITION", "start": 13, "end": 18, "text": "软件工程师"}
    ]
  },
  {
    "text": "李四是腾讯科技产品经理",
    "entities": [
      {"type": "ORGANIZATION", "start": 3, "end": 7, "text": "腾讯科技"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "产品经理"}
    ]
  },
  {
    "text": "王五在华为研发中心工作",
    "entities": [
      {"type": "ORGANIZATION", "start": 3, "end": 5, "text": "华为"},
      {"type": "DEPARTMENT", "start": 5, "end": 9, "text": "研发中心"}
    ]
  },
  {
    "text": "百度云计算部门的算法工程师赵六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 2, "text": "百度"},
      {"type": "DEPARTMENT", "start": 2, "end": 6, "text": "云计算部门"},
      {"type": "POSITION", "start": 9, "end": 14, "text": "算法工程师"}
    ]
  },
  {
    "text": "字节跳动运营部总监孙七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "字节跳动"},
      {"type": "DEPARTMENT", "start": 4, "end": 7, "text": "运营部"},
      {"type": "POSITION", "start": 7, "end": 9, "text": "总监"}
    ]
  },
  {
    "text": "美团外卖事业群技术负责人周八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 2, "text": "美团"},
      {"type": "DEPARTMENT", "start": 2, "end": 7, "text": "外卖事业群"},
      {"type": "POSITION", "start": 7, "end": 11, "text": "技术负责人"}
    ]
  },
  {
    "text": "网易游戏事业部高级项目经理吴九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 2, "text": "网易"},
      {"type": "DEPARTMENT", "start": 2, "end": 7, "text": "游戏事业部"},
      {"type": "POSITION", "start": 7, "end": 13, "text": "高级项目经理"}
    ]
  },
  {
    "text": "小米科技手机部产品总监郑十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "小米科技"},
      {"type": "DEPARTMENT", "start": 4, "end": 7, "text": "手机部"},
      {"type": "POSITION", "start": 7, "end": 11, "text": "产品总监"}
    ]
  },
  {
    "text": "滴滴出行安全监察部总经理王十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "滴滴出行"},
      {"type": "DEPARTMENT", "start": 4, "end": 9, "text": "安全监察部"},
      {"type": "POSITION", "start": 9, "end": 12, "text": "总经理"}
    ]
  },
  {
    "text": "京东物流供应链管理部副总裁李十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "京东物流"},
      {"type": "DEPARTMENT", "start": 4, "end": 9, "text": "供应链管理部"},
      {"type": "POSITION", "start": 9, "end": 12, "text": "副总裁"}
    ]
  },
  {
    "text": "拼多多电商平台技术总监张十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "拼多多"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "电商平台"},
      {"type": "POSITION", "start": 7, "end": 11, "text": "技术总监"}
    ]
  },
  {
    "text": "快手科技内容审核部经理刘十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "快手科技"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "内容审核部"},
      {"type": "POSITION", "start": 8, "end": 10, "text": "经理"}
    ]
  },
  {
    "text": "哔哩哔哩社区运营主管陈十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "哔哩哔哩"},
      {"type": "DEPARTMENT", "start": 4, "end": 6, "text": "社区"},
      {"type": "POSITION", "start": 6, "end": 10, "text": "运营主管"}
    ]
  },
  {
    "text": "知乎内容生产部资深编辑杨十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 2, "text": "知乎"},
      {"type": "DEPARTMENT", "start": 2, "end": 6, "text": "内容生产部"},
      {"type": "POSITION", "start": 6, "end": 10, "text": "资深编辑"}
    ]
  },
  {
    "text": "微博社交媒体事业部市场总监何十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 2, "text": "微博"},
      {"type": "DEPARTMENT", "start": 2, "end": 8, "text": "社交媒体事业部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "市场总监"}
    ]
  },
  {
    "text": "蚂蚁金服金融科技事业群总裁林十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "蚂蚁金服"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "金融科技事业群"},
      {"type": "POSITION", "start": 10, "end": 12, "text": "总裁"}
    ]
  },
  {
    "text": "阿里云智能计算研究院院长钱十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "阿里云"},
      {"type": "DEPARTMENT", "start": 3, "end": 9, "text": "智能计算研究院"},
      {"type": "POSITION", "start": 9, "end": 11, "text": "院长"}
    ]
  },
  {
    "text": "腾讯云产品开发部测试工程师孙二十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "腾讯云"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "产品开发部"},
      {"type": "POSITION", "start": 10, "end": 14, "text": "测试工程师"}
    ]
  },
  {
    "text": "华为云技术服务部技术支持专家李二十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "华为云"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "技术服务部"},
      {"type": "POSITION", "start": 10, "end": 15, "text": "技术支持专家"}
    ]
  },
  {
    "text": "百度智能云 AI 平台部算法科学家王二十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 5, "text": "百度智能云"},
      {"type": "DEPARTMENT", "start": 5, "end": 9, "text": "AI 平台部"},
      {"type": "POSITION", "start": 9, "end": 14, "text": "算法科学家"}
    ]
  },
  {
    "text": "平安集团保险事业部财务总监赵二十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "平安集团"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "保险事业部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "财务总监"}
    ]
  },
  {
    "text": "招商银行零售银行部客户经理钱二十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "招商银行"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "零售银行部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "客户经理"}
    ]
  },
  {
    "text": "中国平安人寿保险事业部总经理孙二十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "中国平安"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "人寿保险事业部"},
      {"type": "POSITION", "start": 10, "end": 13, "text": "总经理"}
    ]
  },
  {
    "text": "万科地产项目管理部工程总监李二十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "万科地产"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "项目管理部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "工程总监"}
    ]
  },
  {
    "text": "恒大集团财务管理部会计主管王二十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "恒大集团"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "财务管理部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "会计主管"}
    ]
  },
  {
    "text": "碧桂园设计研究院建筑设计师赵二十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "碧桂园"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "设计研究院"},
      {"type": "POSITION", "start": 7, "end": 12, "text": "建筑设计师"}
    ]
  },
  {
    "text": "中海地产营销策划部市场经理孙二十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "中海地产"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "营销策划部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "市场经理"}
    ]
  },
  {
    "text": "华润置地商业管理部招商总监李三十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "华润置地"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "商业管理部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "招商总监"}
    ]
  },
  {
    "text": "国家电网电力调度中心总工程师王三十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "国家电网"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "电力调度中心"},
      {"type": "POSITION", "start": 10, "end": 14, "text": "总工程师"}
    ]
  },
  {
    "text": "中石化石油化工研究院研究员李三十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "中石化"},
      {"type": "DEPARTMENT", "start": 3, "end": 9, "text": "石油化工研究院"},
      {"type": "POSITION", "start": 9, "end": 11, "text": "研究员"}
    ]
  },
  {
    "text": "中石油勘探开发部地质工程师赵三十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "中石油"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "勘探开发部"},
      {"type": "POSITION", "start": 7, "end": 12, "text": "地质工程师"}
    ]
  },
  {
    "text": "中国移动通信技术研发部高级工程师孙三十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "中国移动"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "通信技术研发部"},
      {"type": "POSITION", "start": 10, "end": 14, "text": "高级工程师"}
    ]
  },
  {
    "text": "中国联通网络运维部运维总监李三十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "中国联通"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "网络运维部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "运维总监"}
    ]
  },
  {
    "text": "中国电信云计算分公司总经理王三十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "中国电信"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "云计算分公司"},
      {"type": "POSITION", "start": 10, "end": 13, "text": "总经理"}
    ]
  },
  {
    "text": "上汽集团研发总院自动驾驶总监赵三十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "上汽集团"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "研发总院"},
      {"type": "POSITION", "start": 8, "end": 14, "text": "自动驾驶总监"}
    ]
  },
  {
    "text": "比亚迪汽车工程院电池工程师李三十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "比亚迪"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "汽车工程院"},
      {"type": "POSITION", "start": 7, "end": 12, "text": "电池工程师"}
    ]
  },
  {
    "text": "吉利汽车研究院整车集成总监王三十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "吉利汽车"},
      {"type": "DEPARTMENT", "start": 4, "end": 7, "text": "研究院"},
      {"type": "POSITION", "start": 7, "end": 13, "text": "整车集成总监"}
    ]
  },
  {
    "text": "长城汽车技术中心动力总成经理赵四十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "长城汽车"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "技术中心"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "动力总成经理"}
    ]
  },
  {
    "text": "蔚来汽车用户发展部运营副总裁李四十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "蔚来汽车"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "用户发展部"},
      {"type": "POSITION", "start": 8, "end": 13, "text": "运营副总裁"}
    ]
  },
  {
    "text": "小鹏汽车智能驾驶研究院算法总监王四十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "小鹏汽车"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "智能驾驶研究院"},
      {"type": "POSITION", "start": 10, "end": 14, "text": "算法总监"}
    ]
  },
  {
    "text": "理想汽车产品规划部产品总监赵四十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "理想汽车"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "产品规划部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "产品总监"}
    ]
  },
  {
    "text": "富士康科技集团制造事业部总经理李四十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 7, "text": "富士康科技集团"},
      {"type": "DEPARTMENT", "start": 7, "end": 11, "text": "制造事业部"},
      {"type": "POSITION", "start": 11, "end": 14, "text": "总经理"}
    ]
  },
  {
    "text": "台积电中国有限公司技术副总王四十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 9, "text": "台积电中国有限公司"},
      {"type": "POSITION", "start": 9, "end": 13, "text": "技术副总"}
    ]
  },
  {
    "text": "英特尔亚太研发有限公司软件架构师赵四十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 11, "text": "英特尔亚太研发有限公司"},
      {"type": "POSITION", "start": 11, "end": 16, "text": "软件架构师"}
    ]
  },
  {
    "text": "AMD 中国技术中心硬件工程师李四十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 7, "text": "AMD 中国技术中心"},
      {"type": "POSITION", "start": 7, "end": 12, "text": "硬件工程师"}
    ]
  },
  {
    "text": "英伟达 AI 研究中心深度学习科学家王四十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 7, "text": "英伟达 AI 研究中心"},
      {"type": "POSITION", "start": 7, "end": 13, "text": "深度学习科学家"}
    ]
  },
  {
    "text": "高通通信技术公司射频工程师赵四十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 9, "text": "高通通信技术公司"},
      {"type": "POSITION", "start": 9, "end": 14, "text": "射频工程师"}
    ]
  },
  {
    "text": "联发科无线事业部芯片设计总监李五十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "联发科"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "无线事业部"},
      {"type": "POSITION", "start": 7, "end": 11, "text": "芯片设计总监"}
    ]
  },
  {
    "text": "海思半导体集成电路设计工程师王五十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 5, "text": "海思半导体"},
      {"type": "POSITION", "start": 5, "end": 11, "text": "集成电路设计工程师"}
    ]
  },
  {
    "text": "紫光集团存储事业部技术副总裁赵五十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "紫光集团"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "存储事业部"},
      {"type": "POSITION", "start": 8, "end": 13, "text": "技术副总裁"}
    ]
  },
  {
    "text": "京东方显示技术研究院显示科学家李五十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "京东方"},
      {"type": "DEPARTMENT", "start": 3, "end": 9, "text": "显示技术研究院"},
      {"type": "POSITION", "start": 9, "end": 14, "text": "显示科学家"}
    ]
  },
  {
    "text": "TCL 华星光电技术研发部光学工程师王五十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 6, "text": "TCL 华星光电"},
      {"type": "DEPARTMENT", "start": 6, "end": 10, "text": "技术研发部"},
      {"type": "POSITION", "start": 10, "end": 15, "text": "光学工程师"}
    ]
  },
  {
    "text": "大疆创新飞行器控制算法总监赵五十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "大疆创新"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "飞行器控制算法总监"}
    ]
  },
  {
    "text": "科大讯飞语音技术研究院语音识别科学家李五十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "科大讯飞"},
      {"type": "DEPARTMENT", "start": 4, "end": 9, "text": "语音技术研究院"},
      {"type": "POSITION", "start": 9, "end": 15, "text": "语音识别科学家"}
    ]
  },
  {
    "text": "商汤科技智能视觉研究院计算机视觉总监王五十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "商汤科技"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "智能视觉研究院"},
      {"type": "POSITION", "start": 10, "end": 16, "text": "计算机视觉总监"}
    ]
  },
  {
    "text": "旷视科技 Face++实验室算法科学家赵五十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "旷视科技"},
      {"type": "DEPARTMENT", "start": 4, "end": 10, "text": "Face++实验室"},
      {"type": "POSITION", "start": 10, "end": 15, "text": "算法科学家"}
    ]
  },
  {
    "text": "依图医疗医学影像分析总监李五十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "依图医疗"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "医学影像分析总监"}
    ]
  },
  {
    "text": "云从科技人机协同操作系统首席架构师王六十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "云从科技"},
      {"type": "POSITION", "start": 4, "end": 14, "text": "人机协同操作系统首席架构师"}
    ]
  },
  {
    "text": "寒武纪智能芯片研发部硬件总监赵六十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "寒武纪"},
      {"type": "DEPARTMENT", "start": 3, "end": 7, "text": "智能芯片研发部"},
      {"type": "POSITION", "start": 7, "end": 11, "text": "硬件总监"}
    ]
  },
  {
    "text": "地平线机器人征程芯片架构师李六十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 5, "text": "地平线机器人"},
      {"type": "POSITION", "start": 5, "end": 11, "text": "征程芯片架构师"}
    ]
  },
  {
    "text": "深鉴科技 FPGA 计算平台技术总监王六十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "深鉴科技"},
      {"type": "POSITION", "start": 4, "end": 12, "text": "FPGA 计算平台技术总监"}
    ]
  },
  {
    "text": "云天励飞大数据事业部解决方案总监赵六十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "云天励飞"},
      {"type": "DEPARTMENT", "start": 4, "end": 7, "text": "大数据事业部"},
      {"type": "POSITION", "start": 7, "end": 13, "text": "解决方案总监"}
    ]
  },
  {
    "text": "格林深瞳智能视频分析算法工程师李六十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "格林深瞳"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "智能视频分析算法工程师"}
    ]
  },
  {
    "text": "极智嘉科技仓储物流机器人产品总监王六十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 5, "text": "极智嘉科技"},
      {"type": "POSITION", "start": 5, "end": 13, "text": "仓储物流机器人产品总监"}
    ]
  },
  {
    "text": "优必选科技人形机器人运动控制总监赵六十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "优必选科技"},
      {"type": "POSITION", "start": 4, "end": 12, "text": "人形机器人运动控制总监"}
    ]
  },
  {
    "text": "云鲸智能清洁机器人研发部经理李六十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "云鲸智能"},
      {"type": "POSITION", "start": 4, "end": 11, "text": "清洁机器人研发部经理"}
    ]
  },
  {
    "text": "石头科技扫地机器人算法总监王六十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "石头科技"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "扫地机器人算法总监"}
    ]
  },
  {
    "text": "九号机器人平衡车产品线总监赵七十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 5, "text": "九号机器人"},
      {"type": "POSITION", "start": 5, "end": 11, "text": "平衡车产品线总监"}
    ]
  },
  {
    "text": "追觅科技智能家电研发工程师李七十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "追觅科技"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "智能家电研发工程师"}
    ]
  },
  {
    "text": "添可智能科技洗地机产品经理王七十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "添可智能科技"},
      {"type": "POSITION", "start": 4, "end": 8, "text": "洗地机产品经理"}
    ]
  },
  {
    "text": "乐聚机器人仿人智能控制首席科学家赵七十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 5, "text": "乐聚机器人"},
      {"type": "POSITION", "start": 5, "end": 13, "text": "仿人智能控制首席科学家"}
    ]
  },
  {
    "text": "宇树科技四足机器人运动规划总监李七十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "宇树科技"},
      {"type": "POSITION", "start": 4, "end": 12, "text": "四足机器人运动规划总监"}
    ]
  },
  {
    "text": "微纳星空卫星姿控推进系统工程师王七十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "微纳星空"},
      {"type": "POSITION", "start": 4, "end": 11, "text": "卫星姿控推进系统工程师"}
    ]
  },
  {
    "text": "星际荣耀运载火箭总体设计师赵七十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "星际荣耀"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "运载火箭总体设计师"}
    ]
  },
  {
    "text": "蓝箭航天液氧甲烷发动机研发总监李七十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "蓝箭航天"},
      {"type": "POSITION", "start": 4, "end": 11, "text": "液氧甲烷发动机研发总监"}
    ]
  },
  {
    "text": "星河动力固体火箭结构工程师王七十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "星河动力"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "固体火箭结构工程师"}
    ]
  },
  {
    "text": "零壹空间航天电子系统副总师赵七十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "零壹空间"},
      {"type": "POSITION", "start": 4, "end": 11, "text": "航天电子系统副总师"}
    ]
  },
  {
    "text": "天仪研究院遥感卫星应用科学家李八十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "天仪研究院"},
      {"type": "POSITION", "start": 4, "end": 9, "text": "遥感卫星应用科学家"}
    ]
  },
  {
    "text": "长光卫星吉林一号数据处理总监王八十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "长光卫星"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "吉林一号数据处理总监"}
    ]
  },
  {
    "text": "航天宏图谱睿 GIS 平台研发经理赵八十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "航天宏图"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "谱睿 GIS 平台研发经理"}
    ]
  },
  {
    "text": "中科星图数字地球产品总监李八十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "中科星图"},
      {"type": "POSITION", "start": 4, "end": 8, "text": "数字地球产品总监"}
    ]
  },
  {
    "text": "欧比特人工智能卫星星座运控总监王八十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 3, "text": "欧比特"},
      {"type": "POSITION", "start": 3, "end": 11, "text": "人工智能卫星星座运控总监"}
    ]
  },
  {
    "text": "国盾量子量子密钥分发系统科学家赵八十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "国盾量子"},
      {"type": "POSITION", "start": 4, "end": 11, "text": "量子密钥分发系统科学家"}
    ]
  },
  {
    "text": "本源量子量子计算机架构师李八十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "本源量子"},
      {"type": "POSITION", "start": 4, "end": 9, "text": "量子计算机架构师"}
    ]
  },
  {
    "text": "量旋科技量子计算云平台技术总监王八十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "量旋科技"},
      {"type": "POSITION", "start": 4, "end": 11, "text": "量子计算云平台技术总监"}
    ]
  },
  {
    "text": "启科量子量子通信设备研发工程师赵八十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "启科量子"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "量子通信设备研发工程师"}
    ]
  },
  {
    "text": "问天量子量子精密测量首席科学家李八十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "问天量子"},
      {"type": "POSITION", "start": 4, "end": 11, "text": "量子精密测量首席科学家"}
    ]
  },
  {
    "text": "百度风投硬科技投资部投资总监王九十",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "百度风投"},
      {"type": "DEPARTMENT", "start": 4, "end": 7, "text": "硬科技投资部"},
      {"type": "POSITION", "start": 7, "end": 11, "text": "投资总监"}
    ]
  },
  {
    "text": "红杉资本中国基金合伙人赵九十一",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 7, "text": "红杉资本中国基金"},
      {"type": "POSITION", "start": 7, "end": 9, "text": "合伙人"}
    ]
  },
  {
    "text": "高瓴资本医疗健康投资团队执行董事李九十二",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "高瓴资本"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "医疗健康投资团队"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "执行董事"}
    ]
  },
  {
    "text": "IDG 资本先进制造投资部副总裁王九十三",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 6, "text": "IDG 资本"},
      {"type": "DEPARTMENT", "start": 6, "end": 10, "text": "先进制造投资部"},
      {"type": "POSITION", "start": 10, "end": 13, "text": "副总裁"}
    ]
  },
  {
    "text": "启明创投 TMT 投资团队主管赵九十四",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "启明创投"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "TMT 投资团队"},
      {"type": "POSITION", "start": 8, "end": 10, "text": "主管"}
    ]
  },
  {
    "text": "经纬中国早期投资部投资经理李九十五",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "经纬中国"},
      {"type": "DEPARTMENT", "start": 4, "end": 8, "text": "早期投资部"},
      {"type": "POSITION", "start": 8, "end": 12, "text": "投资经理"}
    ]
  },
  {
    "text": "源码资本数字经济投资总监王九十六",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "源码资本"},
      {"type": "POSITION", "start": 4, "end": 8, "text": "数字经济投资总监"}
    ]
  },
  {
    "text": "五源资本硬科技投资执行董事赵九十七",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "五源资本"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "硬科技投资执行董事"}
    ]
  },
  {
    "text": "线性资本人工智能首席投资官李九十八",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "线性资本"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "人工智能首席投资官"}
    ]
  },
  {
    "text": "峰瑞资本生物医药投资分析师王九十九",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "峰瑞资本"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "生物医药投资分析师"}
    ]
  },
  {
    "text": "顺为资本绿色能源投资副总裁赵一百",
    "entities": [
      {"type": "ORGANIZATION", "start": 0, "end": 4, "text": "顺为资本"},
      {"type": "POSITION", "start": 4, "end": 10, "text": "绿色能源投资副总裁"}
    ]
  }
]
```

---

## 指针网络标签构建方法

### 方法 1: 直接位置索引法

对于每个实体类型，构建两个标签:
- `start_labels`: 实体起始位置的 one-hot 编码
- `end_labels`: 实体结束位置的 one-hot 编码

```python
# 示例代码
def build_pointer_labels(text, entities, max_length):
    """
    构建指针网络的训练标签
    
    Args:
        text: 输入文本
        entities: 实体列表
        max_length: 最大序列长度
    
    Returns:
        start_labels: dict, 每个实体类型的起始位置标签
        end_labels: dict, 每个实体类型的结束位置标签
    """
    start_labels = {
        'ORGANIZATION': [0] * max_length,
        'DEPARTMENT': [0] * max_length,
        'POSITION': [0] * max_length
    }
    end_labels = {
        'ORGANIZATION': [0] * max_length,
        'DEPARTMENT': [0] * max_length,
        'POSITION': [0] * max_length
    }
    
    for entity in entities:
        entity_type = entity['type']
        start_pos = entity['start']
        end_pos = entity['end'] - 1  # 转换为包含结束位置
        
        if start_pos < max_length:
            start_labels[entity_type][start_pos] = 1
        if end_pos < max_length:
            end_labels[entity_type][end_pos] = 1
    
    return start_labels, end_labels
```

### 方法 2: 考虑特殊标记

MacBERT 需要添加 [CLS] 和 [SEP] 标记:

```python
def tokenize_with_special_tokens(text, tokenizer):
    """
    使用 MacBERT tokenizer 进行分词并添加特殊标记
    """
    tokens = tokenizer.tokenize(text)
    # 添加 [CLS] 和 [SEP]
    tokens = ['[CLS]'] + tokens + ['[SEP]']
    
    # 调整实体位置 (都 +1，因为前面加了 [CLS])
    return tokens
```

### 损失函数设计

```python
import torch
import torch.nn as nn

class PointerNetworkLoss(nn.Module):
    def __init__(self):
        super().__init__()
        self.criterion = nn.CrossEntropyLoss()
    
    def forward(self, start_logits, end_logits, start_labels, end_labels):
        """
        Args:
            start_logits: (batch_size, seq_len) - 预测的起始位置 logits
            end_logits: (batch_size, seq_len) - 预测的结束位置 logits
            start_labels: (batch_size,) - 真实的起始位置索引
            end_labels: (batch_size,) - 真实的结束位置索引
        
        Returns:
            loss: 总损失
        """
        start_loss = self.criterion(start_logits, start_labels)
        end_loss = self.criterion(end_logits, end_labels)
        
        return start_loss + end_loss
```

---

## 数据增强策略

### 1. 同义词替换

```python
# 公司同义词
ORG_SYNONYMS = {
    '公司': ['企业', '集团', '有限公司', '股份有限公司'],
    '部门': ['事业部', '中心', '研究院', '团队'],
    '岗位': ['职位', '职务', '头衔']
}
```

### 2. 句式变换

- 主动变被动
- 调整语序
- 添加修饰语

### 3. 实体组合

随机组合不同的公司、部门、岗位生成新的训练样本。

---

## 训练建议

1. **学习率**: 2e-5 到 5e-5
2. **Batch Size**: 16-32
3. **Epoch**: 10-20
4. **最大序列长度**: 128 或 256
5. **优化器**: AdamW
6. **评估指标**: Precision, Recall, F1-Score

---

## 推理过程

```python
def predict_entities(model, tokenizer, text, threshold=0.5):
    """
    使用训练好的指针网络模型预测实体
    """
    # 1. 分词
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=128)
    
    # 2. 模型推理
    with torch.no_grad():
        start_logits, end_logits = model(**inputs)
        start_probs = torch.softmax(start_logits, dim=-1)
        end_probs = torch.softmax(end_logits, dim=-1)
    
    # 3. 提取实体
    entities = []
    for entity_type in ['ORGANIZATION', 'DEPARTMENT', 'POSITION']:
        # 找到概率最高的 start 和 end 位置
        start_idx = torch.argmax(start_probs[0, :, entity_type_map[entity_type]])
        end_idx = torch.argmax(end_probs[0, :, entity_type_map[entity_type]])
        
        if start_probs[0, start_idx, entity_type_map[entity_type]] > threshold:
            # 解码实体文本
            entity_text = tokenizer.decode(inputs['input_ids'][0][start_idx:end_idx+1])
            entities.append({
                'type': entity_type,
                'start': start_idx.item(),
                'end': end_idx.item() + 1,
                'text': entity_text
            })
    
    return entities
```

---

## 文件清单

1. `ner_train.json` - 完整的训练数据集
2. `ner_dev.json` - 验证数据集 (可以从 train 中划分 10%)
3. `ner_test.json` - 测试数据集 (可以从 train 中划分 10%)
4. `data_processor.py` - 数据处理脚本
5. `model.py` - MacBERT + 指针网络模型定义
6. `train.py` - 训练脚本
7. `predict.py` - 预测脚本

---

## 参考资料

1. MacBERT 论文: "Revisiting Pre-Trained Models for Chinese Natural Language Processing"
2. Pointer Network 论文: "Neural Machine Translation by Jointly Learning to Align and Translate"
3. Span-based NER: "A Span-Based Model for Joint Overlapping Named Entity Recognition"
