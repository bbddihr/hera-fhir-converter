# 개발 계획서 — FHIR Auto-Converter (Hera)

> **기준 문서:** `Hera_PRD.md`
> **빌드 성격:** 해커톤 MVP (Streamlit 프로토타입, 5분 시연, 솔로 빌드)
> **핵심 원칙:** *수직 슬라이스 먼저* — XML 1건이 끝까지(분류→매핑→검증→출력) 흐르는 파이프라인을 가장 먼저 완성하고, 그 뒤에 도메인 깊이·멀티서식·UI를 붙인다.
> **가정:** 솔로 ~3 dev-day 윈도우. 시간 압축 시 §컷라인 적용으로 1.5 dev-day까지 축소 가능. (팀/기간이 다르면 단계 effort만 재배분)

---

## 0. 아키텍처 한눈에

```
XML 입력
   │
   ▼
[Profiler]  ① cache lookup(시그니처 해시) → 미적중 시 ② semantic classify(Claude) → ③ cache write
   │            산출: form_type, confidence, target_task, target_role
   ▼
[Router]  form_type 분기
   ├─ 검사형 → [Lab Mapper]   Observation + DiagnosticReport  → Bundle(collection)
   └─ 서사형 → [Narrative Mapper] Composition + Procedure/Encounter/Condition/… → Bundle(document)
   │
   ▼
[Validator]  fhir.resources R4 invariant 검증
   │
   ▼
[Contract]  { form_type, classification, target_task, target_role, fhir_bundle, validation }
   │
   ▼
[Streamlit UI]  Source panel │ Output panel(JSON+배지) │ Processing logs
```

---

## 1. 레포 구조 (목표 형상)

```
hera/
├── app.py                       # Streamlit 진입점 (UI 3패널)
├── hera/
│   ├── pipeline.py              # 오케스트레이터: xml → contract
│   ├── contract.py              # 출력 계약 Pydantic 모델
│   ├── profiler/
│   │   ├── signature.py         # 구조 시그니처 해시
│   │   ├── cache.py             # signature → form_type 캐시
│   │   └── semantic.py          # Claude 의미 분류 (Y-KNOT식 모듈 프롬프트)
│   ├── mapper/
│   │   ├── router.py            # form_type → mapper 디스패치
│   │   ├── value_parser.py      # value 분기/참고치/interpretation/UCUM
│   │   ├── lab.py               # Observation + DiagnosticReport
│   │   └── narrative.py         # Composition 중심 조립
│   ├── rulesets/
│   │   ├── lab-observation.yaml
│   │   └── anesthesia-composition.yaml
│   ├── tasks.py                 # form_type → target_task / target_role
│   └── validator.py             # R4 invariant 검증
├── samples/                     # 데모 XML
│   ├── random_urine.xml
│   ├── cbc_chemistry.xml
│   └── anesthesia_record.xml
├── tests/
│   ├── fixtures/                # 입력 XML ↔ 기대 JSON
│   ├── test_value_parser.py
│   ├── test_lab_mapper.py
│   └── test_profiler.py
├── requirements.txt
└── README.md
```

---

## 2. 단계별 개발 계획 (Phase)

각 Phase는 독립 검증 가능한 산출물(DoD)을 가진다. effort는 반일(HD, ≈4h) 단위.

### Phase 0 — Scaffold · ~2h
- 레포/venv/`requirements.txt`(python 3.11, streamlit, fhir.resources, lxml, pyyaml, anthropic, pytest)
- 디렉터리 스켈레톤 + 빈 모듈 stub, `ANTHROPIC_API_KEY` 환경변수 로딩
- `app.py`에 3패널 빈 레이아웃
- **DoD:** `streamlit run app.py`로 좌(입력)·중(실행 버튼)·우(출력/로그) 레이아웃이 뜬다.

### Phase 1 — Lab 수직 슬라이스 (end-to-end) · 1 HD
가장 먼저 "한 건이 끝까지 흐르는" 파이프라인을 만든다. **이 단계에서 form_type은 `lab`으로 하드코딩**해 분류기 없이 매핑·검증·출력을 먼저 검증.
- `contract.py`: 출력 계약 모델 정의 (스파인)
- `value_parser.py`: 단일 숫자 → `valueQuantity` 1케이스만
- `lab.py`: `Observation` 생성 + `DiagnosticReport` 그룹화 → `Bundle(collection)`
- `validator.py`: `fhir.resources`로 R4 검증
- `pipeline.py`: xml → (lab 고정) → bundle → contract
- `samples/random_urine.xml` 1건
- **DoD:** Random Urine XML 투입 → R4 valid `collection` Bundle 출력이 UI에 표시. → **데모 시나리오 1 동작.**

### Phase 2 — Lab 도메인 심화 · 1 HD
- `value_parser.py` 확장: 범위 → `valueRange`, 정성 → `valueCodeableConcept`/`valueString` 자동 분기
- 참고치 파싱(양방향·단방향·정성·결측) + 결과값 비교 → `interpretation` H/L/N 자동 주입(HL7 v3) + UCUM 단위 매핑
- `rulesets/lab-observation.yaml`로 항목 매핑 외부화
- `samples/cbc_chemistry.xml`(정량+정성 혼합)
- `tests/`: 입력 XML ↔ 기대 Bundle 회귀 fixture (pytest)
- **DoD:** 정량/정성 혼합 변환 + 비정상 자동 식별이 로그에 요약(예 "정상 9 / 비정상 3"). → **시나리오 2·3 동작.**

### Phase 3 — Semantic Profiler + TASK 계약 · 1 HD
핵심 차별점(의미 분류)과 2단 계약을 붙인다.
- `tasks.py`: form_type → (target_task, target_role) 매핑 테이블
- `semantic.py`: Claude Sonnet 4.6 프롬프트로 XML 텍스트 → `form_type`+`confidence` (Y-KNOT식 모듈 분리: 분류/근거추출 분리)
- `signature.py`+`cache.py`: 구조 시그니처 해시 → lookup/write
- `pipeline.py`: Profiler를 1차로 삽입 (cache → semantic → cache), contract에 `classification`/`target_task`/`target_role` 채움
- **DoD:** lab 하드코딩 제거 후에도 자동으로 lab 판별, 계약 객체 완성, 로그에 분류 경로(`semantic` / `cache hit`) 표시.

### Phase 4 — 멀티서식 라우팅 (마취 → Composition) · 1 HD
"Lab 변환기가 아님"을 증명하는 단계.
- `narrative.py`: `Composition`(문서 골격) + `Procedure`(마취) + `Observation`(術中 vitals) + `MedicationAdministration` → `Bundle(document)`
- `rulesets/anesthesia-composition.yaml`, `samples/anesthesia_record.xml`
- `router.py`: form_type → lab/narrative 디스패치
- **DoD:** 마취기록 XML → 의미분류 `anesthesia_record` → `document` Bundle + `target_task=마취 협진 회신서`/`target_role=마취과` 동봉. → **시나리오 4 동작.**

### Phase 5 — UI 마감 + 데모 리허설 · 1 HD
- 3패널 완성: XML 신택스 하이라이팅 입력기 / JSON 뷰어 / 실시간 로그
- 배지: ✓Valid·✗Invalid(+오류), `form_type`/`target_task`/`target_role` 메타 배지
- 샘플 로더 드롭다운, 클립보드 복사·JSON 다운로드
- 데모 드라이런 + 타이밍(5분 컷)
- **DoD:** 시나리오 1→4를 끊김 없이 5분 내 시연.

### Stretch — 시나리오 5 (미지 XML) · 0.5 HD
- 룰셋에 없는 신규 서식 투입 → semantic 경로가 form_type 추론 → "no ruleset → LLM inference" 로그 노출
- **DoD:** 캐시에 없는 입력도 분류까지는 동작.

---

## 3. 빌드 의존 순서 & 크리티컬 패스

```
P0 ─▶ P1(슬라이스) ─▶ P2(Lab 심화) ─┐
                                    ├─▶ P5(UI/데모)
        P3(Profiler+계약) ─▶ P4(서사형) ┘
```
- **크리티컬 패스:** P0 → P1 → P2 → P5 (이 라인만으로도 시나리오 1–3 데모 성립)
- P3·P4는 P2와 병렬 진행 가능하나, P4는 P3(분류기) 완료에 의존.

---

## 4. 핵심 데이터 계약 (먼저 고정할 것)

P1에서 가장 먼저 박아야 하는 출력 스키마. 이후 전 모듈이 여기에 맞춰 작성된다.

```json
{
  "form_type": "anesthesia_record",
  "classification": { "confidence": 0.97, "via": "semantic | cache" },
  "target_task": "마취통증의학과 협의진료 회신서",
  "target_role": "마취과 전문의",
  "fhir_bundle": { "resourceType": "Bundle", "type": "document | collection", "entry": [] },
  "validation": { "r4_valid": true, "invariants": "12/12", "errors": [] }
}
```

룰셋(YAML) 최소 형상 예:
```yaml
form_type: lab
resource: Observation
category: laboratory
items:
  - source_field: "혈색소"
    code: { system: local, code: "HGB" }   # MVP는 local 코드, LOINC는 로드맵
    unit: "g/dL"                            # UCUM 매핑 대상
    value_kind: quantity                    # quantity | range | qualitative
```

---

## 5. 테스트 전략

- **회귀 fixture(pytest):** 데모 샘플 3건 각각 "입력 XML ↔ 기대 Bundle"을 고정. 룰셋 수정 시 회귀 즉시 탐지.
- **검증 게이트:** 모든 출력은 `fhir.resources` R4 invariant를 통과해야 contract `r4_valid=true`. 실패 시 errors 노출(UI 배지 연동).
- **분류기 테스트:** form_type 라벨링된 샘플로 semantic 분류 정확도 스폿체크(데모 4서식 + 미지 1건).
- **단위 테스트 우선순위:** `value_parser`(분기·참고치·interpretation)가 가장 버그 잦은 지점 → 케이스 집중.

---

## 6. 리스크 & 완화

| 리스크 | 영향 | 완화 |
|---|---|---|
| 라이브 LLM 호출이 데모 중 지연/실패 | 시연 끊김 | **데모 샘플 4건의 시그니처를 사전 캐시 적재** → 시연은 cache hit로 결정론적 동작. semantic 경로는 시나리오 5에서만 라이브 호출 |
| `Composition` document Bundle invariant 까다로움(Patient 참조·narrative text 필수 등) | P4 지연 | 최소 valid 형상으로 시작(섹션 최소화), 라우팅 증명에 집중. 화려한 섹션은 컷 가능 |
| 룰셋 항목 욕심(스코프 크립) | 일정 압박 | MVP 룰셋은 **데모에 등장하는 항목만**. 100+ 항목은 로드맵 |
| `fhir.resources` 버전·필드 strictness | 디버깅 시간 | P1에서 가장 단순한 valid Observation부터 통과시키고 점증 |

---

## 7. 데모 준비 체크리스트 (Phase ↔ 시나리오)

- [ ] 시나리오 1 (Random Urine) ← P1
- [ ] 시나리오 2 (CBC+Chemistry 값 분기) ← P2
- [ ] 시나리오 3 (임상 판독 interpretation) ← P2
- [ ] 시나리오 4 (마취 → Composition + TASK 계약) ← P3+P4  ← *차별화 포인트*
- [ ] 시나리오 5 (미지 XML, optional) ← Stretch
- [ ] 4서식 시그니처 사전 캐시 적재
- [ ] 5분 타이밍 리허설 완료

---

## 8. 컷라인 (시간 부족 시 우선순위)

1. **절대 사수:** P0 → P1 → P2 → P5 = 시나리오 1–3 + 검증 + UI. (단독으로 완결된 데모)
2. **강력 권장 사수:** P3 + P4 = 분류기·TASK 계약·시나리오 4. "멀티서식 플랫폼"이라는 메시지를 증명하는 부분이라 가능한 끝까지 지킴.
3. **가장 먼저 컷:** Stretch(시나리오 5) → P4 서사형 섹션 디테일 → LOINC 등 로드맵 항목.

> 즉, **최악의 경우에도 시나리오 1–3는 무조건 돌아가는 상태**를 유지하고, 여력에 따라 P3·P4를 얹는다.
