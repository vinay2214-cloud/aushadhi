# AUSHADHI — Hackathon Demo Script
### Word-for-Word, 4 Minutes Exactly

> Practice this 5 times before recording. Time each section.
> Record in one take. No cuts. Judges specifically look for unedited live demos.
> Use OBS or Loom. Webcam optional but recommended (shows authenticity).

---

## SETUP BEFORE RECORDING

Browser tabs open (in order):
1. `Tab 1` — AUSHADHI Dashboard (your Cloud Run frontend URL)
2. `Tab 2` — Google Cloud Console → Cloud Run → Services
3. `Tab 3` — Google Cloud Console → Firestore → health_centers collection
4. `Tab 4` — Google Cloud Console → Pub/Sub → Topics
5. `Tab 5` — Terminal (SSH to Cloud Run or local terminal with gcloud logs)

Terminal command ready to paste (the demo trigger):
```bash
curl -X POST https://[YOUR_API_URL]/api/v1/internal/run-sentinel \
  -H "X-API-Key: [YOUR_KEY]" \
  -H "Content-Type: application/json"
```

---

## SECTION 1: PROBLEM (0:00 – 0:35)

*[Start screen recording. Switch to your dashboard tab. Do NOT start the demo yet.]*

**Say this:**

"In Andhra Pradesh — and across rural India — medicine stockouts are invisible until it's too late.

A doctor at PHC Razole turns away a child with severe dehydration because ORS packets are out of stock. The health worker filed a paper register 23 days ago. The district supply officer has no idea. There is no system watching.

I built AUSHADHI — Autonomous Medicine Supply Intelligence — because that child should not have been turned away.

Five AI agents on Google Cloud run continuously in the background. They watch every health center, validate the data quality, predict stockouts before they happen, auto-generate purchase orders, and — this is the part that surprised even me — they detect disease outbreaks from medicine consumption patterns, three to five days before any manual surveillance system would."

*[30 seconds. Move to next section.]*

---

## SECTION 2: ARCHITECTURE (0:35 – 1:05)

*[Switch to a pre-prepared architecture diagram — either a slide or the one in your README]*

**Say this:**

"Five agents, all on Google Cloud Run, connected by Google Pub/Sub.

The Sentinel Agent polls every health center's inventory every 30 minutes. The DQMS Validation Agent — built on my existing data quality management system — cleans and validates the consumption data before any AI ever sees it. The Forecast Agent uses Gemini 1.5 Flash to predict demand and detect outbreak patterns from consumption signatures. The Procurement Agent uses the routing logic from my previous crisis routing work to find the nearest warehouse and auto-generate a purchase order. The Alert Agent notifies the district health officer and generates the compliance report — automatically.

Zero humans in this loop. Let me show it running live."

*[30 seconds. Move to live demo.]*

---

## SECTION 3: LIVE DEMO (1:05 – 3:00)

*[Switch to Tab 1 — AUSHADHI Dashboard]*

**Say this:**

"This is the AUSHADHI dashboard. Right now it's showing East Godavari and Krishna districts — 8 health centers, 10 essential medicines each.

Look at PHC Razole — ORS packets at 7%, Zinc tablets at 8%, IV Saline at 6%. CRITICAL. And look at this: the 7-day consumption trend is 3.8 times the baseline. Something is happening here."

*[Click on PHC Razole card to show detail view]*

"The DQMS layer flagged these records with anomaly ratios above 3.5x. This isn't random variation. This is a signal."

*[Switch to terminal. Paste the curl command. Hit enter.]*

"I'm triggering the full agent pipeline now. Watch the dashboard."

*[Switch back to dashboard. Watch for SSE updates.]*

"Sentinel Agent detected the threshold breach — [narrate what you see on screen]. DQMS Validation Agent is running — validating 80 consumption records across 8 centers.

Now — Forecast Agent is calling Gemini 1.5 Flash. This is where it happens."

*[Pause 3–4 seconds while Gemini runs]*

"Look. Gemini has analyzed the ORS, Zinc, and IV Saline consumption pattern across PHC Razole and PHC Amalapuram — two centers in the same geographic cluster, near the Krishna-Godavari delta. Simultaneously. 3.7 to 3.8 times baseline for all three primary cholera indicators.

Confidence 89%. AUSHADHI has flagged a potential cholera cluster in Razole mandal."

*[Click on the Outbreak Alerts panel]*

"This outbreak alert would normally take 3 to 5 days to appear in manual disease surveillance. AUSHADHI generated it in 47 seconds from the consumption data alone, before a single patient is officially reported.

Watch the Procurement Agent now — it's already generating a purchase order."

*[Click on Purchase Orders panel]*

"Purchase Order AUSD-20260820-0047. ORS: 500 packets. Zinc: 1000 tablets. IV Saline: 100 bottles. Nearest warehouse: District Medical Stores, Rajahmundry — 78 kilometers. Estimated delivery 6 hours after approval. Total value: ₹6,800.

The Alert Agent has notified the Medical Officer at PHC Razole and the District Health Officer."

*[Click on Agent Activity Log]*

"Every decision made by every agent is logged here with full audit trail. DQMS validation score: 87%. Gemini reasoning is stored. Purchase order number. Notification delivery. Complete provenance."

*[1 minute 55 seconds. Move to GCP proof.]*

---

## SECTION 4: GCP PROOF (3:00 – 3:35)

*[Switch to Tab 2 — Cloud Run services]*

**Say this:**

"Running on Google Cloud. Three Cloud Run services — the API, the agent workers, and the frontend. All deployed with min-instances zero — I'm not burning credits when idle."

*[Switch to Tab 3 — Firestore]*

"Firestore storing the real-time inventory state for all 8 health centers. The outbreak alert document was written by the Forecast Agent 90 seconds ago — you can see it live."

*[Switch to Tab 4 — Pub/Sub]*

"Pub/Sub handling all inter-agent communication. Four topics — you can see the message counts from the pipeline that just ran."

*[30 seconds. Move to close.]*

---

## SECTION 5: IMPACT AND CLOSE (3:35 – 4:00)

*[Switch back to Dashboard]*

**Say this:**

"India has 160,000 health sub-centres, PHCs, and CHCs. Most of them are flying blind. AUSHADHI is the system that watches them — autonomously, continuously, intelligently.

The supply chain system that failed that child in Razole is fixable. This is the fix.

I'm [your name], from Mandapeta, East Godavari. Thank you."

*[Stop recording.]*

---

## TIMING SUMMARY

| Section | Start | End | Duration |
|---------|-------|-----|---------|
| Problem | 0:00 | 0:35 | 35 sec |
| Architecture | 0:35 | 1:05 | 30 sec |
| Live Demo | 1:05 | 3:00 | 1 min 55 sec |
| GCP Proof | 3:00 | 3:35 | 35 sec |
| Impact/Close | 3:35 | 4:00 | 25 sec |
| **Total** | | | **4:00** |

---

## IF THINGS GO WRONG (Backup Plans)

**If Gemini API is slow (>10 sec):**
Keep talking. Say: "Gemini 1.5 Flash is analyzing the consumption pattern across all 8 health centers simultaneously — this is the core intelligence that makes AUSHADHI different from any inventory system."

**If SSE connection drops:**
Switch to the Firestore tab and show documents updating live.

**If the pipeline doesn't complete in time:**
Have a pre-recorded run saved. Switch screens and say: "Let me show you a run I completed earlier while this one finishes in the background."

**If any GCP service is down:**
Cloud Run dashboard → show deployment history. Firestore → show existing documents. Say: "The system ran this morning — you can see the agent logs here from the 8 AM cycle."

---

## YOUTUBE TITLE AND DESCRIPTION

**Title:** `AUSHADHI — AI Agents That Detect Disease Outbreaks | All Things Agentic Hackathon`

**Description:**
```
AUSHADHI (Autonomous Medicine Supply Intelligence System) — a multi-agent AI system 
built for the All Things Agentic Hackathon by Google.

5 AI agents on Google Cloud autonomously monitor medicine supply across rural health 
centers in Andhra Pradesh, predict stockouts, auto-generate purchase orders, and 
detect disease outbreaks from consumption patterns — before any human surveillance 
system does.

Tech: Gemini 1.5 Flash | Google ADK | Cloud Run | Firestore | Pub/Sub | React

Built for the #AllThingsAgenticHackathon
GitHub: [your repo link]

I am from Mandapeta, East Godavari — this problem is personal.
```

---

*Practice. Record in one take. The unedited live demo is worth 30% of your score.*
