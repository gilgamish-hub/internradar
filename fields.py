"""The field catalogue: what "related to my field" actually means.

Every field is one entry. To support a new discipline, add an entry here and
nothing else needs to change - the signup form, the scraper queries and the
matcher all read this table.

  label    what the student sees in the dropdown
  queries  the search terms sent to the job boards (kept to 3-4: each one is a
           separate network round trip per board, per scan)
  titles   regex for "this job title really is in my field" (strongest signal)
  near     regex for adjacent titles - counted, but worth fewer points
  skills   keyword -> regex, matched against the job description. Each hit adds
           points and is shown to the student as "why this matched".
"""
from __future__ import annotations

# Skills worth points in every field - they are what an internship actually
# asks a first-job candidate for.
COMMON_SKILLS = {
    "communication": r"communication skills?|verbal|written english",
    "ms excel": r"\bexcel\b|spreadsheet|google sheets",
    "teamwork": r"team ?player|collaborat",
    "git": r"\bgit\b|github|version control",
}

FIELDS: dict[str, dict] = {
    "ai-ml": {
        "label": "AI / Machine Learning",
        "queries": ["machine learning intern", "AI intern", "generative AI intern", "deep learning intern"],
        "titles": r"machine learning|\bml\b|\bai\b|artificial intelligence|gen ?ai|generative|\bllm|deep learning|applied scien",
        "near": r"data scien|\bnlp\b|computer vision|python",
        "skills": {
            "python": r"\bpython\b", "pytorch": r"\bpytorch\b", "tensorflow": r"\btensorflow\b",
            "scikit-learn": r"scikit|sklearn", "transformers": r"hugging ?face|\btransformers?\b",
            "llm": r"\bllms?\b|large language model", "rag": r"\brag\b|retrieval[- ]augmented",
            "langchain": r"langchain|langgraph", "nlp": r"\bnlp\b|natural language",
            "computer vision": r"computer vision|\bopencv\b|\byolo", "pandas": r"\bpandas\b|\bnumpy\b",
            "fine-tuning": r"fine[- ]?tun", "prompt engineering": r"prompt engineering|prompting",
            "vector db": r"chroma|pinecone|faiss|vector (db|database|store)",
            "fastapi": r"fastapi|flask", "docker": r"\bdocker\b", "sql": r"\bsql\b",
        },
    },
    "data-science": {
        "label": "Data Science / Data Analytics",
        "queries": ["data science intern", "data analyst intern", "business intelligence intern", "data engineer intern"],
        "titles": r"data scien|data analyst|data analytics|business intelligence|\bbi\b|data engineer|statistic",
        "near": r"machine learning|\bai\b|reporting|\bmis\b",
        "skills": {
            "python": r"\bpython\b", "sql": r"\bsql\b|mysql|postgre", "excel": r"\bexcel\b|vlookup|pivot",
            "power bi": r"power ?bi", "tableau": r"tableau", "pandas": r"\bpandas\b|\bnumpy\b",
            "statistics": r"statistic|hypothesis test|regression|probability",
            "visualisation": r"visuali[sz]ation|matplotlib|seaborn|dashboards?",
            "machine learning": r"machine learning|\bml\b", "r": r"\br programming\b|\brstudio\b",
            "etl": r"\betl\b|data pipeline|airflow", "advanced excel": r"advanced excel|macros|\bvba\b",
        },
    },
    "web-dev": {
        "label": "Web Development (Frontend / Backend / Full Stack)",
        "queries": ["web development intern", "full stack developer intern", "frontend developer intern", "backend developer intern"],
        "titles": r"web develop|full ?stack|front ?end|back ?end|\bmern\b|\bmean\b|react|node|php|wordpress|django",
        "near": r"software (develop|engineer)|\bsde\b|ui develop|javascript",
        "skills": {
            "html/css": r"\bhtml\b|\bcss\b|tailwind|bootstrap", "javascript": r"javascript|\bjs\b|es6",
            "react": r"\breact\b|react\.?js|next\.?js", "node": r"node\.?js|express\.?js",
            "typescript": r"typescript", "python": r"\bpython\b", "django": r"django|flask|fastapi",
            "php": r"\bphp\b|laravel", "java": r"\bjava\b|spring boot", "sql": r"\bsql\b|mysql|postgre",
            "mongodb": r"mongo ?db|nosql", "rest api": r"rest(ful)? api|\bapi\b",
            "docker": r"\bdocker\b", "aws": r"\baws\b|cloud deploy",
            "wordpress": r"wordpress|shopify|webflow",
        },
    },
    "mobile-dev": {
        "label": "Mobile App Development (Android / iOS / Flutter)",
        "queries": ["android developer intern", "flutter developer intern", "mobile app development intern", "ios developer intern"],
        "titles": r"android|\bios\b|mobile app|flutter|react native|kotlin|swift|app develop",
        "near": r"software (develop|engineer)|full ?stack|\bsde\b",
        "skills": {
            "flutter": r"flutter|\bdart\b", "android": r"\bandroid\b|android studio",
            "kotlin": r"\bkotlin\b", "java": r"\bjava\b", "swift": r"\bswift\b|swiftui|xcode",
            "react native": r"react native", "firebase": r"firebase", "rest api": r"rest(ful)? api|\bapi\b",
            "sqlite": r"sqlite|room db|realm", "ui": r"\bui\b|material design|responsive",
            "play store": r"play ?store|app ?store|publish",
            "state management": r"\bredux\b|\bbloc\b|provider|riverpod",
        },
    },
    "software-dev": {
        "label": "Software Development / SDE",
        "queries": ["software developer intern", "software engineer intern", "SDE intern", "python developer intern"],
        "titles": r"software (develop|engineer)|\bsde\b|programmer|developer intern|application develop",
        "near": r"web develop|full ?stack|back ?end|\bqa\b|testing",
        "skills": {
            "dsa": r"data structures?|algorithms?|\bdsa\b|problem solving",
            "python": r"\bpython\b", "java": r"\bjava\b", "c++": r"c\+\+|\bcpp\b", "c#": r"c#|\.net\b",
            "sql": r"\bsql\b|database", "oop": r"\boop\b|object[- ]oriented",
            "rest api": r"rest(ful)? api|microservice",
            "linux": r"\blinux\b|\bunix\b|shell script", "testing": r"unit test|pytest|\bjunit\b|debugging",
            "docker": r"\bdocker\b|kubernetes", "cloud": r"\baws\b|\bazure\b|\bgcp\b",
        },
    },
    "cybersecurity": {
        "label": "Cybersecurity / Ethical Hacking",
        "queries": ["cyber security intern", "information security intern", "penetration testing intern", "SOC analyst intern"],
        "titles": r"cyber ?security|information security|infosec|penetration test|\bpentest|ethical hack|\bsoc\b|\bvapt\b|security analyst",
        "near": r"network|\bit\b support|risk|compliance|\bgrc\b",
        "skills": {
            "networking": r"networking|\btcp/?ip\b|\bosi\b|firewall|\bvpn\b",
            "linux": r"\blinux\b|kali|\bunix\b", "python": r"\bpython\b|scripting",
            "owasp": r"\bowasp\b|top ?10|web app security", "burp suite": r"burp ?suite|\bzap\b",
            "nmap": r"\bnmap\b|wireshark|metasploit|nessus", "siem": r"\bsiem\b|splunk|qradar|wazuh",
            "vulnerability assessment": r"vulnerabilit|\bcve\b|patch", "cloud security": r"cloud security|\biam\b",
            "iso 27001": r"iso ?27001|\bnist\b|\bgdpr\b|compliance",
            "ceh": r"\bceh\b|comptia|security\+|\boscp\b",
        },
    },
    "devops-cloud": {
        "label": "DevOps / Cloud Engineering",
        "queries": ["devops intern", "cloud engineer intern", "site reliability intern", "AWS intern"],
        "titles": r"devops|cloud engineer|\bsre\b|site reliability|platform engineer|infrastructure|cloud intern",
        "near": r"system admin|\bit\b infra|backend|linux",
        "skills": {
            "linux": r"\blinux\b|\bunix\b|shell script|\bbash\b", "docker": r"\bdocker\b|container",
            "kubernetes": r"kubernetes|\bk8s\b|helm", "aws": r"\baws\b|\bec2\b|\bs3\b",
            "azure": r"\bazure\b", "gcp": r"\bgcp\b|google cloud",
            "ci/cd": r"\bci/?cd\b|jenkins|github actions|gitlab ci",
            "terraform": r"terraform|\biac\b|cloudformation|ansible",
            "monitoring": r"prometheus|grafana|monitoring|logging|\belk\b",
            "python": r"\bpython\b",
        },
    },
    "ui-ux": {
        "label": "UI / UX Design",
        "queries": ["UI UX design intern", "product design intern", "user experience intern", "figma design intern"],
        "titles": r"\bui\b|\bux\b|user experience|user interface|product design|interaction design|visual design",
        "near": r"graphic design|web design|design intern",
        "skills": {
            "figma": r"\bfigma\b", "adobe xd": r"adobe xd|\bxd\b", "sketch": r"\bsketch\b",
            "wireframing": r"wireframe|lo-?fi|hi-?fi|mockup", "prototyping": r"prototyp",
            "user research": r"user research|usability test|\bpersona|user journey",
            "design system": r"design system|style guide|component library",
            "photoshop": r"photoshop|illustrator", "responsive design": r"responsive|mobile[- ]first",
            "portfolio": r"portfolio|behance|dribbble",
            "html/css": r"\bhtml\b|\bcss\b", "accessibility": r"accessib|\bwcag\b",
        },
    },
    "graphic-design": {
        "label": "Graphic Design / Video Editing",
        "queries": ["graphic design intern", "video editing intern", "motion graphics intern", "creative design intern"],
        "titles": r"graphic design|visual design|video edit|motion graphic|creative design|animat|illustrat|multimedia",
        "near": r"\bui\b|\bux\b|social media|content|brand",
        "skills": {
            "photoshop": r"photoshop", "illustrator": r"illustrator|vector",
            "premiere pro": r"premiere ?pro|final cut", "after effects": r"after ?effects|motion graphic",
            "canva": r"\bcanva\b", "figma": r"\bfigma\b", "coreldraw": r"corel ?draw",
            "branding": r"brand(ing)?|logo|identity", "typography": r"typograph|layout",
            "social media creatives": r"social media (creative|post|design)|reels?|thumbnail",
            "3d": r"blender|\b3d\b|maya|cinema ?4d", "portfolio": r"portfolio|behance|dribbble",
        },
    },
    "digital-marketing": {
        "label": "Digital Marketing / SEO / Social Media",
        "queries": ["digital marketing intern", "social media marketing intern", "SEO intern", "marketing intern"],
        "titles": r"digital marketing|marketing intern|\bseo\b|\bsem\b|social media|performance marketing|growth|brand|influencer",
        "near": r"content|business development|sales|public relation",
        "skills": {
            "seo": r"\bseo\b|search engine optimi|on[- ]page|off[- ]page|backlink",
            "google ads": r"google ads|\bppc\b|\bsem\b|adwords",
            "meta ads": r"meta ads|facebook ads|instagram ads",
            "google analytics": r"google analytics|\bga4\b|analytics",
            "social media": r"social media|instagram|linkedin|twitter",
            "content marketing": r"content (marketing|calendar|strategy)|copywriting|blog",
            "email marketing": r"email marketing|mailchimp|newsletter|drip",
            "canva": r"\bcanva\b|creatives?", "wordpress": r"wordpress|\bcms\b",
            "keyword research": r"keyword research|semrush|ahrefs|ubersuggest",
        },
    },
    "content-writing": {
        "label": "Content Writing / Copywriting",
        "queries": ["content writing intern", "content writer intern", "copywriting intern", "technical writer intern"],
        "titles": r"content writ|content intern|copywrit|technical writ|editor|blogger|script ?writ|journalis",
        "near": r"digital marketing|\bseo\b|social media|communication",
        "skills": {
            "writing": r"writing skills?|articles?|blogs?|long[- ]form",
            "seo writing": r"\bseo\b|keyword|search intent",
            "editing": r"editing|proofread|grammar", "research": r"research|fact[- ]check",
            "copywriting": r"copywrit|ad copy|landing page|\bcta\b",
            "social media": r"social media|caption|reels? script",
            "wordpress": r"wordpress|\bcms\b|publish",
            "technical writing": r"technical writ|documentation|\bapi\b docs",
            "script writing": r"script|video script|storyboard",
            "ai tools": r"chatgpt|\bai\b tools?|generative",
        },
    },
    "business-analyst": {
        "label": "Business Analyst / Consulting",
        "queries": ["business analyst intern", "business development intern", "consulting intern", "research analyst intern"],
        "titles": r"business analyst|business development|\bbd\b intern|consult|research analyst|strategy|market research|operations analyst",
        "near": r"data analyst|product|sales|finance",
        "skills": {
            "excel": r"\bexcel\b|vlookup|pivot|advanced excel",
            "sql": r"\bsql\b", "powerpoint": r"power ?point|\bppt\b|deck",
            "market research": r"market research|competitor|industry (research|analysis)",
            "requirement gathering": r"requirement|\bbrd\b|\bfrs\b|user stor",
            "power bi": r"power ?bi|tableau|dashboard",
            "business modelling": r"financial model|business model|forecast|unit economics",
            "stakeholder management": r"stakeholder|client (interaction|facing)",
            "process mapping": r"process (map|improvement)|\bsop\b|workflow",
            "jira": r"\bjira\b|confluence|agile|scrum",
        },
    },
    "product-management": {
        "label": "Product Management",
        "queries": ["product management intern", "associate product manager intern", "product intern", "program management intern"],
        "titles": r"product manage|product intern|\bapm\b|product owner|program manage|product analyst|growth product",
        "near": r"business analyst|project manage|\bui\b|\bux\b|strategy",
        "skills": {
            "roadmap": r"roadmap|\bprd\b|product requirement|backlog",
            "user research": r"user research|customer interview|\bpersona",
            "agile": r"agile|scrum|sprint|\bjira\b",
            "product analytics": r"analytics|mixpanel|amplitude|metrics|\bkpi\b|funnel",
            "wireframing": r"wireframe|figma|mockup|prototyp",
            "sql": r"\bsql\b", "excel": r"\bexcel\b|spreadsheet",
            "a/b testing": r"a/?b test|experiment",
            "go-to-market": r"go[- ]to[- ]market|\bgtm\b|launch",
            "stakeholder management": r"stakeholder|cross[- ]functional",
        },
    },
    "finance": {
        "label": "Finance / Accounting",
        "queries": ["finance intern", "accounts intern", "financial analyst intern", "investment banking intern"],
        "titles": r"financ|account|\bca\b intern|audit|taxation|investment|equity research|\bfp&a\b|treasury|credit analyst",
        "near": r"business analyst|data analyst|operations|\bmis\b",
        "skills": {
            "excel": r"\bexcel\b|vlookup|pivot|advanced excel",
            "accounting": r"accounting|book ?keeping|journal entr|ledger|\bgaap\b|ind ?as",
            "tally": r"\btally\b|zoho books|quickbooks|\berp\b|\bsap\b",
            "taxation": r"\bgst\b|\btds\b|income tax|taxation|return filing",
            "financial modelling": r"financial model|\bdcf\b|valuation|forecast",
            "audit": r"audit|internal control|reconcil",
            "equity research": r"equity research|\bipo\b|capital market|portfolio",
            "powerpoint": r"power ?point|\bppt\b", "sql": r"\bsql\b|power ?bi",
        },
    },
    "hr": {
        "label": "Human Resources / Recruitment",
        "queries": ["HR intern", "human resources intern", "talent acquisition intern", "recruitment intern"],
        "titles": r"\bhr\b|human resource|talent acquisition|recruit|people (ops|operation)|\bhrbp\b|staffing",
        "near": r"operations|admin|business development|training",
        "skills": {
            "recruitment": r"recruit|sourcing|screening|\bats\b|naukri|hiring",
            "interview coordination": r"interview (coordination|scheduling)|scheduling",
            "onboarding": r"onboard|induction|documentation",
            "excel": r"\bexcel\b|\bmis\b|tracker",
            "employee engagement": r"engagement|employee relation|culture|event",
            "payroll": r"payroll|attendance|\bhrms\b|compensation",
            "linkedin sourcing": r"linkedin|boolean search|headhunt",
            "hr policy": r"\bhr\b polic|compliance|labour law",
        },
    },
    "sales-bd": {
        "label": "Sales / Business Development",
        "queries": ["sales intern", "business development intern", "inside sales intern", "sales executive intern"],
        "titles": r"\bsales\b|business development|\bbd\b (intern|executive)|inside sales|account (executive|manager)|pre ?sales|telecall",
        "near": r"marketing|customer success|operations|\bcrm\b",
        "skills": {
            "lead generation": r"lead gen|prospect|cold call|cold email|outreach",
            "crm": r"\bcrm\b|salesforce|hubspot|zoho",
            "negotiation": r"negotiat|closing|conversion",
            "linkedin": r"linkedin|sales navigator",
            "target driven": r"target|quota|revenue|\bkpi\b",
            "excel": r"\bexcel\b|reporting|pipeline",
            "client relationship": r"client (relationship|handling)|account management|customer success",
            "product demo": r"product demo|presentation|pitch",
        },
    },
    "operations": {
        "label": "Operations / Supply Chain",
        "queries": ["operations intern", "supply chain intern", "logistics intern", "process excellence intern"],
        "titles": r"operations|supply chain|logistic|procurement|warehouse|\bscm\b|process excellence|category",
        "near": r"business analyst|project|admin|\bmis\b",
        "skills": {
            "excel": r"\bexcel\b|vlookup|pivot|\bmis\b",
            "supply chain": r"supply chain|inventory|demand (planning|forecast)|procurement",
            "sql": r"\bsql\b|power ?bi|dashboard",
            "process improvement": r"process (improvement|mapping)|\bsop\b|lean|six sigma|\bkaizen\b",
            "vendor management": r"vendor|supplier|negotiat",
            "logistics": r"logistic|dispatch|last mile|freight|warehouse",
            "coordination": r"coordinat|cross[- ]functional|stakeholder",
            "erp": r"\berp\b|\bsap\b|oracle",
        },
    },
    "electronics-vlsi": {
        "label": "Electronics / VLSI / Embedded",
        "queries": ["electronics intern", "VLSI intern", "embedded systems intern", "hardware design intern"],
        "titles": r"electronic|\bvlsi\b|embedded|\bece\b|hardware|\bpcb\b|firmware|\brtl\b|chip design|semiconductor|\biot\b",
        "near": r"instrumentation|automation|\bplc\b|robotic",
        "skills": {
            "verilog": r"verilog|\bvhdl\b|system ?verilog|\brtl\b",
            "embedded c": r"embedded c|\bc programming\b|microcontroller",
            "microcontrollers": r"arduino|raspberry ?pi|\bstm32\b|\b8051\b|\bavr\b|\besp32\b",
            "pcb design": r"\bpcb\b|altium|eagle|kicad|schematic",
            "matlab": r"matlab|simulink", "python": r"\bpython\b",
            "iot": r"\biot\b|sensor|\bmqtt\b",
            "eda tools": r"cadence|synopsys|xilinx|vivado|quartus",
            "testing": r"testing|validation|debug|oscilloscope",
            "signal processing": r"signal processing|\bdsp\b|communication system",
        },
    },
    "mechanical": {
        "label": "Mechanical / Automobile / Design",
        "queries": ["mechanical engineering intern", "design engineer intern", "CAD intern", "production engineer intern"],
        "titles": r"mechanical|automobile|automotive|design engineer|production|manufactur|\bcad\b|\bcae\b|thermal|\bhvac\b|maintenance engineer",
        "near": r"quality|operations|project engineer|industrial",
        "skills": {
            "solidworks": r"solid ?works|\bcatia\b|creo|inventor",
            "autocad": r"auto ?cad|drafting|\bgd&t\b",
            "ansys": r"\bansys\b|\bfea\b|\bcfd\b|simulation|hypermesh",
            "manufacturing": r"manufactur|machining|\bcnc\b|welding|casting|sheet metal",
            "quality": r"quality|\bqc\b|\bqa\b|inspection|iso ?9001|six sigma",
            "thermal": r"thermal|heat transfer|\bhvac\b|refrigerat",
            "project costing": r"\bbom\b|costing|\bnpd\b",
            "documentation": r"\bexcel\b|documentation|report",
        },
    },
    "civil": {
        "label": "Civil / Architecture",
        "queries": ["civil engineering intern", "architecture intern", "site engineer intern", "structural design intern"],
        "titles": r"civil|architect|structural|site engineer|construction|quantity survey|planning engineer|\bbim\b|interior",
        "near": r"project engineer|design|estimation|real estate",
        "skills": {
            "autocad": r"auto ?cad|drafting",
            "revit": r"\brevit\b|\bbim\b|navisworks",
            "staad pro": r"staad|\betabs\b|\bsap2000\b|structural analysis",
            "sketchup": r"sketch ?up|3ds max|lumion|rhino",
            "estimation": r"estimation|quantity|\bboq\b|costing|billing",
            "site execution": r"site (execution|supervision|visit)|construction|\brcc\b|survey",
            "project planning": r"ms project|primavera|scheduling|planning",
            "is codes": r"\bis ?456\b|building (code|bye[- ]?law)|\bnbc\b",
        },
    },
    "law": {
        "label": "Law / Legal",
        "queries": ["legal intern", "law intern", "legal research intern", "company secretary intern"],
        "titles": r"\blegal\b|\blaw\b intern|advocate|litigation|compliance|contract|paralegal|company secretary|intellectual property|\bipr\b",
        "near": r"policy|research|governance|\bgrc\b|secretarial",
        "skills": {
            "legal research": r"legal research|scc ?online|manupatra|case law|judgment",
            "drafting": r"draft|notice|petition|agreement",
            "contracts": r"contract|\bnda\b|\bmsa\b|vendor agreement|lease",
            "compliance": r"compliance|regulator|\brbi\b|\bsebi\b|\bmca\b|statutory",
            "corporate law": r"companies act|corporate law|\bm&a\b|due diligence",
            "ipr": r"intellectual property|\bipr\b|trademark|patent|copyright",
            "litigation": r"litigation|court|arbitrat|hearing",
            "data privacy": r"data (privacy|protection)|\bgdpr\b|\bdpdp\b",
        },
    },
}

# Internship-shaped words, used to tell an internship from a full-time opening.
INTERN_TITLE = r"\bintern\b|\binternship\b|\btrainee\b|\bapprentice\b|\bfresher\b|\bgraduate program\b"


def field_choices() -> list[tuple[str, str]]:
    """(key, label) pairs for the signup dropdown, alphabetical by label."""
    return sorted(((k, v["label"]) for k, v in FIELDS.items()), key=lambda p: p[1])


def label(key: str) -> str:
    return FIELDS.get(key, {}).get("label", key)


def skills_for(key: str) -> dict[str, str]:
    """Field skills plus the common ones, for both matching and the skills picker."""
    f = FIELDS.get(key)
    if not f:
        return dict(COMMON_SKILLS)
    return {**f["skills"], **COMMON_SKILLS}


def queries_for(key: str) -> list[str]:
    return FIELDS.get(key, {}).get("queries", [])
