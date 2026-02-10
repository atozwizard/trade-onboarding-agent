# GitHub Token 설정 및 리포지토리 생성 가이드

## 방법 1: 환경 변수 사용 (권장)

### 1단계: 토큰 환경 변수 설정
PowerShell에서:
```powershell
$env:GH_TOKEN = "your_github_token_here"
```

### 2단계: 리포지토리 생성 및 푸시
```powershell
gh repo create trade-onboarding-agent --public --description "AI-powered onboarding simulator for trading company new employees using Upstage Solar API" --source=. --remote=origin --push
```

---

## 방법 2: 새 토큰 생성 (권한 부족 시)

### 필요한 권한
- `repo` (전체 저장소 제어)
- `read:org` (조직 읽기)
- `workflow` (워크플로우)

### 토큰 생성 방법
1. https://github.com/settings/tokens/new 접속
2. Note: "TradeOnboarding Agent CLI"
3. Expiration: 선택
4. 권한 선택:
   - ✅ repo (전체)
   - ✅ read:org
   - ✅ workflow
5. "Generate token" 클릭
6. 토큰 복사

### 토큰 사용
```powershell
$env:GH_TOKEN = "복사한_토큰"
gh repo create trade-onboarding-agent --public --description "AI-powered onboarding simulator for trading company new employees using Upstage Solar API" --source=. --remote=origin --push
```

---

## 방법 3: 수동으로 리포지토리 생성 후 푸시

### 1단계: GitHub에서 리포지토리 생성
1. https://github.com/new 접속
2. Repository name: `trade-onboarding-agent`
3. Description: `AI-powered onboarding simulator for trading company new employees using Upstage Solar API`
4. Public 선택
5. "Create repository" 클릭

### 2단계: 로컬에서 푸시
```powershell
git remote add origin https://github.com/YOUR_USERNAME/trade-onboarding-agent.git
git branch -M main
git push -u origin main
```

---

## 이슈 생성

리포지토리 푸시 완료 후:

```powershell
# GitHub CLI 사용
gh issue create --title "[완료] TradeOnboarding Agent 초기 구현" --body-file docs/IMPLEMENTATION_REPORT.md --label enhancement,documentation

# 또는 웹에서 수동 생성
# https://github.com/YOUR_USERNAME/trade-onboarding-agent/issues/new
```

---

## 빠른 실행 (토큰이 있는 경우)

```powershell
# 1. 토큰 설정
$env:GH_TOKEN = "your_token_here"

# 2. 리포지토리 생성 및 푸시
gh repo create trade-onboarding-agent --public --description "AI-powered onboarding simulator for trading company new employees using Upstage Solar API" --source=. --remote=origin --push

# 3. 이슈 생성
gh issue create --title "[완료] TradeOnboarding Agent 초기 구현" --body-file docs/IMPLEMENTATION_REPORT.md --label enhancement,documentation
```
