# Manthan HRMS Pilot — Progress Log

Status as of **2026-09-15**: Day 1, Day 2 and Day 3 (Sprints 1–6) done and verified for **Prudeno Wealth**.
Next: **Day 4** (Sprint 7 branding + walkthrough, Sprint 8 package + start NS Wealth).

- Requirement doc: `~/piyush/work/spring-money/DOING/HRMS/manthan-hrms-pilot-plan.html` (5 days / 10 sprints)
- Bench: `~/piyush/work/spring-money/frappe-bench` — frappe 15.120.0, erpnext 15.121.0, hrms 15.64.0, Python 3.11
- Site: **`prudeno-prod.localhost`** (existing shared site, not a new one — it also hosts other Manthan apps and **real users**)
- Company: **Prudeno Wealth** (abbr `PW`, fake domain `prudenowealth.example`)
- Apps: `hrms`, `india_payroll` (our v15 backport), `manthan_hrms` (this app)

---

## 1. Quick resume

```bash
cd ~/piyush/work/spring-money/frappe-bench
S=prudeno-prod.localhost

# Health check: everything built so far (expect 19/19, 37/37, 21/21)
bench --site $S execute manthan_hrms.setup.day1.verify_day1
bench --site $S execute manthan_hrms.setup.day2.verify_day2
bench --site $S execute manthan_hrms.setup.day3.verify_day3
```

All `run_sprintN` functions are **idempotent** (safe to re-run; verified no duplicates):

| Day | Setup | Verify |
|---|---|---|
| 1 | `manthan_hrms.setup.day1.run_sprint1`, `run_sprint2` | `day1.verify_day1` (19 checks) |
| 2 | `manthan_hrms.setup.day2.run_sprint3`, `run_sprint4` | `day2.verify_day2` (37 checks) |
| 3 | `manthan_hrms.setup.day3.run_sprint5`, `run_sprint6` | `day3.verify_day3` (21 checks + payslip table) |

After changing hooks (`override_doctype_class`, `doc_events`): `bench --site $S clear-cache` and restart `bench start`.

### Logins (local pilot only — fake data)

| User | Password | Role / purpose |
|---|---|---|
| `hr.test@prudenowealth.example` | not set | HR Manager + HR User + Leave/Expense Approver + Manthan Compliance Reviewer (Role Profile "Manthan HR Reviewer"); leave/expense approver for all departments |
| `test.employee@prudenowealth.example` | shared pilot password | HR-EMP-00001, raised expense claim |
| `priya.nair@prudenowealth.example` | shared pilot password | HR-EMP-00003, Casual Leave, Fit & Proper Declaration, cert reminder |
| `kavya.iyer@prudenowealth.example` | shared pilot password | HR-EMP-00006, Sick Leave; also sees Siddharth (reports to her) |
| `ishita.banerjee@prudenowealth.example` | shared pilot password | HR-EMP-00015, onboarded joiner |

Passwords are not stored in this repo. Set or reset with `bench --site $S set-password <user> <password>`.
All employee users: Employee role only, Module Profile "Manthan HR Only", default workspace Leaves.
**Change the shared password before the site is reachable by anyone else.**

---

## 2. Decisions taken (differ from / extend the requirement doc)

1. **Existing site** `prudeno-prod.localhost` instead of a brand-new site (doc decision #4).
2. **Company-scoped**: all sample data carries `company = Prudeno Wealth`; lookups filter by it.
3. **india_payroll v15 backport**: upstream has no v15 line → forked, branch `version-15-backport`, changes in `apps/india_payroll/BACKPORT_V15.md`.
4. **PF / Professional Tax** come from india_payroll's real logic (ported hook), not formula components.
5. **Advisory features are code in `manthan_hrms`** (DocType + custom fields), so Sprint 8 can reuse them. Schema is site-wide.
6. **Payroll month** September 2026 (covers all 15, incl. Ishita who joined 1 Sep).
7. **Payroll Settings** (site-wide single): EPF + PT enabled with india_payroll **multi-company mode**, one row = Prudeno Wealth → no other company gets statutory deductions. ESI/LWF off.
8. **Reviewer role**: real people hold HR Manager / HR User / Compliance Officer on this site, so Fit & Proper approvals use a new role **Manthan Compliance Reviewer** held only by hr.test.

---

## 3. What was built, by sprint

### Day 1 — Foundations (`setup/day1.py`)
**Sprint 1**
- Company Prudeno Wealth (India, INR, standard CoA).
- Module Profile **Manthan HR Only**: blocks every module not from `hrms` / `india_payroll` / `manthan_hrms` (rebuilt each run).
- Test HR user `hr.test@…`.

**Sprint 2**
- Departments Advisory, Compliance, Operations, Admin, Research (the 13 generic auto-created ones disabled); hr.test = leave + expense approver on each.
- Designations: Relationship Manager, Compliance Officer, Operations Executive, Admin Executive, Research Analyst.
- Holiday List "Prudeno Wealth 2026" (Sat/Sun + 11 holidays), set as company default.
- Leave Types Casual 12, Sick 12, Earned 15 (carry forward); Leave Policy "Prudeno Wealth Standard Leave Policy" assigned to all active employees via Leave Control Panel.
- Test Employee HR-EMP-00001 with login.

Fixtures (`hooks.py`): Module Profile, 3 Leave Types, 5 Designations.

### Day 2 — People, attendance, leave (`setup/day2.py`)
**Sprint 3**
- 13 sample employees (`SAMPLE_EMPLOYEES`) + Test Employee + onboarded joiner = **15 active**. Every department/designation covered; `reports_to` chains (Aarav → Priya/Rohan/Sneha, Kavya → Siddharth, Ananya → Vikram/Rahul, Meera → Arjun, Neha → Karan/Ishita).
- Full onboarding: Employee Onboarding Template "Prudeno Wealth Standard Onboarding" (5 activities) → Job Applicant → Job Offer (Accepted) → Employee Onboarding HR-EMP-ONB-2026-00001 → tasks completed → Employee **HR-EMP-00015 Ishita Banerjee** (DOJ 2026-09-01).
- Logins for Ishita, Priya, Kavya (`create_employee_logins`).

**Sprint 4**
- Leave: Priya Casual Leave 2026-09-09 (balance 12→11); Kavya Sick Leave 2026-09-10..11 (12→10). Created before attendance.
- Attendance Mon 2026-09-07 → Fri 2026-09-11 for all 15 (75 records; some WFH; leave days = On Leave).
- Expense Claim Types mapped to PW accounts; company `default_expense_claim_payable_account` = Creditors - PW.
- Expense claim **HR-EXP-2026-00001** (Test Employee, ₹3,100) approved, submitted, paid via Journal Entry against Cash - PW → status Paid.

### Day 3 — Payroll + 3 advisory features (`setup/day3.py`)
**Sprint 5**
- Payroll Settings: EPF + PT on, multi-company with Prudeno Wealth row.
- Payroll Period "Prudeno Wealth FY 2026-27" (2026-04-01 → 2027-03-31).
- Income Tax Slab "Prudeno Wealth New Regime 2026-27" (copy of 2025-26 new regime: std exemption 75,000, relief limit 12L, cess 4%), submitted.
- Liability accounts PF Payable / Professional Tax Payable / TDS Payable - PW; component accounts; Income Tax component `variable_based_on_taxable_salary = 1` (global).
- Salary Structure **"Prudeno Wealth Standard"**: Basic = base×0.6, HRA = base×0.4, Provident Fund, Professional Tax, Income Tax.
- SSAs for all 15 (`MONTHLY_GROSS`, ₹35k–₹2.5L), employment_state Maharashtra, epf_applicable 1.

**Sprint 6**
- Payroll Entry Sep 2026 → 15 submitted slips, each with PF + PT; accrual Journal Entry posted. Emails muted during run.
- Hand-checked (all match):

  | Employee | Gross | PF | PT | Income Tax | Net |
  |---|---|---|---|---|---|
  | Aarav | 2,50,000 | 1,800 | 200 | 20,057.14 | 2,27,942.86 |
  | Priya | 90,000 | 1,800 | 200 | 0 | 88,000 |
  | Ishita | 45,000 | 1,800 | 200 | 0 | 43,000 |

  hrms projects tax over the 7 remaining FY months (no Apr–Aug slips).
- **Feature 1 — Certification tracker**: Employee fields `nism_certification`, `nism_certificate_no`, `nism_valid_upto`, `arn_number`, `euin_number`, `arn_valid_upto` (section after `reports_to`). Data on Aarav, Priya, Rohan, Kavya, Siddharth. Notifications "NISM Certificate Expiring" + "ARN/EUIN Renewal Due" (Days Before 30, System Notification → hr.test). Test reminder for Priya delivered (Notification Log).
- **Feature 2 — Fit & Proper Declaration**: DocType `Fit and Proper Declaration` (module Manthan HRMS, submittable, one per employee + FY, unticked item needs disclosures, reviewer stamped on submit). Workflow **"Fit and Proper Review"**: Draft →(Employee: Submit for Review)→ Pending Review →(Manthan Compliance Reviewer: Approve / Reject)→ Approved / Rejected. Test: **FPD-2026-00001** by Priya, approved by hr.test.
- **Feature 3 — Exit checklist**: Employee Separation fields `client_book_handed_over`, `handover_to`, `clients_handed_over`, `handover_date`, `non_solicitation_signed(_on)`, `system_access_revoked(_on)`; `before_submit` blocks until all 3 ticked + handover_to set. Test: **HR-EMP-SEP-2026-00001** for Rohan — incomplete submit blocked (logged as Comment), then submitted (42 clients → Priya). Rohan stays Active.

---

## 4. Code map

### `apps/manthan_hrms` (branch `develop`, **uncommitted** beyond scaffold)
| Path | Purpose |
|---|---|
| `manthan_hrms/hooks.py` | fixtures, `after_install` / `after_migrate`, `doc_events` (Employee Separation `before_submit`) |
| `manthan_hrms/setup/install.py` | creates custom fields on install/migrate |
| `manthan_hrms/setup/custom_fields.py` | Employee certification + Employee Separation exit fields |
| `manthan_hrms/setup/day1.py` / `day2.py` / `day3.py` | sprint setup + verification |
| `manthan_hrms/compliance/employee_separation.py` | exit checklist validation |
| `manthan_hrms/manthan_hrms/doctype/fit_and_proper_declaration/` | DocType json + controller |
| `manthan_hrms/fixtures/` | module_profile, leave_type, designation |

### `apps/india_payroll` (branch `version-15-backport`, **uncommitted**)
| Path | Purpose |
|---|---|
| `BACKPORT_V15.md` | all v15 changes + known gaps |
| `india_payroll/compat.py` | tax helpers missing from hrms v15 |
| `india_payroll/overrides/salary_slip.py` | `IndiaPayrollSalarySlip`: v15 `calculate_net_pay` + `apply_regional_deductions` |
| `india_payroll/hooks.py` | `override_doctype_class` for Salary Slip |
| `india_payroll/india_payroll/salary_slip.py` | skips employer contributions (no v15 table) |

**Not ported** (documented): `apply_regional_ctc_components` (no Employer Contribution type in v15), surcharge hook (>₹50L only). hrms v15 applies no India marginal relief above the ₹12L rebate limit.

---

## 5. Gotchas learned (read before Day 4)

- **Shared site with real users**: never trigger site-wide actions (e.g. `trigger_daily_alerts`, role-wide workflow actions, emails). Send targeted notifications only.
- **Role Profile rewrites roles on every User save** → `add_roles` alone is lost. Use a Role Profile (hr.test is on "Manthan HR Reviewer"). Day 1 no longer resets an existing profile.
- **Module Profile save** queues `update_all_users` behind a doc lock; day1 applies it inline and unlocks (no background worker needed).
- **Onboarding**: `boarding_begins_on` must be ≥ `date_of_joining`; reload doc after submit before `mark_onboarding_as_completed`; onboarding department/designation are `fetch_from` template (generic template blanks them).
- **Leave vs attendance**: create leave applications before marking Present attendance.
- **Expense claim** rows need their own `cost_center`.
- **Employee user permission** covers the reports_to subtree (managers see reports).
- **Payroll**: no India marginal relief in hrms v15 → keep sample gross out of the ₹12L–₹12.75L projected band. Mute emails during slip submission.
- `bench execute` prints a misleading `NameError: name 'manthan_hrms' is not defined` whenever the called function raises — read the first traceback.
- Bench build/module quirks: see memory note on UAT-pinned versions (SM-SYNC / BSE module clash).

---

## 6. Day 4 — what's next (from requirement doc)

### Sprint 7 — Branding + full walkthrough
DoD:
- [ ] Logo and favicon visible on login and inside the system
- [ ] Primary colour changed from default
- [ ] Full walkthrough completed, all errors fixed

Notes / open questions:
- Branding on this **shared** site affects every app/user on it (Website Settings / Navbar Settings are global). Decide: apply here anyway, or only on the NS Wealth site / a theme scoped per site.
- Walkthrough checklist: HR user desk (sidebar limited), employee self-service (leave apply, expense claim, payslip view, F&P declaration), onboarding, attendance, leave approval, expense payment, payroll entry, cert reminder bell, exit checklist block.

### Sprint 8 — Package the setup, start NS Wealth
DoD:
- [ ] Prudeno Wealth configuration exported into a reusable package
- [ ] NS Wealth site created, all software installed, no errors
- [ ] Non-HR menus hidden on NS Wealth
- [ ] One Company record created for NS Wealth

Notes / open questions:
- Commit both app repos first (nothing committed yet).
- Package = `manthan_hrms` app itself: day1–day3 setup modules are already company-parameterised via `COMPANY_*` constants → refactor constants into a per-client config (e.g. `setup/clients.py` or site_config) instead of editing code per client.
- Candidates for new fixtures: Notifications (certification), Workflow "Fit and Proper Review" + Workflow States/Actions, Role "Manthan Compliance Reviewer", Role Profile "Manthan HR Reviewer", Employee Onboarding Template (company-specific — keep in setup code).
- Payroll Settings multi-company row must be added for NS Wealth (or single-company on its own site).
- New site: `bench new-site <ns-wealth site> --install-app erpnext hrms india_payroll manthan_hrms` (check memory note on bench build/module clash first).
