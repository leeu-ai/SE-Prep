---
name: se-demo-site
description: "Create a personalised Wix Studio demo site for a prospect, using parameters from an existing SE brief. Usage: 'Create demo site for [Company Name]'"
---

You are creating a personalised Wix Enterprise demo site for a prospect. Use the SE brief parameters to make it feel purpose-built for this specific client.

## STEP 1 — Load Brief Parameters

Find the site_request.json in `~/Documents/SE Tools/gong_intel/Briefs/`. Look for a file matching the company name (slug format: lowercase, hyphens). For example, "Acme Corp" → `acme_corp_site_request.json`.

Read the following fields:
- `company_name`, `domain`, `industry`, `company_summary`
- `why_wix`, `pain_points`, `tech_stack`
- `recommended_focus`, `selected_verticals`, `attendees`

If no JSON file is found, ask the user for: company name, domain, and industry.

---

## STEP 2 — Check for Existing Site

**ListWixSites** — search by company name. If a site already exists → return the URL and stop. Do not create a duplicate.

---

## STEP 3 — Choose Template

**CreateWixBusinessGuide** — find the most appropriate Wix Studio template for the company's specific industry and use case.

Be precise:
- Mortgage brokerage network → financial/real estate template
- Auto dealer franchise → automotive/dealership template
- Florist franchise → retail/floral template
- SaaS company → tech/software template

Not just "generic business."

---

## STEP 4 — Create Site

**ManageWixSite** — create the site from the chosen template.
Name it: `[Company Name] Demo — Wix Enterprise`

---

## STEP 5 — Deep Personalisation (REQUIRED — do not skip)

**CallWixSiteAPI** — personalise the site thoroughly. This is the most important step.

### CMS Collections
Create and populate collections with realistic, company-specific content. Use the company's actual geography, brand names, product lines, and pricing from the brief's web research.

Examples by industry:
- **Mortgage/Lending:** loan products, branch locations, broker profiles, calculators, application forms
- **Real estate franchise:** property listings (real local addresses/prices), agent profiles, neighborhoods, open house events
- **Auto dealer network:** vehicle inventory (real makes/models/prices), dealership locations, service packages, financing options
- **Florist franchise:** arrangement catalog (seasonal, occasion-based), location finder, event booking, care guides

**Minimum requirements:**
- [ ] At least 5–8 CMS items per collection (not 1–2 placeholder entries)
- [ ] Content uses the company's real brand names, geography, and product lines
- [ ] Pain points from the brief are addressed visibly in the site structure
- [ ] Forms configured for their actual use case (lead capture, application, booking, etc.)

### Apps to install (based on selected_verticals)
- eCom → `1380b703-ce81-ff05-f115-39571d94dfcd`
- Events → `140603ad-af8d-84a5-2c80-a0f60cb47351`
- Bookings/Services → `13d21c63-b5ec-5912-8397-c3a5ddb27a97`
- Blog → `14bcded7-0066-7c35-14d7-466cb3f09103`
- Forms → `14ce1214-b278-a7e4-1373-00cebd1bef7c`
- Chat → `14517e1a-3ff0-af98-408e-2bd6953c36a2`

---

## STEP 6 — Publish

Publish the site and return the live URL.

---

## NOTES

- NEVER use browser automation — always use Wix MCP tools only
- If brief JSON is missing, proceed with whatever company info the user provides
- The goal is a demo that feels bespoke, not a template with a logo swap
