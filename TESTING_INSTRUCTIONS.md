# 测试说明 - Speaking 智能评分 & TTS 改进

## 功能概述

### 1. Speaking 智能评分系统 ✅
- 实时语音转文字（Web Speech API）
- 关键词智能匹配
- 根据匹配率给分

### 2. 语音自然化 ✅
- 优先使用预生成的 MP3 文件
- 自动降级到浏览器 TTS

---

## 如何测试

### 测试 1: Speaking 智能评分

#### 步骤
1. 访问 `http://127.0.0.1:8000/question/19`
2. 点击 **"Start Recording"** 按钮
3. 对着麦克风说出回答（例如下面的示例）
4. 观察状态显示的实时转录
5. 点击 **"Stop Recording"** 按钮
6. 查看转录文本是否正确
7. 提交答案
8. 跳到 Q21 查看最终得分

#### Q19 测试场景

**题目**: A guest says: 'The air conditioning in my room is too cold.' Please respond appropriately.

**期望关键词**: apologize, sorry, send someone, fix, adjust, maintenance, comfortable

**测试回答**:

| 回答内容 | 期望结果 |
|----------|----------|
| "I apologize, I'm sorry. I will send someone from maintenance to fix and adjust the AC to make you comfortable." | 7/7 分（匹配全部7个关键词） |
| "I'm sorry about that. I will send maintenance to fix it." | 4/7 分（匹配3个关键词：sorry, fix, maintenance） |
| "I apologize. Let me adjust the temperature." | 3/7 分（匹配2个关键词：apologize, adjust） |
| "Okay, I will help you." | 1/7 分（无关键词，仅尝试分） |
| 什么都不说（静音） | 1/7 分（有录音但无语音） |

---

### 测试 2: 音频播放功能

#### 步骤
1. 访问 `http://127.0.0.1:8000/question/1`
2. 打开浏览器开发者工具（F12）→ Console 标签
3. 点击 **"Play Audio"** 按钮
4. 查看 Console 输出

#### 预期结果

**如果没有预生成的 MP3 文件**:
```
Console: Pre-generated audio not found, using TTS fallback
→ 使用浏览器 TTS 播放（机器声音）
```

**如果有预生成的 MP3 文件**:
```
→ 直接播放 MP3（自然人声）
```

---

## 验证清单

### Speaking 智能评分
- [ ] 录音时显示 "Recording... (listening for speech)"
- [ ] 停止录音后显示转录文本
- [ ] 转录文本包含在提交的数据中
- [ ] 后端根据关键词匹配计算分数
- [ ] 得分与匹配率相符

### 音频播放
- [ ] 尝试加载 `/static/audio/q1_listening.mp3`
- [ ] 文件不存在时自动降级到 TTS
- [ ] 播放次数限制正常（2次）
- [ ] 音频播放完成后更新剩余次数

### Session 数据
- [ ] 所有 21 道题的答案都保存在 Session
- [ ] Session 大小 <4KB（约 500 字节）
- [ ] 最终得分计算正确

---

## 调试端点

### 测试 Speaking 评分算法
```
GET http://127.0.0.1:8000/debug/test-speaking-scoring
```
返回不同关键词匹配率的评分结果

### 测试整体评分
```
GET http://127.0.0.1:8000/debug/test-scoring
```
测试所有 21 题的评分逻辑

### 查看 Session 数据
```
GET http://127.0.0.1:8000/debug/session
```
查看当前保存的答案数据

---

## 预期测试结果

### 正确答案应得 100/100 分

- Listening: 16/16
- Time & Numbers: 16/16
- Grammar: 16/16
- Vocabulary: 16/16
- Reading: 16/16
- Speaking: 20/20（包含关键词的完整回答）

### Speaking 部分评分示例

**Q19** (7分):
- 优秀回答（包含 apologize, sorry, send someone, fix, adjust, maintenance, comfortable）→ 7/7
- 良好回答（包含 sorry, fix, maintenance）→ 4/7
- 一般回答（包含 apologize, adjust）→ 3/7

**Q20** (7分):
- 优秀回答（包含 buffet, closes, hours, dining, alternative, room service, restaurant）→ 7/7

**Q21** (6分):
- 优秀回答（包含 elevator, deck, directions, follow, signs, spa, level, floor）→ 6/6

---

## 已知问题

### Edge TTS API 限制
- Edge TTS API 当前遇到 403 错误（网络限制）
- **解决方案**: 使用浏览器 TTS 降级（已实现）
- **替代方案**: 手动录制真人语音或使用其他 TTS 服务

### 浏览器兼容性
- Web Speech API 在 Chrome/Edge 上支持最好
- Firefox 和 Safari 可能需要不同的实现
- 建议使用 Chrome 或 Edge 浏览器测试

---

**准备就绪！请按照上述步骤测试 Speaking 智能评分功能。** 🎯

