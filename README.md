# Elden Ring Lore DB

엘든링 인게임 원문 텍스트(NPC 대사, 아이템 설명, 컷씬 자막)를 DB화하여
오피셜 원문 기반으로 질문에 답하는 챗봇 서비스.

## 개요

FromSoftware의 공식 인게임 텍스트만을 소스로 사용하며, 팬 위키나 2차 해석이 아닌
순수 원문 기반으로 로어 질문에 답변합니다.

답변은 두 섹션으로 분리됩니다:
- **[오피셜]**: 인게임 원문 그대로
- **[추론]**: 원문 기반으로 Ollama LLM이 생성한 해석

## 기술 스택

| 역할 | 기술 |
|------|------|
| 데이터 저장 | Python + SQLite |
| 원문 검색 | SQLite FTS5 (Full-Text Search) |
| 추론 생성 | Ollama (llama3.1 로컬 LLM) |
| 웹 UI | Streamlit |
| 데이터 파이프라인 | Python (fetch + parse 스크립트) |

## 동작 흐름

```
유저 입력 (예: "멜리나")
      ↓
SQLite에서 관련 원문 전체 조회
      ↓
조회된 원문 → Ollama llama3.1 로 전달
      ↓
Streamlit 화면 출력:
  [오피셜] 인게임 원문 목록
  [추론]   LLM이 생성한 해석
```

## 프로젝트 구조

```
elden-ring-lore-db/
├── app/                  # Streamlit 앱 (추후 세팅)
├── data/
│   ├── raw/              # 원본 추출 데이터 (git 미포함)
│   └── processed/        # 파싱된 JSON (lore_entries.json)
├── scripts/
│   ├── fetch_erdb.py     # erdb / fromsoft-fts에서 데이터 다운로드
│   └── parse_fmg.py      # raw 데이터 → lore_entries.json 변환
└── README.md
```

> `app/` 폴더 내 Streamlit 앱 및 SQLite 연동 코드는 Phase 2에서 작성 예정

## 데이터 스키마

```json
{
  "id": "weapons_12345",
  "category": "item | dialogue | cutscene | misc",
  "source_name": "Grafted Blade Greatsword",
  "text_en": "A greatsword with many smaller blades grafted...",
  "text_ko": "수많은 작은 검날이 접합된 대검...",
  "location": "Castle Morne"
}
```

## 데이터 출처

아래 공개 데이터셋 및 도구를 기반으로 합니다.

### 1. erdb (EldenRingDatabase) — 메인 데이터셋
- **URL**: https://github.com/EldenRingDatabase/erdb
- **내용**: 무기 / 방어구 / 탈리스만 / 아이템 / 마법 / NPC / 지도 위치 등 종합 JSON
- **포맷**: JSON
- **언어**: 영어
- **라이선스**: MIT
- **Stars**: 66 / 활발히 유지보수 중

### 2. fromsoft-fts (FromSoftware Full-Text Search)
- **URL**: https://github.com/tefkah/fromsoft-fts
- **내용**: Elden Ring + Bloodborne 아이템 설명 및 NPC 대사 검색 가능 DB
- **포맷**: JSON
- **언어**: 영어
- **데모**: https://fromsoft-fts.vercel.app/
- **Stars**: 3 / 2025년 생성, 활발히 유지보수 중

### 3. Elden Ring Lorebook
- **URL**: https://github.com/jeremy-green/elden-ring-lorebook
- **내용**: SillyTavern AI 포맷으로 정리된 로어 컬렉션
- **용도**: 참고 / AI 프롬프트 보조

### 추출 도구 (게임 소유 시 직접 추출용)

| 도구 | URL | 용도 |
|------|-----|------|
| Yabber | https://github.com/JKAnderson/Yabber | `.bnd` / `.fmg` 언팩 |
| SoulsFormats | https://github.com/JKAnderson/SoulsFormats | `.fmg` `.param` 파싱 라이브러리 |
| UXM | https://github.com/Nordgaren/UXM-Selective-Unpack | 게임 파일 선택적 언팩 |

> **주의**: 게임 파일 직접 추출은 Elden Ring 소유 시에만 가능합니다.
> 이 프로젝트는 공개된 데이터셋(erdb, fromsoft-fts)을 기본 소스로 사용합니다.

## 실행 방법

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 원본 데이터 다운로드 (items JSON + FMG HTML)
python scripts/fetch_erdb.py

# 3. 아이템 / 스킬 / 마법 파싱
python scripts/parse_fmg.py

# 4. NPC 대사 / 컷씬 자막 파싱
python scripts/parse_html.py

# 5. 통합 lore_entries.json 생성
python scripts/merge_entries.py

# 6. SQLite + FTS5 DB 빌드
python scripts/build_db.py

# 7. Streamlit 앱 실행
streamlit run app/app.py
```

> Ollama가 없으면 추론 기능은 비활성화됩니다.
> `ollama serve` + `ollama pull llama3.1` 후 토글 ON.

## 데이터 출처

## 로드맵

### Phase 1 — 데이터 파이프라인 (현재)
- [x] 프로젝트 구조 세팅
- [x] erdb / fromsoft-fts 데이터 수집 스크립트
- [ ] 데이터 정제 및 한국어 매핑
- [ ] SQLite DB 적재 스크립트

### Phase 2 — 백엔드 + UI
- [ ] SQLite FTS5 인덱싱
- [ ] Ollama llama3.1 연동 (원문 → 추론 생성)
- [ ] Streamlit 챗봇 UI ([오피셜] / [추론] 섹션 분리)

### Phase 3 — 고도화
- [ ] 한국어 원문 매핑 확충
- [ ] 검색 정확도 개선 (임베딩 기반 유사도 검색 검토)
- [ ] 출처 표시 강화

## 기여

데이터 오류, 누락된 텍스트, 번역 이슈는 Issue로 남겨주세요.
