# Hera — FHIR Auto-Converter

병원 EMR 의무기록 **XML**을 의미 기반으로 서식 판별하고 **HL7 FHIR R4 리소스(JSON)** 로 자동 변환하는 전처리 엔진. 동시에 다운스트림 생성 TASK를 결정해 2단 생성 플랫폼이 곧바로 소비할 **계약 객체**를 출력한다.

> LLM 의료기록 생성 플랫폼의 **FHIR 전처리(입력) 단계** — 2단 파이프라인의 1단.

## 핵심 원칙

- **LLM은 분류·라우팅 결정만**, FHIR 리소스 조립은 **결정론적 룰셋 + 코드** (R4 검증 안정성 확보)
- 검사형 = `collection`/Observation+DiagnosticReport, 서사형 = `document`/Composition
- 구조 시그니처 캐시로 반복 입력 가속, 미적중 시 Claude 의미 분류

## 빠른 시작

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows (PowerShell: .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
cp .env.example .env            # ANTHROPIC_API_KEY 입력
streamlit run app.py
```

## 문서

- [Hera_PRD.md](Hera_PRD.md) — 제품 요구사항 정의서
- [Hera_DevPlan.md](Hera_DevPlan.md) — 개발 계획서 (Phase 0~5)

## 기술 스택

Python 3.11 · Streamlit · `fhir.resources` · `lxml` · PyYAML · Claude Sonnet 4.6 (`claude-sonnet-4-6`) · pytest

> ⚠️ 모든 샘플·테스트 데이터는 **합성**이다. 실제 환자정보(PHI)를 LLM API로 전송하지 않는다.
