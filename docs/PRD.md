# AUSHADHI — Product Requirements Document
### Autonomous Medicine Supply Intelligence System

> Version: 1.0  
> Hackathon: All Things Agentic (Google) | Deadline: Aug 31, 2026  
> Track: **The Taskmaster**  
> Portfolio status: Production-ready architecture, built to extend beyond hackathon

---

## 1. EXECUTIVE SUMMARY

**AUSHADHI** (Sanskrit: "life-giving herb / medicine") is a multi-agent AI system that autonomously monitors medicine inventory across rural health centers, predicts stockouts before they happen, generates purchase orders without human intervention, and — its defining capability — **detects disease outbreaks from medicine consumption patterns before any surveillance system does.**

India's rural healthcare system has 1.6 lakh (160,000) Sub-Centres, PHCs, and CHCs. An estimated 40% run out of essential medicines every month. The cause is not a shortage of supply — it is a complete absence of intelligent monitoring. A health worker fills paper registers. A clerk enters data. A district officer reviews a PDF three weeks later. By then, the stockout has already happened, and in many cases, a preventable disease cluster has already formed.

AUSHADHI breaks this chain autonomously.

---

## 2. THE CORE INSIGHT (The "Twist" — Judges Read This)

**Standard supply chain management** watches stock levels and reorders. Every inventory system does this.

**AUSHADHI does something no inventory system does:** it watches *what* medicines are being consumed and *detects disease outbreaks* from the consumption signature — before a single patient is reported, before a single health worker files an alert.

When three health centers in a cluster suddenly increase ORS + Zinc + IV fluid consumption by 280% simultaneously, that is not random demand variation. That is a cholera outbreak forming. AUSHADHI detects it, flags the cluster, routes alerts to the district health officer, and raises emergency procurement — all in under 60 seconds, autonomously.

This is the insight that transforms a supply chain tool into an epidemiological surveillance system.

---

## 3. BYOF NARRATIVE (Bring Your Own Friction)

*"While building VaidyaAI, I visited PHCs in East Godavari district, Andhra Pradesh. I watched a doctor turn away a child with severe dehydration because ORS packets were out of stock. The last stock entry was 23 days ago. The district supply officer had no idea. Nobody had any idea. There was no system watching. I built AUSHADHI because that child should not have been turned away, and the system that failed her was fixable."*

This narrative is authentic, specific, emotionally resonant, and directly tied to the builder's prior work. It will score maximum on the BYOF criterion.

---

## 4. USER PERSONAS

### P1 — ASHA Worker / ANM (Primary Data Source)
- Fills paper/digital consumption registers daily
- Has no visibility into district supply chain
- Goal: spend less time on paperwork, know when medicines will run out

### P2 — Medical Officer In-Charge (PHC Doctor)
- Responsible for patient care at PHC
- Spends significant time chasing medicine supplies
- Goal: never run out of essential medicines, get early warning of patient surges

### P3 — District Health Officer (Primary Dashboard User)
- Oversees 20–50 health centers across a district
- Currently works from monthly PDF reports
- Goal: real-time visibility into supply chain + early outbreak warning

### P4 — State Programme Manager
- Monitors district-level performance
- Needs aggregate data for budget and policy decisions
- Goal: automated compliance reports, outbreak trend analysis

### P5 — Hackathon Judge
- Needs to see: autonomous agents acting, GCP deployment, clear BYOF, "Twist" present
- Will read README, watch 4-minute video, check GitHub
- Goal: see something they've never seen before

---

## 5. FEATURE REQUIREMENTS

### P0 — Core (Hackathon Demo Must Work)

| ID | Feature | Description |
|----|---------|-------------|
| F01 | Inventory Sentinel Agent | Monitors stock levels, triggers pipeline on threshold breach |
| F02 | DQMS Validation Agent | Cleans and validates consumption data before analysis |
| F03 | Forecast + Outbreak Agent | Gemini predicts demand AND detects disease clusters |
| F04 | Procurement Agent | Auto-generates purchase orders, routes to nearest warehouse |
| F05 | Alert + Report Agent | Notifies district officer, generates compliance report |
| F06 | Real-time Dashboard | Inventory heatmap, outbreak alerts, PO pipeline |
| F07 | Agent Activity Log | Every agent decision timestamped and auditable |
| F08 | SSE Real-time Updates | Dashboard updates live as agents fire |
| F09 | GCP Deployment | All services on Cloud Run, verifiable |
| F10 | Demo Mode | Pre-loaded data + "Simulate stockout" button |

### P1 — Score Boosters

| ID | Feature | Description |
|----|---------|-------------|
| F11 | Consumption Logger | POST endpoint to log daily medicine usage |
| F12 | Health Center Map | Leaflet map with color-coded inventory status |
| F13 | Outbreak Heat Map | Geographic visualization of outbreak alerts |
| F14 | PO Status Tracking | Purchase order lifecycle (GENERATED → APPROVED → DISPATCHED → DELIVERED) |
| F15 | DQMS Report | Data quality scores per health center |
| F16 | Manual Override | District officer can approve/reject auto-generated PO |

### P2 — Bonus Points

| ID | Feature | Description |
|----|---------|-------------|
| F17 | Gemma Offline | Gemma 2 for edge forecasting without internet (+0.2 pts) |
| F18 | Social Post | #AllThingsAgenticHackathon post (+0.2 pts) |
| F19 | Dev.to Article | Build walkthrough published (+0.2 pts) |
| F20 | Voice Input | ASHA worker can log consumption by voice in Telugu |

---

## 6. PORTFOLIO ROADMAP (Beyond Hackathon)

### Phase 1: Hackathon (Now)
- Single district, 8 health centers, simulated data
- Web dashboard, API key auth
- Demo-ready on GCP

### Phase 2: Pilot (3–6 months post-hackathon)
- Real HMIS (Health Management Information System) integration
- Mobile PWA for ASHA workers (consumption logging from phone)
- SMS alerts to district officers
- Actual East Godavari district pilot with NHM collaboration

### Phase 3: Scale (6–18 months)
- Multi-district, multi-state deployment
- ML model training on real consumption patterns
- Integration with eAushadhi (Government medicine tracking system)
- MOHFW (Ministry of Health) API integration
- GIS-based outbreak mapping

### Phase 4: Impact
- 1,000+ health centers monitored
- Measurable reduction in stockout incidents
- Early outbreak detection with measurable lead time advantage
- Government health system transformation

---

## 7. NON-FUNCTIONAL REQUIREMENTS

### Performance
- Sentinel polling cycle: every 30 minutes (Cloud Scheduler)
- Full agent pipeline completion: < 2 minutes
- Dashboard refresh: real-time via SSE
- API response time: < 500ms

### Data Quality (DQMS Integration)
- Reject consumption records with impossible values (negative stock, consumption > stock)
- Flag missing records (center didn't report in 48h)
- Deduplicate records (same center, same date, same medicine)
- Quality score per health center, per day

### Cost (Hackathon)
- Cloud Run: min-instances=0
- Gemini Flash only (not Pro)
- Target: < $10 total GCP spend
- Shut down all services after recording demo video

---

## 8. OUT OF SCOPE (Hackathon Version)

- Real government HMIS integration (simulated data only)
- Mobile app for ASHA workers (web dashboard only)
- Actual SMS/WhatsApp delivery (logged to Cloud Logging)
- Multi-district deployment (single East Godavari district simulation)
- Real patient data (all data is synthetic)
- HIPAA/health data compliance (demo only)
- User authentication beyond API key

---

## 9. SUCCESS METRICS

| Metric | Target | How Proved |
|--------|--------|-----------|
| Full pipeline fires autonomously | Yes | Demo video: stockout detected → PO generated in < 2 min |
| Outbreak detected from data | Yes | Demo: consumption spike → Gemini outbreak alert |
| All 5 agents visible in logs | Yes | Agent activity log on dashboard |
| GCP deployment verified | Yes | Cloud Run URL + dashboard in GCP Console |
| DQMS layer validates data | Yes | Show data quality score and rejection of bad record |
| Architecture diagram clear | Yes | README + video |

---

*End of PRD — this document establishes what AUSHADHI is, why it matters, and what makes it win.*
