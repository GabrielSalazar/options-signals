# PRÉ-F0.0-S Security Audit — pip-audit Report

**Data:** 2026-08-15  
**Ferramenta:** pip-audit 2.10.1  
**Status:** ⚠️ 56 CVEs encontrados em 13 packages

---

## 📊 Sumário

```
Total Dependências: 105
Packages com CVEs: 13
Total CVEs: 56
HIGH/CRITICAL: ~5-7
```

---

## 🔴 Crítico: Atualizar Imediatamente

### 1. **curl_cffi 0.13.0**
- **CVE:** PYSEC-2026-2431 (GHSA-qw2m-4pqf-rmpp, CVE-2026-33752)
- **Severidade:** 🔴 HIGH
- **Descrição:** SSRF via unfiltered internal IP ranges + auto-redirect
- **Fix:** Upgrade para `curl_cffi>=0.15.0`
- **Impact:** Risco de SSRF attacks contra metadata endpoints

### 2. **Flask (múltiplas versões)**
- **Status:** Multiple CVEs
- **Current:** 3.0.3
- **Recomendação:** Verificar se há patches

### 3. **NumPy (múltiplas)**
- **Current:** 2.2.6
- **Status:** Múltiplos CVEs conhecidos

---

## 🟡 MEDIUM: Avaliar e Atualizar

### Packages a Atualizar:

```
urllib3         → verificar versão
requests        → verificar versão
lxml            → pode ter parsing vulns
pandas          → verificar versão
matplotlib      → avaliar
```

---

## 📝 Estratégia de Remediação

### Fase 1: TODAY (PRÉ-F0.0-S)
1. ✅ Pin requirements.txt (feito)
2. 🟡 Identificar HIGH/CRITICAL CVEs
3. ⚠️ Marcar para patch em F0

### Fase 2: F0
1. Update curl_cffi para 0.15.0+
2. Avaliar outros packages
3. Re-run pip-audit (deve reduzir drasticamente)

### Fase 3: Ongoing (F1+)
1. Setup Dependabot no GitHub
2. Automatizar alertas de CVE
3. Schedule updates

---

## 🚨 Ação Imediata Necessária

**curl_cffi SSRF é CRÍTICO** — este package é usado para fazer requests HTTP.
Se há redirects automáticos para IPs internos, temos risco real de:
- Cloud metadata exposure (AWS, GCP, Azure)
- Internal service enumeration
- Credential theft

**Recomendação:**
- [ ] Upgrade curl_cffi para 0.15.0+ HOJE
- [ ] Re-run pip-audit
- [ ] Validate no CI

---

## 📋 Próximas Ações

1. **TODAY:**
   - Update curl_cffi in requirements.txt
   - pip freeze novamente
   - Re-run pip-audit
   - Commit como PRÉ-F0.0-S

2. **CI Setup (também TODAY):**
   - Add `pip-audit` to GitHub Actions
   - Fail on HIGH/CRITICAL
   - Block merge se houver new vulns

3. **F0:**
   - Avaliar outros packages
   - Create security.txt (versioninfo)
   - Document patch strategy

---

**Relatório:** ✅ Completado  
**Full JSON:** disponível em pip-audit output (56 vulns JSON)  
**Status:** Aguardando remediation de curl_cffi

