"""Sample internships, so the portal can be shown working before a scrape.

Set DEMO_MODE=1 in .env (or run `python scraper.py` with it set) and these go
into the pool instead of anything being downloaded. The descriptions are
deliberately realistic - including one that asks for a registration fee, which
the matcher must refuse to pass on, and one course-style posting it should
flag rather than hide.
"""
from __future__ import annotations

import cities
import matcher
import scraper
import utils

SAMPLES = [
    ("ai-ml", "Machine Learning Intern", "Vernacular AI", "Bengaluru, Karnataka, India", 0, 25000, 35000,
     "We are looking for an ML intern to work on production NLP pipelines. You will fine-tune "
     "transformer models with PyTorch and Hugging Face, build evaluation sets in Python with pandas "
     "and numpy, and ship inference endpoints with FastAPI and Docker. Exposure to LLMs, RAG and "
     "vector databases such as FAISS is a plus. 6 month internship, stipend 25-35k per month, "
     "pre-placement offer for strong performers. Final year B.Tech/M.Tech students may apply."),
    ("ai-ml", "Generative AI Intern", "Hexaware Technologies", "Noida, Uttar Pradesh, India", 0, 20000, 20000,
     "Join our GenAI practice. Work on LangChain and LangGraph agents, prompt engineering, and "
     "retrieval-augmented generation over enterprise documents. Requirements: strong Python, "
     "understanding of large language models, Git, and willingness to learn. SQL is useful. "
     "Stipend Rs 20,000/month, 6 months, Noida office, 5 days a week."),
    ("ai-ml", "AI Intern (Certificate Program)", "SkillForge Academy", "Remote", 1, None, None,
     "What you'll learn: Python, machine learning basics, deep learning. Mentor guidance throughout. "
     "Internship certificate and letter of recommendation on completion. Duration: 2 months. "
     "Stipend: based on performance. Build 3 projects and get placement assistance."),
    ("ai-ml", "ML Engineer Intern - Apply Now", "Career Boost Services", "Delhi, India", 0, None, None,
     "Guaranteed placement after training. One time registration fee of Rs 2,999 applies. "
     "Learn machine learning with Python and get an internship certificate."),
    ("data-science", "Data Analyst Intern", "Zomato", "Gurugram, Haryana, India", 0, 30000, 30000,
     "You will own reporting for one city team: write SQL against our warehouse, build dashboards "
     "in Power BI, and dig into funnels with Python and pandas. Advanced Excel including pivot "
     "tables is expected. Comfort with statistics and regression helps. Stipend Rs 30,000/month, "
     "6 months, Gurugram, hybrid. Open to 2026 graduates."),
    ("data-science", "Business Intelligence Intern", "Tiger Analytics", "Chennai, Tamil Nadu, India", 0, 18000, 25000,
     "Support the analytics team with data visualisation and ETL work. Tools: SQL, Tableau, Python, "
     "Airflow. You will clean messy data, build data pipelines and present findings. Good "
     "communication skills needed. 3-6 months, stipend 18-25k."),
    ("web-dev", "Full Stack Developer Intern (MERN)", "Scaler", "Bengaluru, Karnataka, India", 0, 40000, 40000,
     "Build features end to end with React.js, Node.js and Express.js against MongoDB. You will "
     "write REST APIs, use TypeScript, style with Tailwind CSS, and ship through Git and Docker. "
     "Stipend Rs 40,000/month for 6 months, full-time offer likely. Strong JavaScript fundamentals "
     "and HTML/CSS required."),
    ("web-dev", "Frontend Developer Intern", "Zoho", "Chennai, Tamil Nadu, India", 0, 15000, 15000,
     "Work on dashboards in React with JavaScript and CSS. Responsive design, REST API integration "
     "and version control with Git. Freshers from any engineering branch welcome. Stipend Rs 15,000 "
     "per month, 6 months, Chennai."),
    ("web-dev", "Web Development Intern", "Brandcrest Media", "Remote", 1, 8000, 8000,
     "WordPress and basic PHP work for client websites. HTML, CSS, some JavaScript. Shopify "
     "experience a bonus. Work from home, 3 months, stipend Rs 8,000/month."),
    ("software-dev", "Software Engineer Intern", "Juspay", "Bengaluru, Karnataka, India", 0, 50000, 60000,
     "Strong data structures and algorithms are the only hard requirement. You will write Python or "
     "Java services, work with SQL databases, REST APIs and Linux, and write unit tests. 6 month "
     "internship, stipend 50-60k per month, Bengaluru. 2026 batch."),
    ("cybersecurity", "Cyber Security Intern (SOC)", "Sophos", "Ahmedabad, Gujarat, India", 0, 20000, 20000,
     "Join the SOC team. You will triage alerts in a SIEM (Splunk), study networking and TCP/IP, "
     "use Wireshark and Nmap, and document incidents. OWASP Top 10 awareness and Linux comfort "
     "expected. CEH or CompTIA Security+ in progress is a plus. Stipend Rs 20,000/month."),
    ("cybersecurity", "Penetration Testing Intern", "Safe Security", "Remote", 1, 25000, 25000,
     "VAPT internship: web application security testing with Burp Suite, vulnerability assessment, "
     "report writing. Python scripting needed. Knowledge of OWASP, CVEs and patch management. "
     "Remote, 6 months, Rs 25,000/month."),
    ("ui-ux", "UI UX Design Intern", "CRED", "Bengaluru, Karnataka, India", 0, 35000, 35000,
     "Own flows end to end: user research, wireframing in Figma, prototyping and handoff. You will "
     "work inside our design system, run usability tests and iterate. Share a portfolio (Behance or "
     "Dribbble) with your application. Stipend Rs 35,000/month, 6 months."),
    ("ui-ux", "Product Design Intern", "Unacademy", "Remote", 1, 15000, 20000,
     "Wireframes, mockups and prototypes in Figma and Adobe XD. Responsive, mobile-first thinking. "
     "Basic understanding of accessibility and HTML/CSS useful. Remote, 3 months, 15-20k."),
    ("digital-marketing", "Digital Marketing Intern", "Nykaa", "Mumbai, Maharashtra, India", 0, 15000, 15000,
     "SEO (on-page and off-page), keyword research with Semrush, Google Analytics GA4 reporting, and "
     "social media calendars for Instagram. Some Google Ads and Meta ads exposure. Canva for "
     "creatives. Stipend Rs 15,000/month, Mumbai, 6 months."),
    ("digital-marketing", "SEO Intern", "WebFX India", "Remote", 1, 10000, 12000,
     "Keyword research, backlink outreach, content marketing support, WordPress publishing and "
     "email marketing with Mailchimp. Good written English required. Work from home."),
    ("finance", "Finance Intern", "Zerodha", "Bengaluru, Karnataka, India", 0, 25000, 25000,
     "Support the FP&A team: advanced Excel modelling, reconciliation, journal entries and monthly "
     "reporting. Exposure to GST and TDS filings. Equity research reading encouraged. PowerPoint for "
     "management decks. Stipend Rs 25,000/month, 6 months, Bengaluru."),
    ("hr", "HR Intern - Talent Acquisition", "Darwinbox", "Hyderabad, Telangana, India", 0, 12000, 15000,
     "End-to-end recruitment support: sourcing on LinkedIn and Naukri, resume screening, interview "
     "scheduling, and onboarding documentation. Excel trackers and MIS. Strong communication skills "
     "and interpersonal ability. 3-6 months, stipend 12-15k, Hyderabad."),
    ("electronics-vlsi", "VLSI Design Intern", "Qualcomm", "Hyderabad, Telangana, India", 0, 45000, 45000,
     "RTL design and verification in Verilog and SystemVerilog. Use Cadence and Synopsys tools, run "
     "simulations, debug waveforms. Knowledge of digital electronics and some Python scripting. "
     "Stipend Rs 45,000/month, 6 months, Hyderabad."),
    ("mechanical", "Design Engineer Intern (CAD)", "Tata Motors", "Pune, Maharashtra, India", 0, 20000, 20000,
     "Component design in CATIA and SolidWorks, 2D drawings in AutoCAD with GD&T, and FEA checks in "
     "ANSYS. Exposure to manufacturing processes, sheet metal and BOM costing. Stipend Rs 20,000 "
     "per month, 6 months, Pune plant."),
    ("product-management", "Associate Product Manager Intern", "Razorpay", "Bengaluru, Karnataka, India", 0, 50000, 50000,
     "Write PRDs, groom the backlog in Jira, run customer interviews, and read product analytics in "
     "Mixpanel. You will define KPIs, run A/B tests and support go-to-market with cross-functional "
     "stakeholders. SQL and Excel needed. Stipend Rs 50,000/month, 6 months."),
    ("content-writing", "Content Writing Intern", "Groww", "Remote", 1, 15000, 15000,
     "Write blogs and long-form articles on personal finance. SEO writing with keyword and search "
     "intent research, editing and proofreading, WordPress publishing. Strong writing skills and "
     "fact-checking discipline. Remote, 3 months, Rs 15,000/month."),
    ("law", "Legal Intern - Contracts", "Flipkart", "Bengaluru, Karnataka, India", 0, 20000, 20000,
     "Assist the commercial legal team with contract drafting and review (NDAs, vendor agreements), "
     "legal research on SCC Online and Manupatra, and compliance tracking under the Companies Act. "
     "Exposure to data privacy and the DPDP Act. Stipend Rs 20,000/month, 2-3 months."),
    ("business-analyst", "Business Analyst Intern", "Deloitte India", "Gurugram, Haryana, India", 0, 25000, 30000,
     "Support consulting engagements: market research, competitor analysis, requirement gathering "
     "(BRD and user stories), advanced Excel and PowerPoint decks. Power BI dashboards and SQL "
     "queries. Agile and Jira exposure. Stipend 25-30k, Gurugram, 6 months."),
]


def seed() -> int:
    """Put the samples in the pool. Safe to run twice - the key is derived from
    company + title, so a second run updates instead of duplicating."""
    rows = []
    today = utils.utcnow().date().isoformat()
    for field, title, company, location, remote, lo, hi, description in SAMPLES:
        _, city_label = cities.identify(location, bool(remote))
        rows.append({
            "key": utils.posting_key(company, title), "title": title, "company": company,
            "location": location, "city_label": city_label, "is_remote": int(bool(remote)),
            "is_intern": 1, "stipend_min": lo, "stipend_max": hi, "pay_interval": "monthly",
            "pay_label": matcher.pay_label(lo, hi, "monthly"), "source": "sample",
            "link": f"https://example.com/internship/{utils.posting_key(company, title)}",
            "posted": today, "description": description,
            "found_for": ",".join(sorted({field} | scraper.fields_matching_title(title))),
        })
    # The scam posting must never reach the pool, exactly as in a real scrape.
    rows = [r for r in rows if not matcher.red_flags(r["description"])]
    scraper.save_postings(rows)
    return len(rows)


if __name__ == "__main__":
    import db
    db.migrate()
    print(f"seeded {seed()} sample internships")
