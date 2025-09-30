# 题库设计方案 (Question Bank Design)

## 总体规划

### 题目总量
- **Hotel Operations**: 10部门 × 100题 = **1,000题**
- **Marine Operations**: 3部门 × 200题 = **600题**
- **Casino Operations**: 3部门 × 200题 = **600题**
- **总计**: **2,200题**

### 模块分配策略

每个部门的题目按以下比例分配到6个模块：

| 模块 | 比例 | Hotel (100题) | Marine/Casino (200题) |
|------|------|--------------|----------------------|
| Listening (听力) | 20% | 20题 | 40题 |
| Time & Numbers (时间数字) | 15% | 15题 | 30题 |
| Grammar (语法) | 20% | 20题 | 40题 |
| Vocabulary (词汇) | 20% | 20题 | 40题 |
| Reading (阅读) | 15% | 15题 | 30题 |
| Speaking (口语) | 10% | 10题 | 20题 |
| **总计** | **100%** | **100题** | **200题** |

## Hotel Operations 部门题目分配

### 1. Front Desk (前台接待) - 100题
- Listening: 20题（每个场景2题）
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 2. Housekeeping (客房服务) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 3. Food & Beverage (餐饮服务) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 4. Bar Service (酒吧服务) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 5. Guest Services (宾客服务) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 6. Cabin Service (客舱服务) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 7. Auxiliary Service (辅助服务) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 8. Laundry (洗衣房) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 9. Photo (摄影服务) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

### 10. Provisions (物资供应) - 100题
- Listening: 20题
- Time & Numbers: 15题
- Grammar: 20题
- Vocabulary: 20题
- Reading: 15题
- Speaking: 10题

## Marine Operations 部门题目分配

### 11. Deck Department (甲板部) - 200题
- Listening: 40题（每个场景4题）
- Time & Numbers: 30题
- Grammar: 40题
- Vocabulary: 40题
- Reading: 30题
- Speaking: 20题

### 12. Engine Department (机舱部) - 200题
- Listening: 40题
- Time & Numbers: 30题
- Grammar: 40题
- Vocabulary: 40题
- Reading: 30题
- Speaking: 20题

### 13. Security Department (安全部) - 200题
- Listening: 40题
- Time & Numbers: 30题
- Grammar: 40题
- Vocabulary: 40题
- Reading: 30题
- Speaking: 20题

## Casino Operations 部门题目分配

### 14. Table Games (赌桌游戏) - 200题
- Listening: 40题（每个场景4题）
- Time & Numbers: 30题
- Grammar: 40题
- Vocabulary: 40题
- Reading: 30题
- Speaking: 20题

### 15. Slot Machines (老虎机) - 200题
- Listening: 40题
- Time & Numbers: 30题
- Grammar: 40题
- Vocabulary: 40题
- Reading: 30题
- Speaking: 20题

### 16. Casino Services (娱乐场服务) - 200题
- Listening: 40题
- Time & Numbers: 30题
- Grammar: 40题
- Vocabulary: 40题
- Reading: 30题
- Speaking: 20题

## 题目结构 (JSON Schema)

```json
{
  "question_id": "HOTEL_FD_L_001",
  "department": "Front Desk",
  "operation": "Hotel Operations",
  "scenario_id": 1,
  "scenario_title": "Guest Embarkation Check-in",
  "module": "Listening",
  "difficulty": "medium",
  "points": 4,
  "question_type": "multiple_choice",
  "question_text": "What document does the guest need to show?",
  "audio_file": "hotel_fd_scenario1_q1.mp3",
  "options": {
    "A": "Passport",
    "B": "Driver's license",
    "C": "Credit card",
    "D": "Boarding pass"
  },
  "correct_answer": "A",
  "explanation": "Guests must show their passport for identification during embarkation.",
  "skills_tested": ["listening_comprehension", "vocabulary"],
  "created_date": "2025-09-30"
}
```

## 实施阶段建议

### 阶段1：框架搭建（已完成）
- 设计题库结构
- 确定分配比例
- 创建JSON schema

### 阶段2：样本生成（建议先做）
- 为每个部门生成10-20道示例题
- 验证题目质量和分布
- 调整策略

### 阶段3：批量生成
- 使用AI辅助批量生成题目
- 人工审核和优化
- 建立题目审核流程

### 阶段4：题库管理系统
- 开发题库管理界面
- 实现题目标签和搜索
- 支持难度调整和更新

## 题目质量标准

### Listening (听力)
- 对话长度：30-60秒
- 语速：130-150 words/minute
- 口音：标准美式或英式英语
- 背景噪音：适度模拟真实环境

### Time & Numbers
- 涉及时间表达、数字、日期
- 填空题或选择题
- 测试实际工作中的数字理解

### Grammar
- 覆盖时态、语态、从句
- 填空或选择题
- 基于实际工作场景

### Vocabulary
- 行业专业术语
- 匹配题或选择题
- 分类练习

### Reading
- 文章长度：150-300词
- 包括通知、菜单、说明书
- 理解和推断能力

### Speaking
- 回答长度：30-60秒
- AI评分标准：发音、流利度、语法、内容
- 基于真实工作场景

## 下一步行动

1. **确认方案**：确认以上分配策略是否合理
2. **选择实施方式**：
   - 选项A：生成所有2200题（时间较长）
   - 选项B：先生成每个部门10-20道示例题（快速验证）
   - 选项C：生成特定部门的完整题库
3. **开始生成**：根据确认的方案开始生成题目
