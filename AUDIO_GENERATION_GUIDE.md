# Audio Generation Guide - 音频生成指南

## Edge TTS 音频生成

由于 Edge TTS API 可能遇到网络限制（403 错误），你可以使用以下方法生成自然语音音频：

### 方法 1: 使用 Edge TTS 命令行工具（推荐）

1. **安装 Edge TTS**（如果还没安装）:
```bash
pip install edge-tts
```

2. **使用命令行生成音频**:
```bash
# 生成单个音频文件
edge-tts --voice en-US-JennyNeural --text "Hello, I would like to book a table for four people at seven PM tonight, please." --write-media q1_listening.mp3

# 或者使用 Python 脚本（需要网络连接）
python scripts/generate_audio_files.py
```

### 方法 2: 使用在线 TTS 服务

1. **ElevenLabs** (https://elevenlabs.io/) - 非常自然，需要注册
2. **Google Cloud Text-to-Speech** - 需要 Google Cloud 账号
3. **Azure Cognitive Services** - 需要 Azure 账号

### 方法 3: 使用浏览器录制

1. 使用 Edge 浏览器访问在线 TTS 服务
2. 播放文本并录制音频
3. 保存为 MP3 文件

### 音频文件命名规则

音频文件应保存在: `src/main/python/static/audio/`

命名格式: `q{question_number}_{module}.mp3`

例如:
- `q1_listening.mp3`
- `q2_listening.mp3`
- `q3_listening.mp3`
- `q4_time_numbers.mp3`
- `q5_time_numbers.mp3`
- `q6_time_numbers.mp3`

### 当前状态

- ✅ 前端代码已支持预生成音频文件
- ✅ 如果没有音频文件，会自动降级到浏览器 TTS
- ⚠️ Edge TTS API 遇到网络限制，需要手动生成或使用其他方法

### 测试

即使没有预生成的音频文件，系统也会正常工作（使用浏览器 TTS 作为降级方案）。

要测试预生成的音频：
1. 手动生成音频文件并放在 `src/main/python/static/audio/` 目录
2. 刷新页面，系统会自动使用预生成的音频文件

