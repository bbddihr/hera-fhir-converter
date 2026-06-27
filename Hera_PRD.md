# PRD — FHIR Auto-Converter (Hera)

> **문서 성격:** 제품 요구사항 정의서 (개발문서)
> **작성일:** 2026-06-26
> **프로젝트명:** FHIR Auto-Converter (코드네임 *Hera*)
> **포지셔닝:** LLM 의료기록 생성 플랫폼의 **FHIR 전처리(입력) 단계**

---

## 0. 한 줄 정의

> 병원 EMR에서 들어온 **다양한 의무기록 서식(XML)** 을, **내용 의미(semantic)** 기준으로 어떤 서식인지 판별하여 **HL7 FHIR R4 리소스(JSON)** 로 자동 변환하고, **동시에 다운스트림 생성 TASK를 결정**해 생성 플랫폼으로 넘기는 전처리 엔진.

이 문서가 정의하는 시스템은 **2단 파이프라인의 1단(전처리)** 이다.

```
[1단: Hera — 본 PRD]                         [2단: 생성 플랫폼 (Y-KNOT류)]
원본 서식 XML ─▶ 의미 분류 ─▶ FHIR 리소스 조립 ─▶  { fhir_bundle, target_task, target_role }
              (서식 판별)   (서식별 라우팅)            │
                                                      └─▶ LLM이 target_task 문서 생성
                                                          (마취 협진 회신서 / 응급진료기록 …)
```

1단의 출력은 단순한 FHIR JSON이 아니라 **2단이 곧바로 소비할 수 있는 계약(contract)** 이어야 한다. → §5.3, §6 참조.

---

## 1. 배경 및 문제점

국내외 의료기관은 디지털 헬스케어 전환과 의료 데이터 표준화 흐름 속에서, 자체 EMR 데이터를 HL7 FHIR 국제 표준으로 변환해야 하는 압력을 받고 있다. 현장에는 다음 3가지 구조적 문제가 존재한다.

**비표준화된 의료 데이터.** 병원마다 자체 EMR 형식(XML, CSV, 비정형 텍스트)으로 의무기록을 관리하고 있어 외부 시스템 연동, 다기관 연구, AI 학습 데이터 활용이 사실상 불가능하다. 같은 "혈색소" 검사도 병원별로 필드명·코드·단위 표기가 모두 다르며, 같은 "마취기록"이라도 서식의 태그 구조가 벤더마다 제각각이다.

**높은 도입 비용.** EMR → FHIR 변환은 FHIR R4 스펙(150+ 리소스, 800+ 필드)을 이해하는 개발자와, 임상 용어를 표준 코드(LOINC, SNOMED CT, UCUM)에 매핑할 수 있는 의료 전문가가 동시에 투입되어야 하는 작업이다. 병원 1곳 기준 평균 3–6개월, 수억 원 규모의 매핑 프로젝트가 필요하다.

**휴먼 에러 및 운영 부담.** 참고치(Reference Range)와 결과값을 일일이 대조하는 판독 과정에서 누락·오류가 빈발한다. EMR 스키마가 한 번 변경되면 전체 매핑 정의서를 재작업해야 한다.

**시장 신호.** 보건복지부 의료데이터 중심 정책 가속화(2024–2026), HIRA·KDCA의 FHIR 도입 본격화, 임상 RWD(Real World Data) 시장 급성장, 그리고 LLM의 임상 도메인 정확성 임계점 도달(Claude 4, MedGemma 27B). 이 변화 속에서 "수개월·수억 원 매핑 작업을 LLM 기반으로 자동화"하는 솔루션의 사업화 가능성이 빠르게 열리고 있다.

---

## 2. 타겟 사용자

**최종 서비스 이용자(2단 결과물 소비자): 의료인(의사·간호사 등).** 본 시스템의 산출물은 궁극적으로 임상의가 사용할 생성 문서(마취 협진 회신서, 응급진료기록 등)의 입력이 된다.

**1차 사용자:** 의료기관 EMR/HIS 운영팀, 임상 데이터 매핑 담당자. 수작업으로 매핑 정의서를 작성·유지하는 의무기록팀, FHIR 도입 프로젝트를 진행 중인 IT 운영팀.

**2차 사용자:** 임상 연구자. CDM(Common Data Model) 변환이 필요한 연구자, 다기관 데이터 통합 연구 수행자.

**3차 사용자:** 디지털 헬스케어 스타트업 및 헬스테크 기업. FHIR 호환 데이터를 요구하는 헬스케어 SaaS, AI 진단·의료기기 인허가를 위해 표준 데이터가 필요한 기업.

---

## 3. 해결책 (Solution)

사용자가 원문 EMR 서식(XML)을 입력하면, 시스템이 자동으로:

- **의미 기반 서식 판별 (Semantic Profiling):** XML의 **태그 구조가 아니라 안의 텍스트 내용(semantic)** 을 읽어 어떤 의무기록 서식인지(마취기록 / 외래초진기록 / 진단검사기록 / 응급진료기록 …) 분류한다. 동일 구조가 반복되면 구조 시그니처를 **캐시로 활용해 가속**한다. (→ §5.2)
- **서식별 리소스 라우팅 (Form-aware Mapping):** 판별된 서식에 따라 적절한 FHIR 리소스 조립 경로로 분기한다. 검사형 서식은 `Observation + DiagnosticReport`, 서사형 서식(마취·외래·응급)은 `Composition` 중심 document Bundle로 조립한다. (→ §5.2, §3-매핑표)
- **임상 판독 자동화:** (검사 도메인) 결과값과 참고치를 비교해 H(High)/L(Low)/N(Normal) interpretation 코드를 HL7 표준에 따라 자동 부여한다.
- **TASK 결정:** 분류 시점에 **다운스트림 생성 TASK와 대상 의료인 역할**을 함께 확정해 출력에 포함한다. (→ §5.3)
- **FHIR Best Practice 적용 + 자동 검증:** R4 valid JSON Bundle을 생성하고 `fhir.resources` 라이브러리로 invariant 검증을 통과시킨다.

전체 변환은 **캐시 적중 시 1초 이내**, **LLM 의미분류 경로에서도 수 초 이내**에 완료되며, 출력은 외부 FHIR 시스템 연동 + 2단 생성 플랫폼 투입이 동시에 가능한 상태로 제공된다.

### 3-매핑표. 서식 → FHIR 리소스 → 생성 TASK

| 입력 서식 (원본 XML) | 핵심 FHIR 리소스 (R4) | Bundle type | 생성 TASK (2단) | 대상 의료인 | MVP 상태 |
|---|---|---|---|---|---|
| **진단검사기록** | `Observation`(laboratory) + `DiagnosticReport`(그룹화) | `collection` | 검사결과 판독/요약 | 검사 의뢰의 | ✅ MVP 완성 |
| **마취기록** | `Procedure`(마취) + `Observation`(術中 vitals) + `MedicationAdministration`(약물) + `Composition` | `document` | 마취통증의학과 협의진료 회신서 | 마취과 전문의 | 🔜 라우팅 확장 |
| **외래초진기록** | `Encounter` + `Condition`(주호소/진단) + `Observation`(소견) + `Composition` | `document` | 협진 의뢰/회신·초진 요약 | 진료과 의사 | 🔜 라우팅 확장 |
| **응급진료기록** | `Encounter`(class: EMER) + `Condition` + `Observation`(triage/vitals) + `Procedure` + `Composition` | `document` | 응급진료기록 | 응급의학과 의사 | 🔜 라우팅 확장 |

> **설계 원칙:** 검사형은 `collection`/Observation 중심, 서사형(마취·외래·응급)은 `document`/`Composition` 중심이라는 **두 조립 패턴**으로 수렴한다. 리소스 조립 로직은 서식 유형에 따라 분기하며, 새 서식 추가 = 새 라우팅 룰 추가다.

---

## 4. 차별점 (Competitive Advantage)

| 항목 | 기존 도구 (Mirth, Lyniate, HAPI) | FHIR Auto-Converter (Hera) |
|---|---|---|
| 서식 판별 | 개발자가 구조 규칙 하드코딩 | **내용 의미(LLM) 기반 자동 분류** |
| 매핑 정의 방식 | 개발자가 코드로 작성 | 임상 전문가가 YAML 룰셋 수정 |
| 새 EMR 포맷 대응 | 개발자 재작업(주~월 단위) | 룰셋 추가 또는 LLM 추론(시간 단위) |
| 임상 판독 | 별도 룰 엔진 구축 필요 | 변환 단계에서 자동 부여 |
| FHIR 검증 | 별도 validator 호출 | 변환 파이프라인에 통합 |
| 생성 연계 | 없음 (변환에서 종료) | **TASK 계약 출력 → 생성 플랫폼 직결** |
| 학습 곡선 | FHIR 스펙 + 도구 학습 필요 | 매핑 정의서만 작성 |
| 가격 | 라이센스 비용 高 | SaaS 변환 건당 과금 |

---

## 5. 핵심 기능 (Core Features)

### 5.1 Raw Data 입력부 (Source Panel)

- 병원 EMR XML을 그대로 붙여넣는 텍스트 에디터, XML 신택스 하이라이팅
- 기본 테스트용 샘플 데이터 로드(서식 유형별 3–5개 시나리오)
- 입력 데이터 검증(well-formed XML 여부)

### 5.2 분류 & 매핑 엔진 (Profiler & Mapper)

**(A) Profiler — 의미 분류가 1차, 구조 시그니처는 가속용 캐시**

마취·외래·검사처럼 벤더별 태그 구조가 제각각인 다양한 서식을 다루려면, 판별 기준은 구조가 아니라 **내용 의미**여야 한다. 따라서 판별은 LLM 의미 분류를 1차로 두고, 구조 시그니처는 반복 입력을 가속하는 캐시로 사용한다.

```
1) [Cache lookup]  구조 시그니처 해시가 캐시에 있으면 → 즉시 form_type 반환 (결정론적·고속·저비용)
2) [Semantic classify]  미적중 시 → LLM이 XML 텍스트 내용을 읽어 form_type + target_task 분류
3) [Cache write]  분류 결과를 구조 시그니처와 함께 캐시에 적재 → 동일 서식 반복 시 1)에서 가속
```

- **1차 = LLM 의미 분류** (Claude Sonnet 4.6): 텍스트 내용만으로 "어떤 서식인가"를 판단. 구조에 의존하지 않으므로 신규 벤더·신규 서식에 강건.
- **가속 = 구조 시그니처 캐시**: 한 번 본 안정적 구조는 캐시 적중으로 LLM 호출을 건너뛰어 속도·비용·결정론성을 확보.
- 산출: `form_type`, `confidence`, `target_task`, `target_role`.

**(B) Mapper — 서식별 라우팅**

판별된 `form_type`에 따라 조립 경로로 분기한다.

- **검사형 라우팅 (MVP 완성):**
  - 결과값 형태별 자동 분기 — 단일 숫자 → `valueQuantity` / 범위(a~b) → `valueRange` / 정성 → `valueCodeableConcept` 또는 `valueString`
  - 참고치 파싱(양방향·단방향·정성·결측), 결과값-참고치 비교 후 `interpretation` 자동 주입(HL7 v3 표준 코드), UCUM 단위 매핑
  - 개별 `Observation` 생성 + `DiagnosticReport` 그룹화 → `collection` Bundle
- **서사형 라우팅 (마취·외래·응급, 확장):**
  - `Composition`(문서 골격) + 서식별 핵심 리소스(`Procedure`/`Encounter`/`Condition`/`MedicationAdministration` 등) → `document` Bundle
  - 본문 섹션을 의미 단위로 분할해 `Composition.section`에 매핑

### 5.3 결과 출력부 (Output Panel)

출력은 FHIR Bundle 단독이 아니라 **2단 생성 플랫폼이 곧바로 소비하는 계약 객체**다.

```json
{
  "form_type": "anesthesia_record",
  "classification": { "confidence": 0.97, "via": "semantic" },
  "target_task": "마취통증의학과 협의진료 회신서",
  "target_role": "마취과 전문의",
  "fhir_bundle": { "resourceType": "Bundle", "type": "document", "entry": [ ... ] },
  "validation": { "r4_valid": true, "invariants": "12/12" }
}
```

- 표준 들여쓰기 + 신택스 하이라이팅 JSON 뷰어
- R4 valid 배지(✓ Valid / ✗ Invalid + 오류 상세)
- `form_type` / `target_task` / `target_role` 메타 배지 노출
- 원클릭 클립보드 복사 + JSON 다운로드

### 5.4 실시간 프로세싱 로그 (Processing Logs)

- 판별 경로 표시(예: `"semantic classify → form_type=anesthesia_record (conf 0.97)"` 또는 `"cache hit: SLGeneralResult v1"`)
- 결정된 TASK(예: `"target_task=마취 협진 회신서 / role=마취과"`)
- 추론된 리소스 타입(예: `"Composition + Procedure + Observation×6"`)
- 적용 룰셋(예: `"anesthesia-composition-ruleset v1"`)
- 처리 항목 수 / interpretation 요약(검사형, 예: `"정상 9건, 비정상 3건"`)
- FHIR 검증 결과(예: `"R4 invariant 12/12 통과"`)

---

## 6. 사용자 흐름 (User Flow)

1. **데이터 입력:** 좌측 Source XML 패널에 EMR 의무기록 서식을 붙여넣기
2. **변환 실행:** 중앙 [FHIR 변환 실행] 클릭
3. **의미 분류:** 캐시 미적중 시 LLM이 텍스트 내용으로 `form_type` + `target_task` 판별(실시간 로그)
4. **서식별 매핑:** 라우팅에 따라 리소스 조립(검사형 → Observation+DiagnosticReport / 서사형 → Composition document)
5. **자동 검증:** R4 invariant 검증 통과
6. **결과 확인:** 우측에 **계약 객체(JSON)** 출력 — `fhir_bundle` + `target_task` + `target_role` 포함
7. **활용:** 클립보드/다운로드로 외부 FHIR 시스템·연구 DB에 활용, **또는 2단 생성 플랫폼에 그대로 투입**

---

## 7. 기술 스택 (Tech Stack)

**Backend / Engine** — Python 3.11 · FastAPI(API 서버, SaaS 확장 대비) · `fhir.resources`(Pydantic 기반 R4 모델 + validator) · `lxml`(XML 파싱) · PyYAML(룰셋 정의)

**LLM Integration** — Claude API (Anthropic Claude Sonnet 4.6): **1차 의미 분류 + 미지 서식 추론**. 프롬프트 아키텍처는 Y-KNOT 운영급 모듈 분리 설계. 구조 시그니처 캐시로 LLM 호출 최소화.

**Frontend / Demo UI** — Streamlit(해커톤 신속 프로토타이핑) · JSON/XML 신택스 하이라이팅 라이브러리

**검증 / 테스트** — pytest(회귀 테스트 fixture) · FHIR R4 invariant 자동 검증

**개발 도구** — GitHub(버전 관리) · Claude Code / Cursor(AI pair programming)

---

## 8. 데모 시나리오 (Demo Flow)

5분 발표용 시연. 시나리오 1–3으로 검사 도메인의 완성도를 증명하고, 시나리오 4로 "단일 Lab 변환기가 아니라 멀티서식 플랫폼"임을 증명한다.

**시나리오 1 — 단일 검체 변환 (Random Urine).** 입력: Specific Gravity·pH 등 5개 항목 XML. 시연: 분류 → 매핑 → 검증 → JSON. 메시지: "수동 30분 작업이 1초."

**시나리오 2 — 다중 검체 변환 (CBC + Chemistry).** 입력: 정량/정성 혼합 복합 XML. 시연: 결과 형태별 자동 분기(`valueQuantity`/`valueRange`/`valueString`). 메시지: "임상 결과 형태 다양성을 자동 처리."

**시나리오 3 — 임상 판독 자동화.** 시연: 12개 항목 중 비정상 3건 자동 식별 + `interpretation` 코드 부여. 메시지: "판독까지 한 번에."

**시나리오 4 — 멀티서식 라우팅 (마취기록 → Composition).** 입력: 검사가 아닌 **마취기록 XML**. 시연: 의미 분류가 `form_type=anesthesia_record`로 판별 → `Composition` 중심 document Bundle 조립 → 출력에 `target_task=마취 협진 회신서`, `target_role=마취과` 동봉. 메시지: "같은 엔진이 서식을 알아보고 알맞은 리소스·생성 TASK로 분기한다."

**시나리오 5 — 미지의 XML (Optional, Stretch).** 입력: 룰셋에 없는 신규 EMR 형식. 시연: LLM 의미 추론으로 서식 자동 판단. 메시지: "새 EMR 벤더 대응에 개발자 재작업 불필요."

---

## 9. 스코프 & 확장 계획 (Scope & Roadmap)

> **MVP 스코프 선언:** MVP는 **진단검사(Lab) 도메인**으로 깊이를 완성한다. 단, 엔진은 처음부터 **의미 분류 + 서식별 라우팅** 구조로 설계되어, 마취·외래·응급 등 서사형 서식은 **동일 파이프라인에 라우팅 룰을 추가하는 방식**으로 확장된다. 즉 MVP는 "Lab 변환기"가 아니라 "멀티서식 플랫폼의 첫 도메인"이다.

**도메인 완성 (Lab).** 100+ 검사 항목 매핑 룰셋, 3–5개 주요 EMR 벤더 포맷 대응, LOINC 코드 자동 매핑(선택적 활성화).

**도메인 확장 — Multi-Resource Router.** 서사형 라우팅 정식화: `Composition` + `Condition`(진단) / `MedicationRequest`(처방) / `Procedure`(시술) / `Encounter` / `MedicationAdministration`. `Patient` 리소스 자동 생성 및 cross-reference. 마취기록·외래초진·응급진료 라우팅 룰 순차 출시.

**생성 플랫폼 연계.** 1단 출력의 `target_task` 계약을 2단 LLM 생성 플랫폼(Y-KNOT류)과 인터페이스 표준화.

**상용화.** RESTful API 형태 SaaS 출시. 첫 파일럿: 임상 연구 데이터 변환이 필요한 대학병원. 가격: 변환 건당 과금 + 월 구독.

**시장 확장.** 다기관 데이터 통합 플랫폼 연계, 국제 시장(US Core, IPS) 진출, 보험사·의료기기 회사 대상 B2B.

---

## 10. 솔로프리너 사업 비전

**미션:** 임상 데이터의 표준화·연동에 드는 비용과 시간을 1/10로 축소하여, 의료 AI·임상 연구의 진입 장벽을 낮춘다.

**중장기 비전:** 임상 데이터 매핑·표준화 자동화를 시작점으로, 의료기관의 데이터 인프라 전환을 LLM으로 가속하는 1인 SaaS 사업으로 성장. **전처리(Hera) → 생성(플랫폼)** 으로 이어지는 의무기록 자동화 풀스택을 단계적으로 완성한다.

**솔로프리너 강점:** 임상 도메인 깊은 이해(간호사 출신, 임상 AI 운영자), 실무 운영 경험(매핑 정의서·프롬프트 엔지니어링), 빠른 실행력, 콘텐츠 채널 보유(사용자 확보 자산), 임상 AI 네트워크(초기 고객 접근성).
