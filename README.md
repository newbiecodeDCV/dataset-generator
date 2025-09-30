# 🗣️ Bộ Tạo Dataset Code-Switching Việt-Anh cho Meeting

Tool tạo dataset code-switching (chuyển mã ngôn ngữ) Việt-Anh trong bối cảnh meeting/họp công việc, sử dụng OpenAI API. Dataset được tạo theo format chuẩn ADACS để training/fine-tuning model ASR.

## 📌 Tổng Quan

### Mục đích
- Tạo dataset bổ sung cho [ADACS project](https://github.com/adacs-project/adacs-project.github.io)
- Focus vào bối cảnh meeting/họp trong công ty Việt Nam
- Hỗ trợ fine-tuning model nhận diện code-switching

### Format Dataset (ADACS)
```json
{
  "origin": "Team Leader yêu cầu update status của Sprint Planning Meeting",
  "spoken": "tím lí đơ yêu cầu áp đét xờ tét tút của xờ pin pờ lán ninh mí tinh",
  "en_word": ["Team", "Leader", "update", "status", "Sprint", "Planning", "Meeting"],
  "vi_spoken_word": ["tím", "lí đơ", "áp đét", "xờ tét tút", "xờ pin", "pờ lán ninh", "mí tinh"],
  "type": "hard",
  "en_phrase": ["Team Leader", "Sprint Planning Meeting", "update", "status"]
}
```

## 🚀 Hướng Dẫn Cài Đặt

### 1. Clone repository
```bash
cd /home/hiennt/dataset-generator
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

Output mẫu:
```
Successfully installed openai-1.0.0 python-dotenv-1.0.0 pyyaml-6.0 pandas-2.0.0 tqdm-4.65.0
```

### 3. Cấu hình OpenAI API Key
```bash
# Tạo file .env từ template
cp .env.example .env

# Edit file .env và thêm API key của bạn
nano .env
```

Nội dung file `.env`:
```env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

## 📝 Cấu Trúc Project

```
dataset-generator/
├── config.yaml                 # Cấu hình chính
├── generate_dataset.py         # Script chính
├── src/
│   ├── pronunciation_engine.py # Xử lý phiên âm
│   ├── prompt_builder.py       # Tạo prompts
│   ├── data_processor.py       # Xử lý data
│   └── validator.py            # Kiểm tra format
├── prompts/
│   ├── system_prompt.txt       # System prompt
│   └── few_shot_examples.json  # Ví dụ few-shot
├── data/
│   └── pronunciation_rules.json # Quy tắc phiên âm
└── output/                      # Thư mục output
```

## 🎯 Sử Dụng

### Test với 5 mẫu
```bash
python generate_dataset.py --test
```

Output:
```
🧪 TEST MODE: Generating 5 samples

============================================================
Starting dataset generation: 5 samples
Model: gpt-3.5-turbo
============================================================

Generating samples: 100%|████████████| 5/5 [00:12<00:00,  2.45s/it]

✓ Dataset saved to: ./output/meeting_dataset.json
  Total samples: 5

============================================================
GENERATION STATISTICS
============================================================
Total attempts:    5
Successful:        5 (100.0%)
Failed:            0
API errors:        0
============================================================

Validating dataset...
============================================================
VALIDATION REPORT
============================================================

Total Samples: 5
Valid Samples: 5 (100.0%)
Invalid Samples: 0

--- Type Distribution ---
  easy: 3
  hard: 1
  mixed: 1

Average English words per sample: 4.2
Average text length: 65 characters

============================================================

📝 Sample output:
{
  "origin": "Chúng ta cần optimize performance của system này trước deadline",
  "spoken": "chúng ta cần óp ti mai pơ phóc men của xít tem này trước đét lai",
  "en_word": ["optimize", "performance", "system", "deadline"],
  "vi_spoken_word": ["óp ti mai", "pơ phóc men", "xít tem", "đét lai"],
  "type": "easy",
  "en_phrase": ["optimize", "performance", "system", "deadline", "optimize performance"]
}

✅ Dataset generation completed successfully!
```

### Tạo dataset đầy đủ
```bash
# Tạo 1000 mẫu (default)
python generate_dataset.py

# Hoặc chỉ định số lượng
python generate_dataset.py --size 100

# Chỉ định output file
python generate_dataset.py --size 50 --output ./output/my_dataset.json
```

## ⚙️ Cấu Hình

### File `config.yaml`
```yaml
# Dataset Configuration
dataset:
  name: "meeting_codeswitch_adacs"
  output_file: "./output/meeting_dataset.json"
  size: 1000  # Số lượng mẫu
  
# OpenAI Configuration
openai:
  model: "gpt-3.5-turbo"  # Dùng model rẻ để tiết kiệm chi phí
  temperature: 0.7
  max_tokens: 300
  batch_delay: 0.5        # Delay giữa các request
  max_retries: 3

# Meeting Contexts (Tỷ lệ %)
meeting_contexts:
  daily_standup: 0.20       # 20%
  sprint_planning: 0.15     # 15%
  client_presentation: 0.15 # 15%
  technical_discussion: 0.20 # 20%
  performance_review: 0.10  # 10%
  training_session: 0.10    # 10%
  team_meeting: 0.10        # 10%

# Difficulty Distribution
difficulty_levels:
  easy: 0.50   # 50% - Từ đơn giản
  hard: 0.35   # 35% - Cụm từ kỹ thuật
  mixed: 0.15  # 15% - Mix nhiều
```

## 💰 Chi Phí Ước Tính

| Số lượng | Model | Chi phí |
|----------|-------|---------|
| 100 mẫu | gpt-3.5-turbo | ~$0.06 |
| 1000 mẫu | gpt-3.5-turbo | ~$0.60 |
| 5000 mẫu | gpt-3.5-turbo | ~$3.00 |

## 📊 Ví Dụ Dataset Tạo Ra

### Easy (Từ đơn)
```json
{
  "origin": "Team cần review code trước khi merge",
  "spoken": "tím cần ri viu cốt trước khi mợt",
  "en_word": ["Team", "review", "code", "merge"],
  "vi_spoken_word": ["tím", "ri viu", "cốt", "mợt"],
  "type": "easy",
  "en_phrase": ["Team", "review", "code", "merge"]
}
```

### Hard (Cụm từ)
```json
{
  "origin": "Sprint Planning Meeting sẽ discuss về User Story và Technical Debt",
  "spoken": "xờ pin pờ lán ninh mí tinh sẽ đít cát về diu dơ xờ tô ri và tếch ni cồ đét",
  "en_word": ["Sprint", "Planning", "Meeting", "discuss", "User", "Story", "Technical", "Debt"],
  "vi_spoken_word": ["xờ pin", "pờ lán ninh", "mí tinh", "đít cát", "diu dơ", "xờ tô ri", "tếch ni cồ", "đét"],
  "type": "hard",
  "en_phrase": ["Sprint Planning Meeting", "User Story", "Technical Debt", "discuss"]
}
```

### Mixed (Trộn nhiều)
```json
{
  "origin": "CEO announce strategy mới cho Q4, focus vào digital transformation và customer experience",
  "spoken": "xi i ô ơ náo xờ tờ rát tê gi mới cho quý 4, phô cớt vào đi gi tồ tờ ren phố mây sờn và cắt tô mơ ét pí ri ơn",
  "en_word": ["CEO", "announce", "strategy", "focus", "digital", "transformation", "customer", "experience"],
  "vi_spoken_word": ["xi i ô", "ơ náo", "xờ tờ rát tê gi", "phô cớt", "đi gi tồ", "tờ ren phố mây sờn", "cắt tô mơ", "ét pí ri ơn"],
  "type": "mixed",
  "en_phrase": ["CEO", "announce", "strategy", "focus", "digital transformation", "customer experience"]
}
```

## 🔍 Kiểm Tra & Validate

### Validate dataset đã tạo
```bash
python -c "
from src.validator import ADACSValidator
import json

# Load dataset
with open('./output/meeting_dataset.json', 'r', encoding='utf-8') as f:
    dataset = json.load(f)

# Validate
validator = ADACSValidator()
stats = validator.validate_dataset(dataset)
validator.print_validation_report(stats)
"
```

## 🛠️ Troubleshooting

### Lỗi API Key
```
❌ Error: OPENAI_API_KEY environment variable not set!
```
**Giải pháp**: Kiểm tra file `.env` có API key hợp lệ

### Lỗi Rate Limit
```
API Error: Rate limit exceeded
```
**Giải pháp**: Tăng `batch_delay` trong `config.yaml`

### Lỗi Validation
```
Validation failed: ['en_word' has 5 items, vi_spoken_word has 4 items']
```
**Giải pháp**: Kiểm tra pronunciation rules, có thể thiếu mapping

## 📚 Tài Liệu Tham Khảo

- [ADACS Project](https://github.com/adacs-project/adacs-project.github.io)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Code-Switching ASR Research](https://adacs-project.github.io)

## 📈 Thống Kê Pronunciation Rules

Hiện tại đã có sẵn phiên âm cho:
- **100+ từ thông dụng** trong meeting (meeting, deadline, performance...)
- **15+ từ viết tắt** (API, CEO, UI/UX...)
- **5+ cụm từ ghép** (work-life, real-time...)

## 🎯 Roadmap

- [ ] Thêm nhiều meeting contexts
- [ ] Cải thiện pronunciation rules
- [ ] Thêm validation chặt chẽ hơn
- [ ] Export sang các format khác (CSV, JSONL)
- [ ] Batch API để giảm chi phí

## 👥 Đóng Góp

Mọi đóng góp đều được hoan nghênh! Vui lòng:
1. Fork repo
2. Tạo branch mới
3. Commit changes
4. Tạo Pull Request

## 📄 License

MIT License

## 🙏 Lời Cảm Ơn

- ADACS Project team
- OpenAI
- Cộng đồng NLP Việt Nam

---
*Được phát triển cho mục đích nghiên cứu code-switching ASR tiếng Việt*